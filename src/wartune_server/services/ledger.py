"""Livro-caixa de diamantes (``cash_ledger``): cada gasto de ``point``/``gift_token`` vira uma linha.

As funções só mexem no ``Character`` em memória e devolvem a ``CashLedger``; quem chama grava as
duas na mesma ``characters.save`` (o débito e o registro são atômicos).
"""

from __future__ import annotations

from datetime import datetime

from ..domain.models import CashLedger, Character


def spend(c: Character, cost: int, reason: str, now: datetime, *, bound: bool, ref: str = "") -> CashLedger | None:
    """Desconta ``cost`` diamantes; com ``bound`` gasta os vinculados (gift_token) primeiro, como o
    cliente oferece ("usar Bağlı Elmas"). ``None`` se não houver saldo (nada é alterado)."""
    if cost <= 0:
        raise ValueError("custo deve ser positivo")
    gift = min(c.gift_token, cost) if bound else 0
    point = cost - gift
    if point > c.point:
        return None
    c.gift_token -= gift
    c.point -= point
    return CashLedger(c.id or 0, -point, -gift, c.point, c.gift_token, reason, now, ref)
