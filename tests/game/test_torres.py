"""Torres 8200-8204 (game/torres): Tower of Kings e The Spire, mapas da migração 0102 (TODO(inventado)
``tools/gera_masmorras.py torres``), entrando pela sala (5023, 5024, 5036, 5039)."""

from __future__ import annotations

import asyncio
import json
from datetime import UTC, datetime
from pathlib import Path

import pytest

from tests.game.harness import Game, logged_in
from tests.game.test_batalha import _battle, needs_templates
from tests.game.test_masmorra_1001 import back_to_map, battle, fast_battles  # noqa: F401  (fixture)
from tests.game.test_masmorras_grupo import _start, _weak
from tests.test_end_to_end import TEMPLATES
from wartune_server.domain.models import PlayerSnapshot
from wartune_server.game import battle as battle_mod
from wartune_server.game import battle as bt
from wartune_server.game import daily, torres
from wartune_server.game import events as ev
from wartune_server.protocol.messages import wartune_pb2 as pb
from wartune_server.services.clock import FakeClock

pytestmark = pytest.mark.skipif(not TEMPLATES.exists(), reason="precisa de data/templates")
VERSIONS = Path("src/wartune_server/persistence/migrations/versions")
KING_FIGHTS = (820002, 820003, 820004, 820009, 820010)  # (internet) cinco níveis


def _snap(g: Game) -> PlayerSnapshot:
    s = g.server.online.get(g.user_id)
    assert s is not None and s.snapshot is not None
    return s.snapshot


def _kings(got: list) -> list[pb.KingTowerInfoMsg]:
    return [pb.KingTowerInfoMsg.FromString(p.body) for p in got if p.code == 4900]


def test_cinco_torres_geradas() -> None:
    made = json.loads((VERSIONS / "0102_torres.json").read_text(encoding="utf-8"))
    assert sorted(made) == ["8200", "8201", "8202", "8203", "8204"]
    assert all(c["inventado"] == [int(k)] for k, c in made.items())
    spire = [b for b in made["8201"]["battles"].values() if b.get("trial")]
    assert len(spire) == 1 and len(spire[0]["reinforce"]) == 23 and spire[0]["battleType"] == 25  # 24 chefes
    assert (
        made["8204"]["battles"]["820402"]["gpBonus"] == 2_500_000
        and made["8200"]["battles"]["820002"]["battleType"] == 290
    )
    assert not any("cards" in m for c in made.values() for m in c["maps"].values())  # sem carta no fim
    hp = [made[k]["battles"][f"{k}02"]["soldiers"][0]["hp"] for k in ("8200", "8202", "8203", "8204")]
    assert hp == sorted(hp) and len(set(hp)) == 4  # Easy < Normal < Hard < Nightmare


async def test_king_entra_vence_os_andares_e_ganha_o_bau(tmp_path: Path) -> None:
    async with logged_in(tmp_path, novice=19000) as a:
        b = await a.join("outro")
        await _start(a, b, 8200)
        got = await a.idle()
        assert [m.enterCount for m in _kings(got)] == [1]
        s = a.server.online.get(a.user_id)
        assert s is not None and s.campaign is not None and s.campaign.run is not None
        shadows = s.campaign.run.shadows  # as sombras: cópias dos jogadores do servidor (aqui, os dois da sala)
        assert sorted(h["nickName"] for h in shadows) == ["Maga", "Outro"]
        for h in shadows:
            h.update(hp=1, attack=1)
        for camp in KING_FIGHTS:
            _weak(a, camp)
            a.client.send(5125, pb.CampaignReqMsg(paraInt1=camp, paraBool1=True))
            prepare = pb.BattlePrepareMsg.FromString((await a.until(157))[-1].body)
            foes = [h for h in prepare.heros if h.side == 2]
            assert (
                prepare.battleType == 290 and {h.nickName for h in foes} == {"Maga", "Outro"} and not prepare.soldiers
            )
            got = await a.fight(prepare)
            got += await a.idle() + await back_to_map(a)
        end = _kings(got)[-1]
        assert (end.currentStep, end.currentIndex, end.rewardCount, end.maxIndex) == (1, 5, 5, 1)
        snap = _snap(a)
        assert sum(i.count for i in snap.items if i.template_id == 2131002) == 5  # Bronze King Chest, 1 por luta
        assert 135 not in {p.code for p in got}  # sem carta
        assert torres.unlocked(snap, {"SonTypes": "300", "DifficultyGrade": "2"})


async def test_king_uma_entrada_por_dia_e_dificuldade_fechada(tmp_path: Path) -> None:
    async with logged_in(tmp_path, novice=19000) as a:
        b = await a.join("outro")
        snap, now = _snap(a), a.server.online.get(a.user_id).ctx.clock.now()
        await _start(a, b, 8202)  # Normal sem a Easy vencida: "Clear {0} to enter"
        assert 125 not in {p.code for p in await a.idle()}
        ev.daily(snap, torres.KING_KEY, now).value = 1  # já entrou hoje
        a.client.send(
            5034,
            pb.RoomReqMsg(
                roomId=a.server.online.get(a.user_id).ctx.rooms.of(a.user_id).id, dungeonId=3, campaignId=8200
            ),
        )
        await a.idle()
        a.client.send(5039, pb.CampaignReqMsg(paraInt2=8200, paraBool1=False))
        await a.idle()
        s = a.server.online.get(a.user_id)
        assert s is not None and s.campaign is not None and s.campaign.run is not None
        assert not s.campaign.run.rewarded and torres.used(snap, torres.KING, now) == 1


async def test_spire_conta_a_entrada_e_mostra_o_andar(tmp_path: Path) -> None:
    async with logged_in(tmp_path, novice=19000) as a:
        b = await a.join("outro")
        await _start(a, b, 8201)
        await a.idle()
        snap, now = _snap(a), a.server.online.get(a.user_id).ctx.clock.now()
        assert torres.used(snap, torres.SPIRE, now) == 1 and ev.peek(snap, torres.SPIRE_TOTAL).value == 1
        assert ev.daily(snap, f"leed:{torres.SPIRE_LEED}", now).value == 1  # "Enter the Spire"
        s = a.server.online.get(a.user_id)
        assert s is not None and s.campaign is not None
        boss = next(int(k) for k, v in s.campaign.content["battles"].items() if v.get("trial"))
        a.client.send(5125, pb.CampaignReqMsg(paraInt1=boss, paraBool1=True))
        prepare = pb.BattlePrepareMsg.FromString((await a.until(157))[-1].body)
        assert prepare.currentWave == 1


async def test_recuperar_exp_ve_a_spire(tmp_path: Path) -> None:
    clock = FakeClock(datetime(2026, 10, 23, 10, tzinfo=UTC))
    async with logged_in(tmp_path, novice=19000, clock=clock) as g:
        s = g.server.online.get(g.user_id)
        assert s is not None
        snap, templates = _snap(g), s.ctx.templates
        snap.character.grades = 40
        clock.advance(86400)
        daily.roll(snap, templates, clock.now())
        assert "5" in json.loads(ev.peek(snap, "recover").text)  # não entrou ontem
        ev.daily(snap, torres.DAILY[torres.SPIRE], clock.now()).value = 1
        clock.advance(86400)
        daily.roll(snap, templates, clock.now())
        assert "5" not in json.loads(ev.peek(snap, "recover").text)


def test_pulo_de_andar_do_cliente() -> None:
    """TrailCountView.refreshTurn: Spire (25) até 3 turnos pula 4; nos andares 1 e 5k até 5 turnos pula 5."""
    assert battle_mod.skip_to(1, 3, 25) == 5 and battle_mod.skip_to(1, 4, 25) == 2
    assert battle_mod.skip_to(21, 2, 25) == 25 > battle_mod.SPIRE_CLEAR  # "clear instantly"
    assert battle_mod.skip_to(1, 5, 290) == 5 and battle_mod.skip_to(10, 5, 290) == 15
    assert battle_mod.skip_to(10, 6, 290) == 11 and battle_mod.skip_to(7, 1, 290) == 8


async def test_loja_da_spire_compra_e_carga_na_luta(tmp_path: Path) -> None:
    async with logged_in(tmp_path, novice=19000) as a:
        b = await a.join("outro")
        await _start(a, b, 8201)
        got = await a.idle()
        shop = pb.PlayerTrialMsg.FromString(next(p.body for p in got if p.code == 4468))
        assert [(t.skillId, t.param2, t.param3) for t in shop.trialInfos] == [
            (101, 3, 45), (102, 3, 45), (104, 3, 45), (103, 1, 95)]  # fmt: skip
        snap = _snap(a)
        snap.character.point, snap.character.gift_token = 100, 0
        a.client.send(8582, pb.TrialInfoMsg(skillId=103, count=1, param1=1))
        reply = pb.TrialInfoMsg.FromString((await a.until(4467))[-1].body)
        assert (reply.count, reply.param1, snap.character.point) == (1, 1, 5)
        a.client.send(8582, pb.TrialInfoMsg(skillId=103, count=1, param1=1))  # cota 1 cheia
        assert pb.TrialInfoMsg.FromString((await a.until(4467))[-1].body).param1 == 0
        s = a.server.online.get(a.user_id)
        assert s is not None and s.campaign is not None
        boss = next(int(k) for k, v in s.campaign.content["battles"].items() if v.get("trial"))
        a.client.send(5125, pb.CampaignReqMsg(paraInt1=boss, paraBool1=True))
        prepare = pb.BattlePrepareMsg.FromString((await a.until(157))[-1].body)
        mine = next(h for h in prepare.heros if h.userId == a.user_id)
        assert {t.skillId: t.count for t in mine.trials} == {101: 3, 102: 3, 104: 3, 103: 2}  # 1 grátis + 1 comprada
        assert s.battle is not None
        a.client.send(10507, pb.BattleItemMsg(battleId=s.battle.id, skillTempId=101, userId=a.user_id))
        used = pb.ItemUseResultMsg.FromString((await a.until(158))[-1].body)
        assert (used.result, used.type, used.count, used.uItemId) == (0, 2, 2, 0)


def _spire_battle() -> bt.Battle:
    """A luta do chefe da Spire gerada (0102), com o herói de teste do test_batalha e as quatro runas."""
    made = json.loads((VERSIONS / "0102_torres.json").read_text(encoding="utf-8"))
    spec = next(b for b in made["8201"]["battles"].values() if b.get("trial"))
    b, _ = _battle(**spec)
    b.trials = {101: 1, 102: 1, 103: 1, 104: 1}
    return b


def _kill_wave(b: bt.Battle, turns: int) -> None:
    for u in b.units:
        if u.side != bt.PLAYER_SIDE:
            u.hp, u.turn = 0, turns


@needs_templates
def test_runas_aplicam_o_efeito_na_luta() -> None:
    b = _spire_battle()
    hero = b.player
    assert hero is not None
    assert b.use_trial(101) == 0 and asyncio.run(b._player_skill(b.frame + 2)) == 101
    b._act(hero, 101)
    assert b._mods(hero, {bt.RECEIVED})[0] == -90  # Guardian Shield: dano recebido -90%
    hero.hp = 100
    assert b.use_trial(102) == 0 and asyncio.run(b._player_skill(b.frame + 2)) == 102
    b._act(hero, 102)
    assert hero.hp == 100 + hero.max_hp // 2  # Paean of Life: 50% da vida máxima
    assert b.use_trial(104) == 0 and asyncio.run(b._player_skill(b.frame + 2)) == 104
    b._act(hero, 104)
    assert b._mods(hero, {bt.DEALT, bt.DEALT2})[0] == 200  # Vulcan Wrath
    hero.hp = 0
    assert b.use_trial(103) == 0 and hero.hp == hero.max_hp  # Sacred Nirvana: revive caído
    assert b.use_trial(103) is None  # sem carga


@needs_templates
def test_pulo_de_andar_na_luta_da_spire() -> None:
    b = _spire_battle()
    assert b.layer == 1 and b.spec["battleType"] == 25
    _kill_wave(b, 2)  # chefe caiu em 2 turnos: pula para o 5
    assert b._reinforce() and b.layer == 5 and len(b._waves) == 23 - 4
    _kill_wave(b, 4)  # 4 turnos: sem pulo
    assert b._reinforce() and b.layer == 6
    while b.layer < 21:
        _kill_wave(b, 9)
        assert b._reinforce()
    _kill_wave(b, 1)  # do 21 o pulo passa do 24: "clear instantly"
    assert not b._reinforce() and b.layer == 24 and not b._waves
