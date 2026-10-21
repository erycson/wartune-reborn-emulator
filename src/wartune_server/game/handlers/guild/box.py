"""Guilda: baú de prêmios."""

from __future__ import annotations

from datetime import datetime

from ....domain.models import (
    ConsortiaItem,
    Item,
    Mail,
    MailType,
    PlayerSnapshot,
)
from ....domain.repositories import UnitOfWork
from ....protocol.messages import wartune_pb2 as pb
from ... import bag
from ... import guild as gd
from ...builders import login as b
from ...mail import SYSTEM_SENDER
from ...mail import notify as notify_mail
from ...mail import stage as stage_mail
from ...router import router
from ...session import GameSession
from .common import S_BOX, S_BOX_ALLOT, S_ITEMS, _mine, _now, _profile, _refuse

# ---- baú de prêmios --------------------------------------------------------------------------

PER_MEMBER = 10  # ConsortiaPrizeAllotItem.changeReceviedCount: no máximo 10 por membro


def _box_msg(s: GameSession, guild_id: int) -> pb.ConsortiaStorageInfoMsg:
    out = pb.ConsortiaStorageInfoMsg()
    for i in s.ctx.guilds.box.get(guild_id, []):
        out.storageInfo.add(templateId=i.template_id, consortiaId=guild_id, count=i.count)
    return out


@router.on(8577)
async def box_check(s: GameSession, _: object) -> None:
    mine = _mine(s)
    s.send(S_BOX, b.complete(_box_msg(s, mine[0].id or 0) if mine else pb.ConsortiaStorageInfoMsg()))


@router.on(8579)
async def box_info(s: GameSession, msg: pb.ConsortiaTreasureBoxMsg) -> None:
    """Membros para distribuir um item do baú (4465)."""
    mine = _mine(s)
    if mine is None:
        _refuse(s, 8579, "sem guilda")
        return
    guild = mine[0]
    stored = next((i for i in s.ctx.guilds.box.get(guild.id or 0, []) if i.template_id == msg.templateId), None)
    out = pb.ConsortiaTreasureBoxMsg(
        consortiaId=guild.id,
        chairmanId=guild.chairman_id,
        templateId=msg.templateId,
        count=stored.count if stored else 0,
    )
    for m in s.ctx.guilds.members_of(guild.id or 0):
        c = _profile(s, m.character_id)
        if c is not None:
            out.playerInfo.add(
                job=c.job,
                nickName=c.nickname or "",
                level=c.grades,
                fightCapacity=c.fighting_capacity,
                userId=m.character_id,
                count=0,
                isReceived=False,  # ponytail: o oficial marca quem já recebeu; quando isso zera não está no cliente
            )
    s.send(S_BOX_ALLOT, b.complete(out))


async def _snapshot(s: GameSession, player_id: int) -> PlayerSnapshot:
    """Mochila de um membro: a da sessão se estiver online (ela é dona do snapshot), senão carrega do banco."""
    other = s.ctx.online.get(player_id)
    if other is not None and other.snapshot is not None:
        return other.snapshot
    return await s.ctx.characters.snapshot(player_id)


def _letter(s: GameSession, player_id: int, template_id: int, now: datetime) -> Mail:
    """Correio do sistema com o item; título e texto são o nome do item, como o casamento faz."""
    row = s.ctx.templates.get("ItemTempInfos", template_id)
    name = row.get("TemplateName", str(template_id)) if row is not None else str(template_id)
    return Mail(player_id, now, name, name, mail_type=MailType.SYSTEM, send_type=SYSTEM_SENDER)


@router.on(8578)
async def box_send(s: GameSession, msg: pb.ConsortiaTreasureBoxMsg) -> None:
    """O chefe distribui um item do baú: cada membro recebe na mochila, ou pelo correio se não couber.

    Lê as mochilas dos destinatários antes de mudar qualquer coisa, valida e muda o baú e as mochilas
    de uma vez, e grava tudo numa transação. ponytail: o correio por mochila cheia é dedução (o
    oficial não mostrou o caso); membro offline vê o item no próximo login (o 8224 recarrega o
    snapshot), e se ele logar durante a gravação também só no próximo login.
    """
    g = s.ctx.guilds
    mine = _mine(s)
    if mine is None or mine[1].duty_id != gd.CHAIRMAN:
        _refuse(s, 8578, "não é chefe")
        return
    guild = mine[0]
    wanted = [(p.userId, p.count) for p in msg.playerInfo if p.count > 0]
    snaps: dict[int, PlayerSnapshot] = {}
    for uid, _ in wanted:
        if uid in g.members:
            snaps[uid] = await _snapshot(s, uid)
    for uid in snaps:  # quem logou durante as leituras: a sessão dele é a dona da mochila agora
        other = s.ctx.online.get(uid)
        if other is not None and other.snapshot is not None:
            snaps[uid] = other.snapshot
    box = g.box.get(guild.id or 0, [])
    stored = next((i for i in box if i.template_id == msg.templateId), None)
    total = sum(n for _, n in wanted)
    members_ok = all(
        uid in snaps and (m := g.members.get(uid)) is not None and m.consortia_id == guild.id for uid, _ in wanted
    )
    too_many = any(n > PER_MEMBER for _, n in wanted)
    if stored is None or not wanted or not members_ok or too_many or total > stored.count:
        _refuse(s, 8578, "item, membro ou quantidade inválida", item=msg.templateId)
        return
    now = _now(s)
    stored.count -= total
    gone: list[object] = []
    changed: list[object] = [stored]
    if stored.count <= 0:
        box.remove(stored)
        gone, changed = [stored], []
    moved: dict[int, list[Item]] = {}
    letters: list[tuple[Mail, list[tuple[int, int]]]] = []
    for uid, n in wanted:
        snap = snaps[uid]
        if bag.fits(snap, s.ctx.templates, [(msg.templateId, n)], now):
            got = bag.add(snap, s.ctx.templates, msg.templateId, n, now)
            moved.setdefault(uid, []).extend(got)
            changed += got
        else:
            s.log.info("baú: mochila cheia, item vai pelo correio", jogador=uid, item=msg.templateId)
            letters.append((_letter(s, uid, msg.templateId, now), [(msg.templateId, n)]))

    async def change(uow: UnitOfWork) -> None:
        for entity in gone:
            await uow.delete(entity)
        for entity in changed:
            await uow.save(entity)
        for letter, goods in letters:
            await stage_mail(uow, letter, goods)

    await s.ctx.characters.write(change)
    for uid, got in moved.items():
        other = s.ctx.online.get(uid)
        if other is not None and other.snapshot is not None:
            other.send(S_ITEMS, bag.moved(got, uid))
    for letter, _ in letters:
        notify_mail(s.ctx.online, letter)
    s.send(S_BOX, b.complete(_box_msg(s, guild.id or 0)))


def add_to_box(s: GameSession, guild_id: int, template_id: int, count: int) -> ConsortiaItem:
    """Prêmio para o baú da guilda (altar, guerra); quem chama grava o retorno."""
    box = s.ctx.guilds.box[guild_id]
    item = next((i for i in box if i.template_id == template_id), None)
    if item is None:
        item = ConsortiaItem(guild_id, template_id, count=0)
        box.append(item)
    item.count += count
    return item
