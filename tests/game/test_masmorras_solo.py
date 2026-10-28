"""Masmorras solo: as capturadas (migração 0098) e as geradas (0099, TODO(inventado) ``tools/gera_masmorras.py``)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from tests.game.harness import logged_in
from tests.game.test_masmorra_1001 import battle, enter, fast_battles  # noqa: F401  (fixture)
from tests.test_end_to_end import TEMPLATES
from wartune_server.protocol.messages import wartune_pb2 as pb

pytestmark = pytest.mark.skipif(not TEMPLATES.exists(), reason="precisa de data/templates")
VERSIONS = Path("src/wartune_server/persistence/migrations/versions")


@pytest.mark.parametrize(
    ("campaign", "first_map", "fight"),
    [
        (1101, 1111, 111102), (1104, 1091, 109102), (1107, 1271, 127102), (1201, 1291, 129102),  # capturadas
        (1202, 1311, 131102), (1307, 1551, 155102), (1602, 1891, 189102),  # geradas
    ],
)  # fmt: skip
async def test_entra_e_luta(tmp_path: Path, campaign: int, first_map: int, fight: int) -> None:
    async with logged_in(tmp_path, novice=19000) as g:
        got = await enter(g, campaign)
        assert pb.RoomCreatedMsg.FromString(next(p.body for p in got if p.code == 125)).room.campaignId == first_map
        assert {127, 130} <= {p.code for p in got}
        s = g.server.online.get(g.user_id)
        assert s is not None and s.campaign is not None and s.campaign.node(fight) is not None
        await battle(g, fight)  # vitória (4103 battleResult 1) checada no battle()


async def test_gerada_chega_ao_chefe(tmp_path: Path) -> None:
    """1205 (um mapa, planta 1091): o chefe 137107 vencido acaba a etapa com as cartas (135)."""
    async with logged_in(tmp_path, novice=19000) as g:
        await enter(g, 1205)
        s = g.server.online.get(g.user_id)
        assert s is not None and s.campaign is not None
        boss = s.campaign.node(137107)
        assert boss is not None and boss["masterType"] == 41
        got = await battle(g, 137107)
        assert 135 in {p.code for p in got}


def test_gerador_respeita_as_casas_da_captura() -> None:
    """Os nós capturados da 1201 já estão em casas andáveis do .titles: gerar a planta sobre ela não os move.
    Só a Elise do 1292 (129108, NPC da história) fica fora de casa andável: (82,72) vira (80,68)."""
    from tools.gera_masmorras import CAPTURED, MULTI, Gen, stage
    from wartune_server.templates.repository import GameTemplates

    captured = json.loads(CAPTURED.read_text(encoding="utf-8"))
    g = Gen(GameTemplates.parse(TEMPLATES.read_bytes()))
    made = stage(g, captured[MULTI[0]], MULTI[1], [1291, 1292], 1201)
    for m in ("1291", "1292"):
        want = {n["campDataId"]: (n["posX"], n["posY"]) for n in captured["1201"]["maps"][m]["nodes"]}
        got = {n["campDataId"]: (n["posX"], n["posY"]) for n in made["maps"][m]["nodes"]}
        if m == "1292":
            assert got.pop(129108) == (80, 68) and want.pop(129108) == (82, 72)
        assert got == want


def test_geradas_marcadas() -> None:
    seed = json.loads((VERSIONS / "0099_masmorras_geradas.json").read_text(encoding="utf-8"))
    assert len(seed) == 33 and all(c["inventado"] for c in seed.values())
    assert seed["1102"]["stages"][0] == [1191, 1192] and seed["1102"]["inventado"] == [1201, 1202]
