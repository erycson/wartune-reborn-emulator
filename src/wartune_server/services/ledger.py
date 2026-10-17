"""Histórico de cash (``cash_ledger``) e de itens (``item_log``), gravados na mesma transação da mudança.

Os helpers só montam a linha; quem chama passa para ``characters.save(c, ..., entry)``, assim o débito e o
registro entram juntos. O portal PHP grava ``cash_ledger`` também (edições GM, recargas) com as mesmas colunas.
"""

from __future__ import annotations

from datetime import UTC, datetime

from ..domain.models import CashLedger, Character, ItemLog


def record_cash(
    c: Character,
    delta_point: int,
    delta_gift_token: int,
    reason: str,
    ref: str,
    now: datetime | None = None,
    gm: str | None = None,
) -> CashLedger:
    """Linha do ledger com o saldo já alterado no ``c``."""
    now = now or datetime.now(UTC)
    return CashLedger(c.id or 0, delta_point, delta_gift_token, c.point, c.gift_token, reason, ref, now, gm)


def pay(c: Character, cost: int, *, bind: bool, reason: str, ref: str, now: datetime) -> CashLedger | None:
    """Debita ``cost``; com ``bind`` usa o vinculado primeiro e completa com diamante. None = sem saldo."""
    gift = min(c.gift_token, cost) if bind else 0
    if cost < 0 or c.point < cost - gift:
        return None
    c.gift_token -= gift
    c.point -= cost - gift
    return record_cash(c, -(cost - gift), -gift, reason, ref, now)


def spend(c: Character, cost: int, reason: str, now: datetime, *, bound: bool, ref: str = "") -> CashLedger | None:
    """Como ``pay``, para custos que o cliente já validou como positivos (eventos, VIP)."""
    if cost <= 0:
        raise ValueError("custo deve ser positivo")
    return pay(c, cost, bind=bound, reason=reason, ref=ref, now=now)


def item_entry(character_id: int, template_id: int, count: int, action: str, ref: str) -> ItemLog:
    return ItemLog(character_id, template_id, count, action, ref, datetime.now(UTC))
