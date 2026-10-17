"""Histórico de cash (``cash_ledger``) e de itens (``item_log``), gravados na mesma transação da mudança.

O portal PHP grava ``cash_ledger`` também (edições GM, recargas) com as mesmas colunas.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Protocol

from ..domain.models import CashLedger, Character, ItemLog


class _Saves(Protocol):
    async def save(self, entity: object) -> None: ...


def cash_entry(
    character: Character, delta_point: int, delta_gift_token: int, reason: str, ref: str, gm: str | None = None
) -> CashLedger:
    """Linha do ledger com o saldo já alterado no ``character``; para passar a ``characters.save``."""
    return CashLedger(
        character.id or 0,
        delta_point,
        delta_gift_token,
        character.point,
        character.gift_token,
        reason,
        ref,
        datetime.now(UTC),
        gm,
    )


async def record_cash(
    uow: _Saves,
    character: Character,
    delta_point: int,
    delta_gift_token: int,
    reason: str,
    ref: str,
    gm: str | None = None,
) -> None:
    """Grava na transação aberta de ``uow`` (chame depois de alterar o saldo do personagem)."""
    await uow.save(cash_entry(character, delta_point, delta_gift_token, reason, ref, gm))


def item_entry(character_id: int, template_id: int, count: int, action: str, ref: str) -> ItemLog:
    return ItemLog(character_id, template_id, count, action, ref, datetime.now(UTC))
