"""Consumir e conceder itens no snapshot (cornetas, carta de renomear, anexos de correio).

Só mexem em memória: quem chama grava tudo numa ``characters.save`` e manda os pacotes.
"""

from __future__ import annotations

from ..domain.models import BagType, Item, PlayerSnapshot
from ..protocol.messages import wartune_pb2 as pb
from ..templates.repository import GameTemplates
from . import rules
from .bag import BAG_BASE as BAG_SIZE  # ponytail: só os 42 base; espaços comprados/alugados via bag.capacity(c, now)
from .builders.player import item_moved
from .handlers.player import CURRENCIES


def bag_item(snap: PlayerSnapshot, *, pos: int | None = None, template_id: int | None = None) -> Item | None:
    return next(
        (
            i
            for i in snap.items
            if i.bag_type == BagType.BAG and pos in (None, i.pos) and template_id in (None, i.template_id)
        ),
        None,
    )


def take_one(snap: PlayerSnapshot, item: Item) -> Item | None:
    """Gasta uma unidade; devolve o item se acabou (para ``delete=``), senão ``None``."""
    item.count -= 1
    if item.count > 0:
        return None
    snap.items.remove(item)
    return item


def item_update(item: Item, player_id: int) -> pb.ItemMovedListMsg:
    """115 da posição do item (vazia se ele acabou)."""
    return item_moved(BagType.BAG, 0, item.pos, item if item.count > 0 else None, player_id)


def fits(snap: PlayerSnapshot, goods: list[tuple[int, int]]) -> bool:
    used = sum(i.bag_type == BagType.BAG for i in snap.items)
    return used + sum(t > 0 for t, _ in goods) <= BAG_SIZE


def known(templates: GameTemplates, template_id: int) -> bool:
    return template_id in CURRENCIES or (template_id > 0 and templates.get("ItemTempInfos", template_id) is not None)


def grant(snap: PlayerSnapshot, goods: list[tuple[int, int]]) -> list[Item]:
    """Põe ``(templateId, quantidade)`` na mochila / moedas; confira ``fits`` e ``known`` antes.

    ponytail: um item novo por entrada, sem empilhar (igual ao 5006); empilhar quando o
    MaxCount importar.
    """
    c, new = snap.character, []
    for template_id, count in goods:
        if (field := CURRENCIES.get(template_id)) is not None:
            setattr(c, field, getattr(c, field) + count)
            continue
        item = Item(c.id or 0, template_id, count=count)
        item.pos = rules.free_bag_pos(snap)
        snap.items.append(item)
        new.append(item)
    return new
