"""Diamante (``point``) e diamante vinculado (``gift_token``): cobrança e registro em ``cash_ledger``.

``record_cash`` só monta a linha; quem chama grava junto com o resto (``characters.save(c, ..., entry)``),
assim o débito e o registro entram na mesma transação.
"""

from __future__ import annotations

from datetime import datetime

from ..domain.models import CashEntry, Character


def record_cash(
    c: Character, delta_point: int, delta_gift_token: int, reason: str, ref: str, now: datetime, gm: str | None = None
) -> CashEntry:
    return CashEntry(c.id or 0, delta_point, delta_gift_token, c.point, c.gift_token, reason, ref, now, gm)


def pay(c: Character, cost: int, *, bind: bool, reason: str, ref: str, now: datetime) -> CashEntry | None:
    """Debita ``cost``; com ``bind`` usa o vinculado primeiro e completa com diamante. None = sem saldo."""
    gift = min(c.gift_token, cost) if bind else 0
    if cost < 0 or c.point < cost - gift:
        return None
    c.gift_token -= gift
    c.point -= cost - gift
    return record_cash(c, -(cost - gift), -gift, reason, ref, now)
