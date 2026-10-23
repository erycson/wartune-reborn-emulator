"""Concessão de recompensas (itens + moedas de TemplateId negativo) no ``PlayerSnapshot``.

Mesma regra do pacote da mochila (5006), usada por eventos, atividades e minigames: valida tudo
antes (``can_grant``), altera o snapshot sem await, e quem chama grava personagem + itens novos
numa ``save`` só, junto com o que foi consumido.
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime

from ..domain.models import BagType, Item, PlayerSnapshot
from ..protocol.messages import wartune_pb2 as pb
from ..templates.repository import GameTemplates
from . import bag, rules
from .builders.player import item_moved

# TemplateId < 0 (-600 Kyanite: os cristais do castelo)
CURRENCIES = {-100: "gold", -300: "strategy", -400: "point", -500: "gift_token", -600: "crystals"}
EXP = -700  # ItemTempInfo -700 "EXP": soma no jogador (rules.add_gp)

Drop = tuple[int, int]  # (TemplateId, quantidade)


def can_grant(
    snap: PlayerSnapshot, templates: GameTemplates, drops: Sequence[Drop], now: datetime, freed: int = 0
) -> bool:
    """Todo TemplateId existe (ou é moeda conhecida) e os itens cabem na mochila real (``bag.capacity``: 42 +
    comprados, 217 com a alugada), um espaço por entrada (``grant`` não empilha).

    ``freed``: espaços que a mesma operação libera (ex. a caixa que está sendo aberta).
    """
    known = all(t in CURRENCIES or t == EXP or (t > 0 and templates.get("ItemTempInfos", t)) for t, _ in drops)
    goods = sum(t > 0 for t, _ in drops)
    return known and all(n > 0 for _, n in drops) and goods <= len(bag.free_positions(snap, now)) + freed


def _name(templates: GameTemplates, template_id: int) -> str:
    return (templates.get("ItemTempInfos", template_id) or {}).get("TemplateName", str(template_id))


def received(templates: GameTemplates, drops: Sequence[Drop]) -> str:
    """O texto do oficial inglês nas campanhas: moeda com o valor antes ("Received: 500 Gold", "Received: 10,000
    Daru"), item com ``x`` ("Received: Worg Tooth x2"): captura inglesa #946, #1216, #2631, #1123. É o ``text`` no
    estilo ``bag``."""
    return text(templates, drops)


def text(templates: GameTemplates, drops: Sequence[Drop], style: str = "bag") -> str:
    """``Received: ...`` como o oficial inglês escreve: ``bag`` (``50,000 Gold, Moderate HP Pack x1``, #2110) ou
    ``active`` (atividades: ``Bound Balens x 10,Daru x 10000``, #2772) ou ``plain`` (login acumulado: ``Worn Weapon
    x1, Gold x10000``, oficial_20261023-153200-1 #1716)."""
    if style == "plain":
        return "Received: " + ", ".join(f"{_name(templates, t)} x{n}" for t, n in drops)
    if style == "active":
        return "Received: " + ",".join(f"{_name(templates, t)} x {n}" for t, n in drops)
    return "Received: " + ", ".join(
        f"{n:,} {_name(templates, t)}" if t < 0 else f"{_name(templates, t)} x{n}" for t, n in drops
    )


def grant(
    snap: PlayerSnapshot, templates: GameTemplates, drops: Sequence[Drop], style: str = "bag"
) -> tuple[list[Item], str]:
    """Aplica ``drops`` no snapshot (chame ``can_grant`` antes). Devolve os itens novos (sem id
    ainda: grave com ``characters.save``) e o texto ``Received: ...``."""
    c = snap.character
    new: list[Item] = []
    for template_id, count in drops:
        if (field := CURRENCIES.get(template_id)) is not None:
            setattr(c, field, getattr(c, field) + count)
        elif template_id == EXP:
            rules.add_gp(snap, templates, count)
        else:
            item = Item(c.id or 0, template_id, count=count)
            item.random_skills = bag.roll_random_skills(templates, template_id)
            item.pos = rules.free_bag_pos(snap)
            snap.items.append(item)
            new.append(item)
    return new, text(templates, drops, style)


def owners(snap: PlayerSnapshot) -> list[object]:
    """O que um ``grant`` pode alterar além dos itens novos: personagem, líder e tropas (EXP sobe nível e completa o
    exército, ``rules.top_up_army``)."""
    return [e for e in (snap.character, snap.leader, *snap.pawns) if e is not None]


def items_msg(items: Sequence[Item], player_id: int) -> pb.ItemMovedListMsg:
    """Um 115 com todos os itens novos (cada um na sua posição da mochila)."""
    msg = pb.ItemMovedListMsg()
    for item in items:
        msg.moved.extend(item_moved(BagType.BAG, 0, item.pos, item, player_id).moved)
    return msg


def take_one(snap: PlayerSnapshot, template_id: int) -> tuple[Item, bool] | None:
    """Consome uma unidade do item ``template_id`` da mochila. Devolve (item, apagado?): grave o item
    ou passe-o em ``delete=`` na mesma ``save`` da recompensa. ``None`` se não tiver."""
    item = next((i for i in snap.items if i.bag_type == BagType.BAG and i.template_id == template_id), None)
    if item is None:
        return None
    if item.count > 1:
        item.count -= 1
        return item, False
    snap.items.remove(item)
    return item, True


def taken_msg(item: Item, gone: bool, player_id: int) -> pb.ItemMovedListMsg:
    """115 do item consumido por ``take_one`` (posição vazia se acabou)."""
    return item_moved(BagType.BAG, 0, item.pos, None if gone else item, player_id)
