"""Batalha de veículos (m17, campanha 3001): a partida em memória (``game/vehicles.py``) e a fila pelo socket."""

from __future__ import annotations

import functools
import random
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from google.protobuf.message import Message

from tests.game.harness import logged_in
from wartune_server.game import vehicles as vh
from wartune_server.game.handlers import vehicle
from wartune_server.protocol.messages import wartune_pb2 as pb
from wartune_server.services.clock import FakeClock
from wartune_server.templates.repository import GameTemplates

TEMPLATES = Path("data/templates/tempinfos.xml")
pytestmark = pytest.mark.skipif(not TEMPLATES.exists(), reason="precisa de data/templates")
OPEN = datetime(2026, 10, 20, 10, 0, tzinfo=UTC)  # MatchOfVehicleTime 10:00,10:25 (UTC nos testes)
TURRET = 1  # Turbo Turret: ataque 100, defesa 50, vida 5000; normal = Mortar (Power 100, 500 px, recarga 3 s)
HIT = 100 * 100 // 100 - 50 // 2  # dano do Mortar num Turbo Turret (_raw)
SHIELD, IMMUNE_BUFF, TRAP = 18, 17, 7


class Sure(random.Random):
    """``randrange`` sempre 99: ninguém esquiva, só chance de 100% acontece."""

    def randrange(self, *_: object, **__: object) -> int:  # type: ignore[override]
        return 99


@functools.cache
def _templates() -> GameTemplates:
    return GameTemplates.parse(TEMPLATES.read_bytes())


Sent = list[tuple[int, int, Message]]


def _match(start: datetime = OPEN) -> tuple[vh.Match, Sent]:
    sent: Sent = []
    end = start + timedelta(minutes=25)
    return vh.Match(_templates(), start, end, lambda p, c, m: sent.append((p, c, m)), rnd=Sure(1)), sent


def _tank(pid: int, team: int, exp: int = 0) -> vh.Tank:
    t = vh.new_tank(_templates(), pid, f"p{pid}", TURRET, exp, team, guild="", vip=0)
    assert t is not None
    return t


def _duel() -> tuple[vh.Match, Sent]:
    """Um de cada lado, no meio do mapa (sem tiles), e o 2 já sem a proteção da entrada."""
    m, sent = _match()
    m.join(_tank(1, vh.RED), OPEN)
    m.join(_tank(2, vh.BLUE), OPEN)
    m.tanks[2].x, m.tanks[2].y = vh.CENTER  # a velocidade não deixa saltar do ponto sorteado no mesmo instante
    assert m.move(2, [vh.CENTER], OPEN)
    sent.clear()
    return m, sent


def _shoot(target: int) -> pb.VehicleAttackReqMsg:
    return pb.VehicleAttackReqMsg(skillId=1, suffererId=[target], effectX=vh.CENTER[0], effectY=vh.CENTER[1])


def _codes(sent: Sent, pid: int) -> list[int]:
    return [c for p, c, _ in sent if p == pid]


def test_join_order_and_max_hp() -> None:
    m, sent = _match()
    m.join(_tank(1, vh.RED), OPEN)
    assert _codes(sent, 1)[:3] == [4474, 4517, 4518]
    sent.clear()
    m.join(_tank(2, vh.BLUE), OPEN)
    assert _codes(sent, 2)[:3] == [4474, 4517, 4518]
    [roster] = [msg for p, c, msg in sent if p == 2 and c == 4517]
    assert isinstance(roster, pb.PlayerVehicleListMsg)
    assert {v.playerId: (v.hp, v.templateId) for v in roster.vehicles} == {1: (5000, TURRET), 2: (5000, TURRET)}
    assert 4513 in _codes(sent, 1)  # o novo para quem já estava
    assert m.tanks[2].has(vh.E_INVINCIBLE)  # 10 s de proteção ao entrar
    grade = vh.tank_grade(_templates(), 10**9)
    assert grade > 1 and _tank(3, vh.RED, 10**9).max_hp == 5000 + (grade - 1) * 100  # PlayerVehicleInfo.totalHp


def test_protection_cooldown_and_damage() -> None:
    m, sent = _match()
    m.join(_tank(1, vh.RED), OPEN)
    m.join(_tank(2, vh.BLUE), OPEN)
    assert not m.cast(1, _shoot(2), OPEN)  # o 2 ainda está protegido
    m.tanks[2].x, m.tanks[2].y = vh.CENTER
    assert m.move(2, [vh.CENTER], OPEN)  # andar tira a proteção
    assert m.cast(1, _shoot(2), OPEN)
    assert m.tanks[2].hp == 5000 - HIT
    [rsp] = [msg for p, c, msg in sent if p == 2 and c == 4520]
    assert isinstance(rsp, pb.VehicleAttackRspMsg)
    assert [(h.affecteId, h.value) for h in rsp.playerHurtDataList] == [(2, HIT)]
    assert m.scores[vh.RED] == HIT // vh.MATCH_RULES["score_damage"]
    assert not m.cast(1, _shoot(2), OPEN + timedelta(seconds=1))  # recarga de 3 s
    assert m.cast(1, _shoot(2), OPEN + timedelta(seconds=3))
    assert not m.cast(2, _shoot(2), OPEN + timedelta(seconds=3))  # no próprio time


def test_kill_reborn_time_and_revive() -> None:
    m, sent = _duel()
    m.tanks[2].hp = 10
    assert m.cast(1, _shoot(2), OPEN)
    [hp] = [v for p, c, msg in sent if p == 1 and c == 4513 for v in msg.vehicles if v.playerId == 2]  # type: ignore[attr-defined]
    assert (hp.hp, hp.rebornTime) == (0, 30)  # revivalTime 30
    assert m.scores[vh.RED] == HIT // vh.MATCH_RULES["score_damage"] + vh.MATCH_RULES["score_kill"]
    assert not m.cast(1, _shoot(2), OPEN + timedelta(seconds=3))  # morto não é alvo
    m.tick(OPEN + timedelta(seconds=29))
    assert not m.tanks[2].alive
    m.tick(OPEN + timedelta(seconds=30))
    assert m.tanks[2].hp == 5000 and m.tanks[2].has(vh.E_INVINCIBLE)


def test_shield_and_immunity() -> None:
    m, _ = _duel()
    m.add_buff(m.tanks[2], SHIELD, OPEN)
    m.tanks[2].buffs[next(iter(m.tanks[2].buffs))].left = HIT + 5
    assert m.cast(1, _shoot(2), OPEN)
    assert m.tanks[2].hp == 5000  # o escudo segurou tudo (-3)
    assert m.cast(1, _shoot(2), OPEN + timedelta(seconds=3))
    assert m.tanks[2].hp == 5000 - (HIT - 5) and not m.tanks[2].has(vh.E_SHIELD)
    m.add_buff(m.tanks[2], IMMUNE_BUFF, OPEN)
    before = m.tanks[2].hp
    assert m.cast(1, _shoot(2), OPEN + timedelta(seconds=6))
    assert m.tanks[2].hp == before


def test_trap_and_pickup() -> None:
    m, sent = _duel()
    t = m.tanks[1]
    t.extra, t.extra_left = TRAP, 1
    assert m.cast(1, pb.VehicleAttackReqMsg(skillId=TRAP, effectX=vh.CENTER[0], effectY=vh.CENTER[1]), OPEN)
    assert t.extra == 0  # o último uso some da tecla Q
    assert m.move(2, [vh.CENTER], OPEN)  # o inimigo pisa na armadilha
    assert m.tanks[2].hp == 5000 - vh.TRAP_DAMAGE
    assert not [n for n in m.nodes.values() if n.type == vh.NODE_TRAP]

    m.tick(OPEN + timedelta(seconds=1))  # primeira renovação das caixas
    [box] = [n for n in m.nodes.values() if n.type == vh.NODE_PROP]  # sem tiles: uma no meio
    sent.clear()
    assert m.pickup(1, box.node_id, OPEN + timedelta(seconds=1))
    assert t.extra == box.skill and box.node_id not in m.nodes
    assert 4521 in _codes(sent, 1)


def test_boss_after_five_minutes() -> None:
    m, sent = _duel()
    m.tick(OPEN + timedelta(seconds=vh.BOSS_AFTER))
    boss = m.boss()
    assert boss is not None and boss.hp == 10000 and boss.hero == vh.BOSS_TEMPLATE
    m.tick(OPEN + timedelta(seconds=vh.BOSS_AFTER + 5))
    assert 4524 in _codes(sent, 1)  # o círculo do golpe
    m.tanks[1].buffs.clear()
    m.tanks[2].buffs.clear()
    m.tick(OPEN + timedelta(seconds=vh.BOSS_AFTER + 7))
    assert m.tanks[1].hp < 5000 and m.tanks[2].hp < 5000


def test_end_and_one_reward_per_window() -> None:
    m, sent = _duel()
    assert not m.ended(OPEN)
    m.scores[vh.RED] = vh.LEAD_END
    m.tanks[1].score = vh.LOW_SCORE
    assert m.ended(OPEN)
    rewarded: set[int] = set()
    rewards = {r.player_id: r for r in m.finish(rewarded)}
    assert rewards[1].items == ((vh.VICTORY, 1), (vh.RANK_PACKS[0], 1))
    assert rewards[2].items == ((vh.FAILURE, 1), (vh.RUNESTONE, vh.MATCH_RULES["runestones"]))  # menos de 200 pontos
    [end] = [msg for p, c, msg in sent if p == 1 and c == 4514]
    assert isinstance(end, pb.VehicleCampaignDetailMsg) and end.winner == vh.RED
    assert [line.awardPropId for line in end.scroeList] == [vh.VICTORY, vh.FAILURE]

    again, _ = _duel()
    assert again.finish(rewarded) == []  # mesma janela: só o placar

    m, _ = _duel()
    m.leave(2, OPEN)
    assert m.ended(OPEN) and m.winner() == vh.RED  # o outro lado saiu todo
    m, _ = _duel()
    assert m.ended(m.end)


def test_arena_places_both_sides() -> None:
    arena = vh.Arena()
    win = (OPEN, OPEN + timedelta(minutes=25))
    arena.enqueue([1])
    assert arena.place(_templates(), win, OPEN, lambda *_: None) == []  # sozinho não abre partida
    arena.enqueue([2, 3])
    placed = arena.place(_templates(), win, OPEN, lambda *_: None)
    assert sorted((g, team) for _, g, team in placed) == [([1], vh.RED), ([2, 3], vh.BLUE)]
    assert not arena.enqueue([1])  # já tem lugar
    arena.enqueue([4])
    [(match, group, team)] = arena.place(_templates(), win, OPEN, lambda *_: None)
    assert match is placed[0][0] and team == vh.RED  # o lado com menos gente


async def test_quick_play_enters_the_tank_scene(tmp_path: Path) -> None:
    clock = FakeClock(OPEN)
    async with logged_in(tmp_path, novice=19000, clock=clock) as a:
        b = await a.join("bruxa")
        await a.idle()  # a bruxa chegando na cidade do céu
        sessions = [a.server.online.get(g.user_id) for g in (a, b)]
        for s in sessions:
            assert s is not None and s.snapshot is not None
            s.snapshot.character.grades = vh.MIN_LEVEL
        a.client.send(8608)
        assert [p.code for p in await a.idle()] == [4525]
        b.client.send(8608)
        for g, first in ((a, []), (b, [4525])):  # (a saída da cidade do céu vai junto)
            got = [p.code for p in await g.idle() if p.code in (4525, 125, 4474, 4517, 4518)]
            assert got[: len(first) + 4] == [*first, 125, 4474, 4517, 4518]
        ctx = sessions[0].ctx  # type: ignore[union-attr]
        match = ctx.vehicles.match_of(a.user_id)
        assert match is not None and set(match.tanks) == {a.user_id, b.user_id}

        a.client.send(8610)  # o vermelho sai: o azul ganha sozinho
        got = await b.idle()
        assert [p.code for p in got if p.code in (4523, 4514, 4515)] == [4523, 4514, 4515]
        assert ctx.vehicles.matches == []
        mails = await ctx.characters.read(lambda uow: uow.mails.by_receiver(b.user_id))
        annexes = await ctx.characters.read(lambda uow: uow.mails.annexes([m.id or 0 for m in mails]))
        assert {(x.template_id, x.count) for x in annexes} == {
            (vh.VICTORY, 1),
            (vh.RUNESTONE, vh.MATCH_RULES["runestones"]),
        }
        task = ctx.vehicles.task
        if task is not None:
            task.cancel()  # type: ignore[attr-defined]


async def test_vehicle_room_start_and_cancel(tmp_path: Path) -> None:
    """VehicleRoomFrame: sala tipo 2 (campanha 3001); o dono, com todos prontos, manda 5039 e todos recebem o 25
    estado 2 (o relógio); o Cancel do dono (5037 estado 1) tira a sala da fila."""
    clock = FakeClock(OPEN)
    async with logged_in(tmp_path, novice=19000, clock=clock) as a:
        b = await a.join("bruxa")
        for g in (a, b):
            s = a.server.online.get(g.user_id)
            assert s is not None and s.snapshot is not None
            s.snapshot.character.grades = vh.MIN_LEVEL
        a.client.send(5023, pb.RoomReqMsg(capacity=4, roomType=2))
        room = next(pb.RoomMsg.FromString(p.body) for p in await a.idle() if p.code == 12)
        assert (room.roomType, room.campaignId) == (2, vh.CAMPAIGN)
        b.client.send(5026, pb.RoomReqMsg(roomType=0))  # a lista PvE não mostra a sala de veículo
        assert not next(pb.RoomListRspMsg.FromString(p.body) for p in await b.idle() if p.code == 13).room
        b.client.send(5024, pb.RoomReqMsg(roomId=room.roomId, roomType=2))
        await b.idle()
        a.client.send(5039, pb.CampaignReqMsg())  # b ainda não está pronto
        await a.idle()
        s = a.server.online.get(a.user_id)
        assert s is not None and s.ctx.vehicles.queue == []
        b.client.send(5036, pb.RoomReqMsg(state=1))
        await b.idle()
        a.client.send(5039, pb.CampaignReqMsg())
        for g in (a, b):
            [state] = [pb.RoomStateRspMsg.FromString(p.body) for p in await g.idle() if p.code == 25]
            assert state.roomState == 2
        assert s.ctx.vehicles.queue == [[a.user_id, b.user_id]]  # um grupo, sem o outro lado ainda
        a.client.send(5037, pb.RoomReqMsg(state=1))
        assert 25 in [p.code for p in await b.idle()]
        assert s.ctx.vehicles.queue == []

        a.client.send(5039, pb.CampaignReqMsg())  # de novo, e a janela fecha sem o outro lado
        await b.idle()
        clock.advance(30 * 60)
        await vehicle.match_up(s.ctx)
        [state] = [pb.RoomStateRspMsg.FromString(p.body) for p in await b.idle() if p.code == 25]
        assert state.roomState == 1 and s.ctx.vehicles.queue == []
