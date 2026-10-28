"""Masmorras em grupo 9000-9112: as capturadas (migração 0100) e as geradas (0101, TODO(inventado)
``tools/gera_masmorras.py grupo``), entrando pela sala de 2 (5023, 5024, 5036, 5039)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from tests.game.harness import Game, logged_in
from tests.game.test_masmorra_1001 import battle, fast_battles  # noqa: F401  (fixture)
from tests.test_end_to_end import TEMPLATES
from wartune_server.protocol.messages import wartune_pb2 as pb

pytestmark = pytest.mark.skipif(not TEMPLATES.exists(), reason="precisa de data/templates")
VERSIONS = Path("src/wartune_server/persistence/migrations/versions")


async def _start(a: Game, b: Game, cid: int) -> None:
    """Sala de 2: b pronto querendo prêmio (``isGet`` = isNoGet false), a começa com prêmio (``paraBool1`` false)."""
    a.client.send(5023, pb.RoomReqMsg(capacity=4))
    room = pb.RoomMsg.FromString(next(p.body for p in await a.idle() if p.code == 12))
    a.client.send(5034, pb.RoomReqMsg(roomId=room.roomId, dungeonId=1, campaignId=cid))
    b.client.send(5024, pb.RoomReqMsg(roomId=room.roomId))
    b.client.send(5036, pb.RoomReqMsg(state=1, isGet=False))
    await b.idle()
    await a.idle()
    a.client.send(5039, pb.CampaignReqMsg(paraInt2=cid, paraBool1=False))


def _weak(g: Game, camp: int) -> None:
    """Inimigos com 1 de vida: o personagem de teste é nível 1 e a luta contra os de nível 30-80 não acaba."""
    s = g.server.online.get(g.user_id)
    assert s is not None and s.campaign is not None
    spec = s.campaign.battle(camp)
    assert spec is not None
    for u in spec["soldiers"] + spec["heroes"]:
        u.update(hp=1, initHp=1)


async def _entered(g: Game, first_map: int, name: str) -> None:
    got = await g.until(83)
    assert pb.RoomCreatedMsg.FromString(next(p.body for p in got if p.code == 125)).room.campaignId == first_map
    text = pb.ChatChannelMsg.FromString(got[-1].body).encodeMsg
    assert text == f"Entered [{name}]. You still have 0/1 multi-player dungeon attempts available."
    s = g.server.online.get(g.user_id)
    assert s is not None and s.snapshot is not None and s.campaign is not None and s.campaign.run is not None
    assert s.campaign.run.rewarded and s.snapshot.character.multi_copy_count == 0


@pytest.mark.parametrize(
    ("cid", "first_map", "name", "fight"),
    [
        (9000, 2091, "Nether Forest", 209102), (9002, 2031, "The Graveyard", 203102),  # capturadas
        (9010, 2211, "Samsara", 221102), (9112, 2261, "Nirvana (Nightmare)", 226102),  # geradas
    ],
)  # fmt: skip
async def test_sala_de_2_entra_e_vence_a_1a_luta(tmp_path: Path, cid: int, first_map: int, name: str, fight: int):
    async with logged_in(tmp_path, novice=19000) as a:
        b = await a.join("outro")
        await _start(a, b, cid)
        await _entered(a, first_map, name)
        await _entered(b, first_map, name)
        _weak(a, fight)
        got = await battle(a, fight)  # vitória (4103 battleResult 1) checada no battle()
        report = pb.BattleReportMsg.FromString(next(p.body for p in got if p.code == 4103))
        assert report.gpBonus > 0  # com prêmio: a captura sem prêmio dava 0 (191924 #4744)


async def test_capturada_chega_ao_chefe(tmp_path: Path) -> None:
    """9000: o grupo 209102-209104 (param3) abre o portal 209105 para o 2092; o chefe 209204 dá as cartas (135)."""
    async with logged_in(tmp_path, novice=19000) as a:
        b = await a.join("outro")
        await _start(a, b, 9000)
        await a.until(83)
        for camp in (209102, 209103, 209104):
            _weak(a, camp)
            await battle(a, camp)
        a.client.send(5125, pb.CampaignReqMsg(paraInt1=209105, paraBool1=True))
        got = await a.idle()
        assert pb.RoomCreatedMsg.FromString(next(p.body for p in got if p.code == 125)).room.campaignId == 2092
        s = a.server.online.get(a.user_id)
        assert s is not None and s.campaign is not None
        boss = s.campaign.node(209204)
        assert boss is not None and boss["masterType"] == 41
        _weak(a, 209204)
        assert 135 in {p.code for p in await battle(a, 209204)}


async def test_gerada_chega_ao_chefe(tmp_path: Path) -> None:
    """9013 (um mapa, o 2033 da 9002 como planta): o chefe 227108 dá as cartas."""
    async with logged_in(tmp_path, novice=19000) as a:
        b = await a.join("outro")
        await _start(a, b, 9013)
        await a.until(83)
        s = a.server.online.get(a.user_id)
        assert s is not None and s.campaign is not None
        boss = s.campaign.node(227108)
        assert boss is not None and boss["masterType"] == 41
        _weak(a, 227108)
        assert 135 in {p.code for p in await battle(a, 227108)}


async def test_sem_premio_nao_gasta(tmp_path: Path) -> None:
    """(visto) 191924 #4525/#4537: ``paraBool1`` true entra com "1/1" e a luta não dá EXP."""
    async with logged_in(tmp_path, novice=19000) as a:
        a.client.send(5023, pb.RoomReqMsg(capacity=4))
        room = pb.RoomMsg.FromString(next(p.body for p in await a.idle() if p.code == 12))
        a.client.send(5034, pb.RoomReqMsg(roomId=room.roomId, dungeonId=1, campaignId=9000))
        await a.idle()
        a.client.send(5039, pb.CampaignReqMsg(paraInt2=9000, paraBool1=True))
        got = await a.until(83)
        assert pb.ChatChannelMsg.FromString(got[-1].body).encodeMsg.endswith(
            " 1/1 multi-player dungeon attempts available."
        )
        report = pb.BattleReportMsg.FromString(next(p.body for p in await battle(a, 209102) if p.code == 4103))
        assert report.gpBonus == 0


def test_todas_9000_9112_tem_conteudo() -> None:
    """3 capturadas + 20 geradas = as 23 campanhas em grupo do ``Campaigns``; as geradas marcadas."""
    captured = json.loads((VERSIONS / "0100_masmorras_grupo.json").read_text(encoding="utf-8"))
    made = json.loads((VERSIONS / "0101_masmorras_grupo_geradas.json").read_text(encoding="utf-8"))
    assert sorted(captured) == ["9000", "9001", "9002"] and len(made) == 20
    assert not set(captured) & set(made) and all(c["inventado"] for c in made.values())
    assert made["9010"]["stages"] == [[2211, 2212, 2213, 2214, 2215]] and made["9013"]["stages"] == [[2271]]
