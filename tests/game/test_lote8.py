"""Lote 8 da auditoria: altar x10, terras de mascote da fazenda (ops 12-16), crescimento do mascote no treino,
5006 Kyanite/Contribution Badge, verificação de e-mail 9591 e Venus Crystal pela missão do casal."""

from __future__ import annotations

from datetime import timedelta
from pathlib import Path

import pytest

from tests.game.harness import Game, logged_in
from tests.game.test_guild import _char, _create, _guild, _one, _session
from tests.game.test_lote5_social import _married
from tests.game.test_shop import me
from wartune_server.domain.models import Item, Pet
from wartune_server.game import events as ev
from wartune_server.game import rewards
from wartune_server.game.handlers import farm_pets, marriage
from wartune_server.game.handlers.guild import altar
from wartune_server.protocol.messages import wartune_pb2 as pb
from wartune_server.services.clock import FakeClock


def _vip(g: Game) -> None:
    snap, now = _session(g).snapshot, _session(g).ctx.clock.now()
    assert snap is not None
    st = ev.state(snap, "vip", now)
    st.value, st.text = 10**9, (now + timedelta(days=1)).strftime(ev.TIME_FMT)  # VIP no último nível


async def test_1_altar_x10_so_com_vip_6_e_faz_o_que_o_dia_deixa(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    async with logged_in(tmp_path, novice=19000) as a:
        await _create(a)
        c = _char(a)
        c.consortia_offer = 10_000
        _guild(a).altar_level = 1
        monkeypatch.setattr(altar._rng, "choice", lambda xs: 2)  # casa 2: Lvl. 3 Endurance Potion
        a.client.send(5145, pb.SimplePropertyMsg(param1=10))  # sem VIP: recusa
        assert _one(await a.idle(), 45, pb.ConsortiaMsg).blessSite == -1

        _vip(a)
        a.client.send(5145, pb.SimplePropertyMsg(param1=10))
        got = await a.idle()
        bless = _one(got, 45, pb.ConsortiaMsg)
        limit = 3  # UpGradeTempInfos tipo 3 nível 1: Property2
        assert bless.blessLeftTime == limit and c.consortia_offer == 10_000 - 20 * limit
        snap = me(a)
        assert sum(i.count for i in snap.items if i.template_id == 2014003) == limit - 1  # n-1 na hora
        member = _guild_member(a)
        assert (member.bless_item, member.bless_count) == (2014003, limit)  # a última fica no altar


def _guild_member(g: Game):  # type: ignore[no-untyped-def]
    from wartune_server.game.handlers.guild.common import _mine

    mine = _mine(_session(g))
    assert mine is not None
    return mine[1]


async def test_2_e_3_treino_na_fazenda_come_e_cresce(tmp_path: Path) -> None:
    clock = FakeClock()
    async with logged_in(tmp_path, novice=19000, clock=clock) as g:
        snap = me(g)
        snap.character.grades = 60
        pet = Pet(g.user_id, 101103, "Amazon", pos=0, grade=1)
        snap.pets.append(pet)
        await g.server.services.characters.save(snap.character, pet)
        g.client.send(15044, pb.FarmOperReqMsg(friendId=g.user_id, opType=0))
        info = pb.FarmInfoRspMsg.FromString((await g.until(4386))[-1].body)
        assert [(p.pos, p.petId) for p in info.petInfo] == [(0, 0), (1, 0)]  # 2 terras abertas e vazias

        g.client.send(15044, pb.FarmOperReqMsg(friendId=g.user_id, opType=12, pos=0, bagPos=pet.id, templateId=12))
        got = await g.idle()
        land = _one(got, 4387, pb.FarmInfoRspMsg).petInfo[0]
        assert (land.pos, land.petId, land.state) == (0, pet.id, 0)
        assert _one(got, 4540, pb.PlayerPetMsg).petInfo[0].isPractice
        g.client.send(8621, pb.PlayerPetOpMsg(opType=9, petId=pet.id))  # treinando não vai à batalha
        await g.idle()
        assert not pet.is_fight

        g.client.send(15044, pb.FarmOperReqMsg(friendId=g.user_id, opType=15, pos=0, bagPos=pet.id, templateId=10))
        assert _one(await g.idle(), 4387, pb.FarmInfoRspMsg).petInfo[0].state == 0  # parte 0: ainda não come
        clock.advance(3 * 3600)  # 12 h em 10 partes: parte 2
        g.client.send(15044, pb.FarmOperReqMsg(friendId=g.user_id, opType=15, pos=0, bagPos=pet.id, templateId=10))
        assert _one(await g.idle(), 4387, pb.FarmInfoRspMsg).petInfo[0].state == 2

        g.client.send(15044, pb.FarmOperReqMsg(friendId=g.user_id, opType=14, pos=0, bagPos=pet.id))
        await g.idle()
        assert pet.gp == 0  # ainda treinando
        clock.advance(9 * 3600)
        g.client.send(15044, pb.FarmOperReqMsg(friendId=g.user_id, opType=14, pos=0, bagPos=pet.id))
        got = await g.idle()
        assert _one(got, 4387, pb.FarmInfoRspMsg).petInfo[0].petId == 0
        assert pet.gp == 12 * 1000 * 110 // 100 and pet.grade > 1  # 1 comida: +10%
        assert not farm_pets.practicing(snap)

        g.client.send(15044, pb.FarmOperReqMsg(friendId=g.user_id, opType=16, pos=-1, bagPos=pet.id, templateId=12))
        assert _one(await g.idle(), 4387, pb.FarmInfoRspMsg).guardPetInfo.petId == pet.id


async def test_4_kyanite_e_insignia_de_contribuicao(tmp_path: Path) -> None:
    async with logged_in(tmp_path, novice=19000) as g:
        snap = me(g)
        snap.character.grades = 40
        c = snap.character
        crystals, offer = c.crystals, c.consortia_offer
        for pos, tid in ((20, 2030201), (21, 2030801)):  # Kyanite Pack 1000, Lvl. 1 Contribution Badge 50
            item = Item(g.user_id, tid, pos=pos, count=2)
            snap.items.append(item)
            await g.server.services.characters.save(item)
            g.client.send(5006, pb.ItemUseMsg(pos=pos, count=2, bagType=1))
            await g.until(3)
        assert (c.crystals - crystals, c.consortia_offer - offer) == (2000, 100)


async def test_5_email_9591_codigo_pin_e_premio_uma_vez(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from wartune_server.game.handlers import mail

    monkeypatch.setattr(mail.random, "randint", lambda a, b: 123456)
    async with logged_in(tmp_path, novice=19000) as g:

        async def check(op: int, pin: int = 0, address: str = "maga@example.com") -> int:
            g.client.send(9591, pb.MailCheckMsg(op=op, mail=address, pin=pin))
            return pb.MailCheckMsg.FromString((await g.until(337))[-1].body).state

        assert await check(1, address="sem-arroba") == 3
        assert await check(1) == 1
        assert await check(2, pin=111111) == 3
        assert await check(2, pin=123456) == 2
        assert await check(2, pin=123456) == 2  # já verificado: sem segundo prêmio

        chars = g.server.services.characters
        mails = list(await chars.read(lambda uow: uow.mails.by_receiver(g.user_id)))
        annexes = await chars.read(lambda uow: uow.mails.annexes([m.id or 0 for m in mails]))
        assert len(mails) == 2 and [(x.template_id, x.count) for x in annexes] == [(-500, 3000)]  # código e prêmio
        assert any("123456" in m.contents for m in mails)


async def test_6_venus_crystal_pela_missao_do_casal(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    async with logged_in(tmp_path, novice=19000) as a:
        await _married(a)
        talk = next(r["TemplateId"] for r in _session(a).ctx.templates.find("RewardCondictionInfos", CondictionType="16")
                    if int(r["TemplateId"]) // 1000 == 4)  # fmt: skip
        monkeypatch.setattr(marriage.random, "choice", lambda pool: int(talk))
        a.client.send(8774, pb.MarriageOpMsg(opType=marriage.TASK_ACCEPT))
        await a.until(marriage.S_TASKS)
        a.client.send(8774, pb.MarriageOpMsg(opType=marriage.TASK_TALK))
        got = await a.until(4725)
        st = ev.peek(me(a), rewards.ETERNAL_KEY)
        assert st is not None and st.value == 5
        tokens = pb.PlayerTokenInfoMsg.FromString(got[-1].body).tokenInfos
        assert next(t.amount for t in tokens if t.masterType == 12) == 5


async def test_4b_203_tropas_contrato_e_medalha(tmp_path: Path) -> None:
    async with logged_in(tmp_path, novice=19000) as g:
        snap = me(g)
        snap.character.grades = 40
        c = snap.character
        geste = c.geste
        for pos, tid in ((20, 2030901), (21, 2031401), (22, 2032201)):  # Huntera x200, Pocket Market, Medallion
            item = Item(g.user_id, tid, pos=pos, count=1)
            snap.items.append(item)
            await g.server.services.characters.save(item)
            g.client.send(5006, pb.ItemUseMsg(pos=pos, count=1, bagType=1))
            await g.idle()
        assert next(p.castle_count for p in snap.pawns if p.template_id == 9001) == 200
        assert ev.contract_end(snap, 1) is not None and ev.contract_end(snap, 2) is None  # só o contrato 1
        assert c.geste - geste == 500
        assert not [i for i in snap.items if i.template_id in (2030901, 2031401, 2032201)]


async def test_2b_amigo_alimenta_e_o_dono_ve(tmp_path: Path) -> None:
    from tests.game.test_castelo import _friends

    clock = FakeClock()
    async with logged_in(tmp_path, novice=19000, clock=clock) as g:
        other = await g.join("outro")  # type: ignore[call-arg]
        await g.idle()
        await _friends(g, other)
        snap = me(g)
        snap.character.grades = 60
        pet = Pet(g.user_id, 101103, "Amazon", pos=0)
        snap.pets.append(pet)
        await g.server.services.characters.save(snap.character, pet)
        g.client.send(15044, pb.FarmOperReqMsg(friendId=g.user_id, opType=12, pos=1, bagPos=pet.id, templateId=12))
        await g.idle()
        clock.advance(4 * 3600)
        other.client.send(8231, pb.FriendUserIdsMsg(friendId=[g.user_id]))
        states = pb.LoadFarmRsp.FromString((await other.until(4190))[-1].body).friendFarmState
        assert next(x for x in states if x.userId == g.user_id).isFeed
        other.client.send(15044, pb.FarmOperReqMsg(friendId=g.user_id, opType=15, pos=1, bagPos=pet.id, templateId=10))
        assert _one(await other.idle(), 4387, pb.FarmInfoRspMsg).petInfo[0].state == 3
        log = _one(await g.idle(), 145, pb.FarmLogRsp)
        assert log.operUserId == other.user_id
