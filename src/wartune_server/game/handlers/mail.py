"""Correio pelo socket: enviar (8205), apagar (8206), pegar anexos (5022) e verificação de e-mail
(9591). A lista em si vai por HTTP (``maillist``, ver http/app.py e game/mail.py)."""

from __future__ import annotations

import random
import re

from ...domain.models import BagType, CashLedger, Item, Mail, MailAnnex, MailType, Pet, PlayerSnapshot
from ...domain.repositories import UnitOfWork
from ...protocol.messages import wartune_pb2 as pb
from ...services import ledger
from ...services.ledger import record_cash
from .. import bag, items, rules, social
from .. import events as gev
from .. import guild as gd
from .. import mail as mailbox
from ..builders import login as b
from ..builders.player import item_moved
from ..castle import castle_yield
from ..mail import SYSTEM_SENDER
from ..mall import SYLPH
from ..router import router
from ..session import GameSession
from . import events, shop
from .login import player_info
from .pets import BASE_SLOTS, S_PETS, pets_msg, take_back

S_PICKUP, S_MAIL_UPDATE, S_DELETED, S_MAIL_CHECK, S_ITEMS, S_PLAYER = 114, 4131, 4132, 337, 115, 3
SEND_COST = 100  # EmailControler.sendEmail: precisa de 100 de ouro
TITLE_MAX, CONTENTS_MAX = 15, 300  # WriteEmailFrame: assunto maxChars 15; texto limitado a 7 linhas
MIN_GRADE = 6  # ReadEmailView: responder exige nível 6
PLAYER_MAIL, GUILD_MAIL = 1, 2  # MailSendReqMsg.sendType (ConsortiaControler.sendEmail manda 2)
# ConsortiaEmailGroupSendView: "Spend 175 Balens to send Guild Mail?"; o botão é do chefe (getRightsByIndex(1))
GUILD_MAIL_COST = 175
MAX_PICKUP = 50
_TAG = re.compile(r"<[^>]*>")
_MAIL_RE = re.compile(r"[\w.+-]+@[\w-]+(\.[\w-]+)+")  # MailCheckFrame.ckSth, mais estrito
MAIL_CHECK_KEY, MAIL_VERIFIED = "mail_check", -1


def _clean(raw: str, limit: int) -> str | None:
    text = _TAG.sub("", raw).strip()
    return text if 0 < len(text) <= limit else None


@router.on(8205)
async def send_mail(s: GameSession, msg: pb.MailSendReqMsg) -> None:
    """Correio de jogador para jogador: só texto (o proto não tem anexo), custa 100 de ouro. ``sendType`` 2 é o
    correio de guilda (``_guild_mail``)."""
    snap = s.snapshot
    assert snap is not None
    c = snap.character
    title, contents = _clean(msg.title, TITLE_MAX), _clean(msg.contents, CONTENTS_MAX)
    if msg.sendType == GUILD_MAIL:
        await _guild_mail(s, msg, title, contents)
        return
    targets = list(msg.receiverUserId)
    found = await social.characters(s.ctx, targets[:1]) if len(targets) == 1 else {}
    receiver = next((r.id for r in found.values() if r.server_id == c.server_id and r.id != c.id), None)
    if (
        msg.sendType != PLAYER_MAIL
        or receiver is None
        or title is None
        or contents is None
        or c.gold < SEND_COST
        or c.grades < MIN_GRADE
    ):
        s.log.info("8205 recusado", para=targets, tipo=msg.sendType, ouro=c.gold)
        return
    c.gold -= SEND_COST  # antes do await: dois envios seguidos não gastam o mesmo ouro
    mail = Mail(
        receiver,
        s.ctx.clock.now(),
        title,
        contents,
        sender_id=s.player_id,
        sender_nick=c.nickname or "",
        sender_grades=c.grades,
        mail_type=MailType.PLAYER,
    )
    await mailbox.deliver(s.ctx.characters, s.ctx.online, mail, (), c)
    castle_yield(s)


async def _guild_mail(s: GameSession, msg: pb.MailSendReqMsg, title: str | None, contents: str | None) -> None:
    """O chefe escreve para vários membros de uma vez (o cliente manda os ids dos nomes que acha na lista da
    guilda); 175 Balens, ``payType`` 0 gasta os vinculados primeiro (caixa USEBINDPOINT_ALERT)."""
    snap = s.snapshot
    assert snap is not None
    c, now, mine = snap.character, s.ctx.clock.now(), s.ctx.guilds.of(s.player_id)
    members = {m.character_id for m in s.ctx.guilds.members_of(mine[0].id or 0)} if mine else set()
    targets = list(dict.fromkeys(msg.receiverUserId))
    chairman = mine is not None and gd.has_right(mine[1].duty_id, gd.R_CHAIRMAN)
    ok = chairman and bool(targets) and set(targets) <= members and title is not None and contents is not None
    ref = f"guild:{mine[0].id if mine else 0}"
    bind = msg.payType == 0
    entry = ledger.pay(c, GUILD_MAIL_COST, bind=bind, reason="guild_mail", ref=ref, now=now) if ok else None
    if entry is None or title is None or contents is None:
        s.log.info("8205 recusado (guilda)", para=targets, chefe=chairman, diamantes=c.point)
        return
    mails = [
        Mail(t, now, title, contents, sender_id=s.player_id, sender_nick=c.nickname or "", sender_grades=c.grades)
        for t in targets
    ]

    async def insert(uow: UnitOfWork) -> None:
        for entity in (c, entry, *mails):
            await uow.save(entity)

    await s.ctx.characters.write(insert)
    for mail in mails:
        mailbox.notify(s.ctx.online, mail)
    s.send(S_PLAYER, b.complete(player_info(s, snap)))


@router.on(8206)
async def delete_mail(s: GameSession, msg: pb.MailDelReqMsg) -> None:
    """4132 com os ids apagados; lista vazia o cliente mostra como erro."""
    ids = list(dict.fromkeys(msg.delList))[:MAX_PICKUP]
    mine = await s.ctx.characters.read(lambda uow: uow.mails.by_receiver(s.player_id, ids))
    annexes = await s.ctx.characters.read(lambda uow: uow.mails.annexes([m.id or 0 for m in mine]))
    # item de verdade que ainda não foi retirado só existe neste correio: ele fica até o 5022
    held = {a.mail_id for a in annexes if a.item_id and not a.taken}
    mine = [m for m in mine if m.id not in held]
    if mine:
        await s.ctx.characters.save(delete=tuple(mine))  # anexos vão junto (ON DELETE CASCADE)
    s.send(S_DELETED, pb.MailDelReqMsg(delList=[m.id or 0 for m in mine]))


def _carried(snap: PlayerSnapshot, fetched: dict[int, Item], item_id: int) -> Item | None:
    """O item de um anexo: a cópia do snapshot se ele já estiver lá, senão a linha lida do banco."""
    return next((i for i in snap.items if i.id == item_id), None) or fetched.get(item_id)


@router.on(5022)
async def take_annexes(s: GameSession, msg: pb.MailMsg) -> None:
    """Pega os anexos (``position`` 0 = todos, senão 1..5) de cada correio, tudo numa transação.

    Mochila sem espaço para todos os itens de um correio: aquele correio fica com result false. O Sylph do leilão
    (item -900) vai para a lista de pets, não para a mochila; lista cheia também dá false ("You cannot accept the
    Sylph if your roster is full", auctionFrame.helpPet). O -900 some ao pegar.
    """
    snap = s.snapshot
    assert snap is not None
    ids = list(dict.fromkeys(msg.mailsIdArray))[:MAX_PICKUP]
    positions = dict(zip(msg.mailsIdArray, msg.position, strict=False))
    mails = await s.ctx.characters.read(lambda uow: uow.mails.by_receiver(s.player_id, ids))
    annexes = await s.ctx.characters.read(lambda uow: uow.mails.annexes([m.id or 0 for m in mails]))
    # itens de verdade (leilão, lance de volta...) que não estão no snapshot: lidos do banco por id
    item_ids = [a.item_id for a in annexes if a.item_id]
    fetched = {i.id or 0: i for i in await s.ctx.characters.read(lambda uow: uow.items.by_ids(item_ids))}
    pet_ids = [i.object_id for i in fetched.values() if i.template_id == SYLPH]

    async def load(uow: UnitOfWork) -> list[Pet]:
        return [p for p in [await uow.pets.get(x) for x in pet_ids] if p is not None]

    held = {p.id: p for p in await s.ctx.characters.read(load)} if pet_ids else {}
    roster = BASE_SLOTS + rules.systems(snap).pet_slots
    now = s.ctx.clock.now()
    c = snap.character
    before = c.gold, c.point, c.gift_token, c.strategy
    result = pb.MailPickupRspMsg()
    taken: list[MailAnnex] = []
    new_items: list[Item] = []
    ledgers: list[CashLedger] = []
    new_pets: list[Pet] = []
    unwrapped: list[Item] = []
    for mail in mails:
        pos = positions.get(mail.id or 0, 0)
        wanted = [a for a in annexes if a.mail_id == mail.id and not a.taken and pos in (0, a.slot)]
        goods = [(a.template_id, a.count) for a in wanted if not a.item_id]
        carried = [_carried(snap, fetched, a.item_id) for a in wanted if a.item_id]
        sylphs = [i for i in carried if i is not None and i.template_id == SYLPH]
        carried = [i for i in carried if i is None or i.template_id != SYLPH]
        ok = bool(wanted) and items.fits(snap, goods, now) and all(items.known(s.ctx.templates, t) for t, _ in goods)
        ok = ok and None not in carried and len(bag.free_positions(snap, now)) >= len(carried) + len(goods)
        ok = ok and len(snap.pets) + len(sylphs) <= roster
        if ok:
            p0, g0 = c.point, c.gift_token
            new_items += items.grant(snap, goods)  # snapshot muda antes do save: nada de await no meio
            dp, dg = c.point - p0, c.gift_token - g0
            if dp or dg:  # diamante do correio (leilão, lance devolvido) também entra no cash_ledger
                ledgers.append(record_cash(c, dp, dg, "mail", f"mail:{mail.id}", now))
            for item in carried:
                assert item is not None
                if all(i is not item for i in snap.items):
                    snap.items.append(item)
                item.bag_type, item.object_id, item.pos = BagType.BAG, 0, bag.free_positions(snap, now)[0]
                new_items.append(item)
            for item in sylphs:
                unwrapped.append(item)
                if item in snap.items:
                    snap.items.remove(item)
                if (pet := held.get(item.object_id)) is not None:
                    take_back(snap, pet)
                    new_pets.append(pet)
                else:  # o vendedor apagou o personagem e o pet foi junto (cascata): só some o -900
                    s.log.warning("5022: Sylph do leilão sem o pet", item=item.id, pet=item.object_id)
            for a in wanted:
                a.taken = True
            taken += wanted
            mail.read_at = mail.read_at or now
        result.pickupResult.add(mailId=mail.id, attachIndex=pos, result=ok)
    if taken:
        await s.ctx.characters.save(
            c, *new_items, *new_pets, *taken, *ledgers, *(m for m in mails if m.read_at == now), delete=tuple(unwrapped)
        )
    if not taken:
        s.send(S_PICKUP, result)
        return
    # (visto) oficial_20261024-121659-1 #507-#535: um 115 por item e o 4476/4426/4484 de cada; 111 e 83 com a lista,
    # depois o 114 e o 4131
    for item in new_items:
        s.send(S_ITEMS, item_moved(item.bag_type, 0, item.pos, item, s.player_id))
        events.items_gained(s)
    if new_pets:
        s.send(S_PETS, pets_msg(snap, s.ctx.templates, new_pets))
    # TODO(inventado): o texto de moeda (ouro, Balens) no correio; só há captura de itens ("Soul Crystal x200")
    names = [f"{bag.name(s.ctx.templates, a.template_id)} x{a.count}" for a in taken]
    shop.alert(s, "Successfully retrieved " + ", ".join(names))
    s.send(S_PICKUP, result)
    update = pb.ReceiveMailMsg()
    for mail in mails:
        update.mailInfos.append(mailbox.info_msg(mail, annexes, c.nickname or ""))
    s.send(S_MAIL_UPDATE, update)
    if c.gold != before[0]:
        castle_yield(s)
    if (c.point, c.gift_token, c.strategy) != before[1:]:
        s.send(S_PLAYER, b.complete(player_info(s, snap)))


@router.on(9591)
async def mail_check(s: GameSession, msg: pb.MailCheckMsg) -> None:
    """Verificação do endereço de e-mail (``MailCheckManager``: op 1 pede o código, op 2 manda o PIN) com o prêmio
    ``mail_rewards`` do ConfigInfos (``ConfigInfoManager.getMailCheckPrize``, "-500,3000"). Estados do 337
    (``MailCheckFrame``): 0 enviar desligado, 1 código enviado (enviar ligado), 2 verificado (fecha e some o botão),
    3 recusado. TODO(inventado): sem SMTP, o código de 6 dígitos vai por correio do jogo; o prêmio também vai pelo
    correio. Uma vez só por personagem (EventState ``mail_check``: ``value`` -1 = verificado, senão o PIN)."""
    snap, now = s.snapshot, s.ctx.clock.now()
    assert snap is not None
    st = gev.state(snap, MAIL_CHECK_KEY, now)
    address = msg.mail.strip()[:64]
    letter: tuple[Mail, list[tuple[int, int]], list[Item]] | None = None
    if st.value == MAIL_VERIFIED:
        state = 2
    elif not _MAIL_RE.fullmatch(address):
        state = 3
    elif msg.op == 1:
        st.value, st.text, state = random.randint(100000, 999999), address, 1
        body = f"Your verification code is {st.value}."  # TODO(inventado): o texto do código
        letter = (Mail(s.player_id, now, "Email Verification", body, mail_type=MailType.SYSTEM,
                       send_type=SYSTEM_SENDER), [], [])  # fmt: skip
    elif msg.op == 2 and st.value > 0 and msg.pin == st.value and address == st.text:
        st.value, state = MAIL_VERIFIED, 2
        raw = rules.config(s.ctx.templates, "mail_rewards", "-500,3000")
        goods = [(int(a), int(n)) for a, n in (x.split(",") for x in raw.split("|") if x)]
        letter = (Mail(s.player_id, now, "Email Verified", "Email verification reward.", mail_type=MailType.SYSTEM,
                       send_type=SYSTEM_SENDER), goods, [])  # fmt: skip
    else:
        state = 3
    st.updated_at = now
    await shop.save_with_mail(s, [letter] if letter else [], st)
    s.log.info("9591", op=msg.op, estado=state)
    s.send(S_MAIL_CHECK, b.complete(pb.MailCheckMsg(op=msg.op, state=state, mail=address)))
