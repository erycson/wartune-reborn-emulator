"""Mercado entre jogadores: encerrar os anúncios vencidos e as cartas que saem deles (correio).

``settle`` roda em dois lugares, sempre na mesma transação e sob ``MALL_LOCK``: no começo de cada pedido do
mercado (``handlers/mall.py``) e no encerramento agendado (``run``, a cada ``SWEEP_SECONDS``), que encerra os
vencidos sem ninguém pedir nada. O item e o diamante vão pelo correio porque o destinatário pode estar offline e o
snapshot dele não pode ser alterado daqui.
"""

from __future__ import annotations

import asyncio
from collections.abc import Sequence
from datetime import datetime
from typing import TYPE_CHECKING

import structlog

from ..domain.models import Item, Mail, MailType, Purchase
from ..domain.repositories import UnitOfWork
from ..templates.repository import GameTemplates
from . import mail as mailbox
from .bag import name

if TYPE_CHECKING:
    from ..services.characters import CharacterService
    from ..services.clock import Clock
    from .session import OnlinePlayers

log = structlog.get_logger(__name__)

DIAMOND = -400  # TemplateId da moeda no correio (CURRENCIES, handlers/player.py): Balens não vinculados
SYLPH = mailbox.SYLPH  # o Sylph à venda (item -900)

# ponytail: lock global do processo (um servidor por processo). Por anúncio se a fila pesar.
MALL_LOCK = asyncio.Lock()
SWEEP_SECONDS = 60  # sono máximo do agendador; dorme menos quando um anúncio vence antes
# (cliente) language.txt AuctionHelp.helpContent item 7: "o sistema tira 20% de imposto do vendedor"
TAX_PERCENT = 20


def income(price: int) -> int:
    """O que o vendedor recebe de uma venda de ``price`` diamantes, já sem o imposto."""
    # ponytail: arredondamento para baixo; o texto do cliente não diz como o oficial arredonda
    return price * (100 - TAX_PERCENT) // 100


def goods_row(templates: GameTemplates, item: Item) -> dict[str, str]:
    """A linha de ``ItemTempInfos`` do item. No Sylph, nome, nível e qualidade são os do pet (o cliente o nomeia
    pelo ``TemplateName`` do pet e mostra o nível dele); a qualidade é a cor, ``(Quality - 1) / 5 + 1``."""
    row = dict(templates.get("ItemTempInfos", item.template_id) or {})
    if item.template_id == SYLPH and item.property1:
        head = item.property1.split("|")[0].split(",")
        pet = templates.get("PetTempInfos", int(head[0])) or {}
        tier = (int(head[1]) - 1) // 5 + 1
        row.update(TemplateName=pet.get("TemplateName", ""), NeedGrades=head[4], Profile=str(tier))
    return row


def label(templates: GameTemplates, item: Item) -> str:
    """O item nas cartas do mercado: "nome xN"."""
    return f"{goods_row(templates, item).get('TemplateName') or name(templates, item.template_id)} x{item.count}"


async def post(
    uow: UnitOfWork,
    receiver: int,
    now: datetime,
    title: str,
    text: str,
    goods: Sequence[tuple[int, int]] = (),
    items: Sequence[Item] = (),
) -> Mail:
    """Carta do sistema na transação de quem chama (sem ``commit``). Mande o 148 com ``notify`` depois."""
    mail = Mail(receiver, now, title, text, mail_type=MailType.SYSTEM, send_type=mailbox.SYSTEM_SENDER)
    await mailbox.stage(uow, mail, goods, items)
    return mail


async def settle(uow: UnitOfWork, templates: GameTemplates, server_id: int, now: datetime) -> list[Mail]:
    """Encerra os anúncios vencidos do servidor. Com lance: o item vai ao vencedor e o diamante ao vendedor.
    Sem lance: o item volta ao vendedor. Devolve as cartas (o 148 sai depois do commit)."""
    due = await uow.mall.expired(server_id, now)
    if not due:
        return []
    items = {i.id: i for i in await uow.items.by_ids([x.item_id for x in due])}
    mails: list[Mail] = []
    for listing in due:
        for bid in await uow.mall.bids_of(listing.id or 0):
            await uow.delete(bid)
        await uow.delete(listing)
        item = items.get(listing.item_id)
        if item is None:  # o item é apagado junto com o anúncio (cascata): não há o que entregar
            continue
        what = label(templates, item)
        if listing.bidder_id:
            # o lance vencedor é a compra (o diamante saiu no lance, mall_bids)
            await uow.save(
                Purchase(
                    listing.bidder_id,
                    "mall_lance",
                    listing.id or 0,
                    item.template_id,
                    item.count,
                    "Point",
                    listing.point,
                    now,
                )
            )
            mails.append(
                await post(
                    # texto deduzido (sem fonte no cliente/captura)
                    uow,
                    listing.bidder_id,
                    now,
                    "Won Item",
                    f"{what}: you are the highest bidder.",
                    items=[item],
                )
            )
            mails.append(
                await post(
                    uow,
                    listing.seller_id,
                    now,
                    "Sale Income",  # texto deduzido (sem fonte no cliente/captura)
                    f"{what} has been sold.",
                    goods=[(DIAMOND, income(listing.point))],
                )
            )
        else:
            mails.append(
                # texto deduzido (sem fonte no cliente/captura)
                await post(uow, listing.seller_id, now, "Returned Item", f"{what}: no buyer was found.", items=[item])
            )
    return mails


async def sweep(
    characters: CharacterService, templates: GameTemplates, online: OnlinePlayers, server_id: int, now: datetime
) -> list[Mail]:
    """Uma rodada do encerramento agendado: os vencidos do servidor, sem pedido de ninguém. Mesmo lock e mesma
    transação dos pedidos; o 148 sai depois do commit."""
    async with MALL_LOCK:
        mails = await characters.write(lambda uow: settle(uow, templates, server_id, now))
    for mail in mails:
        mailbox.notify(online, mail)
    return mails


async def next_wait(characters: CharacterService, server_id: int, now: datetime, every: float) -> float:
    """Segundos até o próximo anúncio vencer, no máximo ``every``."""
    end = await characters.read(lambda uow: uow.mall.next_end(server_id))
    return every if end is None else min(every, max(0.0, (end - now).total_seconds()))


async def run(
    characters: CharacterService,
    templates: GameTemplates,
    online: OnlinePlayers,
    clock: Clock,
    server_id: int,
    every: float = SWEEP_SECONDS,
) -> None:
    """Loop do encerramento (``app.py`` cancela ao desligar). A primeira rodada sai já, para pegar o que venceu
    com o servidor fora. Dorme até o menor ``ends_at`` (no máximo ``every``: o anúncio novo dura horas). Uma rodada
    que falha é registrada e a próxima tenta de novo."""
    from .handlers import vip  # os handlers importam este módulo

    since = clock.now()
    while True:
        wait, now = every, clock.now()
        try:
            await sweep(characters, templates, online, server_id, now)
            wait = await next_wait(characters, server_id, clock.now(), every)
            vip.notify_expired(online, since, now)  # o VIP que vence com o jogador online avisa a guilda
            since = now
        except Exception:
            log.exception("encerramento do mercado falhou", proxima_em_s=every)
        await asyncio.sleep(wait)
