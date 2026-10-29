"""Torres 8200-8204 (game/torres): Tower of Kings e The Spire, mapas da migração 0102 (TODO(inventado)
``tools/gera_masmorras.py torres``), entrando pela sala (5023, 5024, 5036, 5039)."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import pytest

from tests.game.harness import Game, logged_in
from tests.game.test_masmorra_1001 import battle, fast_battles  # noqa: F401  (fixture)
from tests.game.test_masmorras_grupo import _start, _weak
from tests.test_end_to_end import TEMPLATES
from wartune_server.domain.models import PlayerSnapshot
from wartune_server.game import daily, torres
from wartune_server.game import events as ev
from wartune_server.protocol.messages import wartune_pb2 as pb
from wartune_server.services.clock import FakeClock

pytestmark = pytest.mark.skipif(not TEMPLATES.exists(), reason="precisa de data/templates")
VERSIONS = Path("src/wartune_server/persistence/migrations/versions")
KING_FIGHTS = (820002, 820003, 820004, 820008)


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
    assert len(spire) == 1 and len(spire[0]["reinforce"]) == 9  # 10 andares
    hp = [made[k]["battles"][f"{k}02"]["soldiers"][0]["hp"] for k in ("8200", "8202", "8203", "8204")]
    assert hp == sorted(hp) and len(set(hp)) == 4  # Easy < Normal < Hard < Nightmare


async def test_king_entra_vence_os_andares_e_ganha_o_bau(tmp_path: Path) -> None:
    async with logged_in(tmp_path, novice=19000) as a:
        b = await a.join("outro")
        await _start(a, b, 8200)
        got = await a.idle()
        assert [m.enterCount for m in _kings(got)] == [1]
        for camp in KING_FIGHTS:
            _weak(a, camp)
            got = await battle(a, camp)
        end = _kings(got)[-1]
        assert (end.currentStep, end.currentIndex, end.rewardCount, end.maxIndex) == (1, 4, 4, 1)
        snap = _snap(a)
        assert sum(i.count for i in snap.items if i.template_id == 2131002) >= 4  # Bronze King Chest (+ a carta)
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
