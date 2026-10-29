"""Lote 4 da auditoria: correio na varredura, presentes a amigo, leitura offline e subida de nível (um por item)."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest

from tests.game.harness import Game, logged_in
from tests.game.test_varredura import CALORN, _ready, _rsp, _start
from tests.test_end_to_end import TEMPLATES
from wartune_server.domain.models import BagType, Item, Pet, PlayerSnapshot
from wartune_server.game import bag, rewards, rules
from wartune_server.game import events as ev
from wartune_server.game.handlers import player
from wartune_server.game.handlers.vip import _vip_expiry
from wartune_server.game.session import GameSession
from wartune_server.protocol.messages import wartune_pb2 as pb
from wartune_server.services.clock import FakeClock

pytestmark = pytest.mark.skipif(not TEMPLATES.exists(), reason="precisa de data/templates")

NOW = datetime(2026, 1, 1, 12, tzinfo=UTC)
FILLER = 208003  # Bullhorn (Small): só ocupa espaço


def _s(g: Game) -> GameSession:
    s = g.server.online.get(g.user_id)
    assert s is not None and s.snapshot is not None
    return s


def _snap(g: Game) -> PlayerSnapshot:
    snap = _s(g).snapshot
    assert snap is not None
    return snap


async def _mails(g: Game, user_id: int) -> list:  # type: ignore[type-arg]
    chars = g.server.services.characters
    return list(await chars.read(lambda uow: uow.mails.by_receiver(user_id)))


async def _offline(a: Game, b: Game) -> None:
    b.client.writer.close()
    for _ in range(40):
        if a.server.online.get(b.user_id) is None:
            return
        await a.idle(0.05)
    raise AssertionError("o outro jogador não saiu")


async def test_1_varredura_com_mochila_cheia_manda_a_carta_pelo_correio(tmp_path: Path) -> None:
    clock = FakeClock(NOW)
    async with logged_in(tmp_path, novice=19000, clock=clock) as g:
        snap = _ready(g, clock)
        for pos in bag.free_positions(snap, clock.now()):
            snap.items.append(Item(g.user_id, FILLER, count=1, bag_type=BagType.BAG, pos=pos))
        g.client.send(8528, _start(2))
        await g.until(4425)
        clock.advance(600)
        g.client.send(8528, pb.CampaignSweepReq(sweepType=1, opType=3, campaignId=CALORN))
        got = await g.until(4425) + await g.idle()
        poll = _rsp(got)
        assert [r.finishCount for r in poll.result] == [1, 2]  # as duas rodadas seguiram
        cards = [i.templateId for r in poll.result for i in r.items if i.templateId > 0]
        assert len(cards) == 2
        assert 148 in [p.code for p in got]
        mails = await _mails(g, g.user_id)
        annexes = await g.server.services.characters.read(lambda uow: uow.mails.annexes([m.id or 0 for m in mails]))
        assert sorted(a.template_id for a in annexes) == sorted(cards)


async def test_2_vip_e_contrato_de_presente_a_amigo_offline_e_online(tmp_path: Path) -> None:
    async with logged_in(tmp_path, novice=19000) as a:
        b = await a.join("bruxa")
        await b.idle()
        me = _snap(a)
        me.character.point = 10_000
        before = me.character.point

        a.client.send(8513, pb.VipOpenInfoMsg(isFriend=True, friendId=999999, days=31))  # não existe: nada cobrado
        await a.idle()
        assert me.character.point == before

        # contrato do rei ao amigo online: vai pela sessão dele, que recebe o 4434 e a carta
        a.client.send(8540, pb.KingContractBuyMsg(ids=[2], friendId=b.user_id))
        got = await b.until(4434) + await b.idle()
        assert 148 in [p.code for p in got]
        assert ev.contract_end(_snap(b), 2) is not None and ev.contract_end(me, 2) is None
        assert me.character.point == before - 375

        # VIP ao amigo offline: gravado no banco, pago por quem dá
        await _offline(a, b)
        paid = me.character.point
        a.client.send(8513, pb.VipOpenInfoMsg(isFriend=True, friendId=b.user_id, days=31))
        await a.idle()
        assert me.character.point < paid and _vip_expiry(me) is None
        stored = await a.server.services.characters.snapshot(b.user_id)
        assert _vip_expiry(stored) is not None and ev.contract_end(stored, 2) is not None
        texts = [m.title for m in await _mails(a, b.user_id)]
        assert any("VIP" in t for t in texts) and any("Bounty Helper" in t for t in texts)


async def test_3_montaria_e_pets_de_jogador_offline(tmp_path: Path) -> None:
    async with logged_in(tmp_path, novice=19000) as a:
        b = await a.join("bruxa")
        await b.idle()
        other = _snap(b)
        sy = rules.systems(other)
        sy.mount_template = 1000
        pet = Pet(b.user_id, 101103, "Amazon", pos=0)
        other.pets.append(pet)
        await b.server.services.characters.save(sy, pet)
        await _offline(a, b)

        a.client.send(8529, pb.MountEditMsg(op=5, param1=b.user_id))
        mount = pb.MountInfoMsg.FromString((await a.until(4459))[-1].body)
        assert mount.mountTempId == 1000
        a.client.send(8702, pb.PlayerPetOpMsg(petId=b.user_id))
        assert (await a.until(4608))[-1].code == 4608


async def test_4_exp_que_sobe_nivel_manda_o_pacote_completo(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    async with logged_in(tmp_path, novice=19000) as g:
        s, snap = _s(g), _snap(g)
        await g.idle()
        calls: list[int] = []

        async def fake_push(_: GameSession, before: int) -> None:
            calls.append(before)

        monkeypatch.setattr(player, "push_level", fake_push)
        level = snap.character.grades
        drops = [(rewards.EXP, 10)]
        rewards.grant(snap, s.ctx.templates, drops)
        await player.granted(s, drops, [], "", chat=False)
        assert calls == [] and snap.character.grades == level  # sem subir: só o 150
        assert 150 in [p.code for p in await g.idle()]

        need = dict(rules.grade_steps(s.ctx.templates))[level + 1] - snap.character.total_gp
        drops = [(rewards.EXP, need)]
        rewards.grant(snap, s.ctx.templates, drops)
        await player.granted(s, drops, [], "", chat=False)
        assert snap.character.grades == level + 1 and calls == [level]
