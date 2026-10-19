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

# ponytail: lock global do processo (um servidor por processo). Por anúncio se a fila pesar.
MALL_LOCK = asyncio.Lock()
# ponytail: o agendador roda a cada 60 s sem dormir até o menor ends_at: até 60 s de atraso no encerramento
SWEEP_SECONDS = 60
# (cliente) language.txt AuctionHelp.helpContent item 7: "o sistema tira 20% de imposto do vendedor"
TAX_PERCENT = 20


def income(price: int) -> int:
    """O que o vendedor recebe de uma venda de ``price`` diamantes, já sem o imposto."""
    # ponytail: arredondamento para baixo; o texto do cliente não diz como o oficial arredonda
    return price * (100 - TAX_PERCENT) // 100


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
        label = f"{name(templates, item.template_id)} x{item.count}"
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
                    f"{label}: you are the highest bidder.",
                    items=[item],
                )
            )
            mails.append(
                await post(
                    uow,
                    listing.seller_id,
                    now,
                    "Sale Income",  # texto deduzido (sem fonte no cliente/captura)
                    f"{label} has been sold.",
                    goods=[(DIAMOND, income(listing.point))],
                )
            )
        else:
            mails.append(
                # texto deduzido (sem fonte no cliente/captura)
                await post(uow, listing.seller_id, now, "Returned Item", f"{label}: no buyer was found.", items=[item])
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


async def run(
    characters: CharacterService,
    templates: GameTemplates,
    online: OnlinePlayers,
    clock: Clock,
    server_id: int,
    every: float = SWEEP_SECONDS,
) -> None:
    """Loop do encerramento (``app.py`` cancela ao desligar). A primeira rodada sai já, para pegar o que venceu
    com o servidor fora. Uma rodada que falha é registrada e a próxima tenta de novo."""
    while True:
        try:
            await sweep(characters, templates, online, server_id, clock.now())
        except Exception:
            log.exception("encerramento do mercado falhou", proxima_em_s=every)
        await asyncio.sleep(every)
