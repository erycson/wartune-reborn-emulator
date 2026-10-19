"""Moeda premium (``point`` = Balens, ``gift_token`` = Bound Balens) com registro no ``cash_ledger``.

Quem chama altera o personagem com ``change``/``pay`` e passa o ``CashLedger`` devolvido para o
mesmo ``CharacterService.save`` da compra: o débito, o item e o registro entram numa transação só.
"""

from __future__ import annotations

from datetime import datetime

from ..domain.models import CashLedger, Character

BIND_FIRST = 0  # payType dos pacotes: 0 = "Use Bound Balens first" marcado, 1 = só Balens


def change(
    c: Character, point: int, gift_token: int, reason: str, ref: str, now: datetime, gm: str | None = None
) -> CashLedger:
    """Soma ``point``/``gift_token`` (negativos = gasto) e devolve o registro. Saldo negativo é erro de quem chamou."""
    if c.point + point < 0 or c.gift_token + gift_token < 0:
        raise ValueError("saldo de moeda premium ficaria negativo")
    c.point += point
    c.gift_token += gift_token
    return CashLedger(c.id or 0, point, gift_token, c.point, c.gift_token, reason, ref, now, gm)


def split(c: Character, total: int, pay_type: int, gift_ok: bool = True) -> tuple[int, int] | None:
    """Quanto sai de cada moeda para pagar ``total`` Balens, ou None se não dá.

    Com ``BIND_FIRST`` (e se o preço aceita vinculado) usa o vinculado primeiro e completa com Balens,
    como ``BuyFrameI.PayMoney`` (giftToken + point); senão só Balens.
    """
    if total < 0:
        return None
    gift = min(c.gift_token, total) if gift_ok and pay_type == BIND_FIRST else 0
    point = total - gift
    return (point, gift) if c.point >= point else None


def pay(
    c: Character, total: int, pay_type: int, reason: str, ref: str, now: datetime, gift_ok: bool = True
) -> CashLedger | None:
    """Debita ``total`` Balens conforme ``split``; None (nada muda) se faltar saldo."""
    parts = split(c, total, pay_type, gift_ok)
    if parts is None:
        return None
    return change(c, -parts[0], -parts[1], reason, ref, now)
