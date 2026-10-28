"""Forgotten Catacombs: os andares 1-25 como nas capturas (24/10 #12046-#13771, 25/10 #9658-#10906, 26/10 #13286), e as
regras deduzidas batendo com eles. Os números do 127 estão em ``content/maze_floors.json``."""

from __future__ import annotations

from pathlib import Path

import pytest

from tests.game.harness import logged_in
from tests.game.test_labirinto import _set
from tests.test_end_to_end import TEMPLATES
from wartune_server.game import maze as mz
from wartune_server.game import rules
from wartune_server.game import sweep as sw
from wartune_server.game.handlers import tower as tw
from wartune_server.protocol.messages import wartune_pb2 as pb
from wartune_server.templates.repository import GameTemplates

pytestmark = pytest.mark.skipif(not TEMPLATES.exists(), reason="precisa de data/templates")


@pytest.fixture(scope="module")
def content() -> dict:  # type: ignore[type-arg]
    return mz.content(GameTemplates.parse(TEMPLATES.read_bytes()), mz.DEFAULT)


def _nodes(content: dict, floor: int) -> dict[int, dict]:  # type: ignore[type-arg]
    return {n["campDataId"] % 100: n for n in content["maps"][str(8000 + floor)]["nodes"]}


def test_inicio_alterna_por_paridade(content: dict) -> None:  # type: ignore[type-arg]
    """(visto) 1-25: ímpar 40/2, par 62/1 (24/10 #12046 e #12116, 25/10 #9658 e #10906)."""
    for floor in range(1, 26):
        start = _nodes(content, floor)[1]
        assert (start["masterType"], start["state"]) == ((40, 2) if floor % 2 else (62, 1)), floor


def test_monstros_e_chefes_do_oficial(content: dict) -> None:  # type: ignore[type-arg]
    """(visto) nome, sonType e poder de luta; o chefe de cada 5 tem o heroTempId = 7000 + andar."""
    m = _nodes(content, 1)[2]
    assert (m["nodeName"], m["sonType"], m["fightCapaity"], m["heroTempId"]) == ("Tenacor Worg", 2116, 929, -1)
    assert _nodes(content, 5)[2]["sonType"] == 2146 and _nodes(content, 5)[2]["heroTempId"] == 7005
    rontao = _nodes(content, 20)[2]
    assert (rontao["nodeName"], rontao["sonType"], rontao["fightCapaity"], rontao["heroTempId"]) == (
        "Rontao the Bastille",
        2401,
        10446,
        7020,
    )  # o template diz "Rontao the Guardian"
    assert _nodes(content, 25)[2]["fightCapaity"] == 15938
    assert _nodes(content, 25)[2]["param4"] == "802504"  # só o portal, sem o baú


def test_baus_e_portais(content: dict) -> None:  # type: ignore[type-arg]
    """(visto) o baú é visível (state 1, nameColor 4) só nos andares 5, 10, ... ; o portal começa escondido (16)."""
    chest = _nodes(content, 5)[3]
    assert (chest["masterType"], chest["state"], chest["nameColor"], chest["sonType"]) == (61, 1, 4, 2202)
    assert _nodes(content, 10)[3]["sonType"] == 2203
    assert 3 not in _nodes(content, 6)
    assert _nodes(content, 5)[4]["state"] == 16 and _nodes(content, 5)[4]["param1"] == 8006
    assert _nodes(content, 25)[4]["param1"] == 8026
    assert content["maze_chests"]["800503"] == [[2050501, 2], [208009, 2]]
    assert content["maze_chests"]["801003"] == [[2050301, 2], [208009, 4]]
    assert content["maze_chests"]["802003"] == [[2050101, 2], [208009, 6]]


def test_layouts_por_faixa(content: dict) -> None:  # type: ignore[type-arg]
    """(visto) 1-10, 11-20 e 21-25 têm posições próprias; o início do 8021 é (26, 23)."""
    assert content["maps"]["8010"]["start"] == [25, 20]
    assert _nodes(content, 10)[2]["posX"] == 37 and _nodes(content, 11)[2]["posX"] == 35
    assert content["maps"]["8021"]["start"] == [26, 23]
    assert (_nodes(content, 21)[4]["posX"], _nodes(content, 21)[4]["posY"]) == (52, 37)


def test_batalhas_como_o_157(content: dict) -> None:  # type: ignore[type-arg]
    """(visto, 157 de 24/10 a 27/10) 8002: quatro 7002 nas posições 2, 3, 8 e 9 (livingId 4 a 7), vida 1008, castTime
    4000 e skills 40024, 40025, 40025. O chefe 8005 vem sozinho (livingId 4, castTime 4000, skills 60021...)."""
    soldiers = content["battles"]["800202"]["soldiers"]
    assert [(s["livingId"], s["tempId"], s["pos"], s["initHp"]) for s in soldiers] == [
        (4, 7002, 2, 1008), (5, 7002, 3, 1008), (6, 7002, 8, 1008), (7, 7002, 9, 1008)]  # fmt: skip
    assert soldiers[0]["castTime"] == 4000 and soldiers[0]["skillId"] == [40024, 40025, 40025]
    boss = content["battles"]["800502"]
    assert boss["soldiers"] == []
    hero = boss["heroes"][0]
    assert (hero["livingId"], hero["pos"], hero["castTime"], hero["captain"]) == (4, 5, 4000, 1)
    assert hero["skillId"][:4] == [60021, 60021, 60023, 60021]
    assert content["battles"]["802502"]["heroes"][0]["castTime"] == 4000


def test_monstro_nao_larga_item(content: dict) -> None:  # type: ignore[type-arg]
    """(visto, 4103 de 24/10 #12181-#13269) as vitórias dos andares 1 a 15 dão só EXP."""
    assert all(v == [] for v in content["drops"].values())


def test_ganho_do_andar_e_fog(content: dict) -> None:  # type: ignore[type-arg]
    """(visto) o totalGp depois do andar k é 200 * k * (k + 1); o andar 5 dá 2000 de GP de batalha."""
    assert content["battles"]["800502"]["gpBonus"] == 2000
    assert content["battles"]["802502"]["gpBonus"] == 10000
    assert content["maps"]["8005"]["fog"]["row"] == 18 and content["maps"]["8005"]["fog"]["col"] == 14


READY = 19000  # novice_process de quem já fez o tutorial (como test_labirinto)


def _tower(g: object) -> mz.Tower:
    s = g.server.online.get(g.user_id)  # type: ignore[attr-defined]
    return mz.load(s.snapshot, s.ctx.clock.now())


def test_bau_do_andar_so_nos_andares_de_cinco() -> None:
    """(visto) 10/25 #9409 e #9470: o baú sai nos andares 5, 10, 15 e 20 e a configuração guarda o que o oficial deu."""
    assert mz.chest_goods(mz.DEFAULT, 5) == [[2050501, 2], [208009, 2]]
    assert mz.chest_goods(mz.DEFAULT, 10) == [[2050301, 2], [208009, 4]]


async def test_varredura_entrega_os_baus_dos_andares(tmp_path: Path) -> None:
    """(visto) 10/25 #9394-#9510: a rodada do andar 5 leva o baú no 4425 (2050501 x2, 208009 x2), vai para a mochila
    e para o 4205 do ``itemTempIds``; as rodadas sem baú saem sem item. A ordem é 115, 83 da EXP, 111, 4425, 83."""
    async with logged_in(tmp_path, novice=READY) as g:
        snap = g.server.online.get(g.user_id).snapshot  # type: ignore[union-attr]
        snap.character.gold, snap.character.point = 100_000, 100
        _set(g, mz.Tower(index=1, record=60))
        g.client.send(8528, pb.CampaignSweepReq(sweepType=2, opType=1, campaignId=8001, eIndex=5, enterType=1))
        await g.until(4425)
        g.client.send(8528, pb.CampaignSweepReq(sweepType=2, opType=2, campaignId=8001, payType=1))
        got = await g.until(4425)
        got += await g.idle()
        codes = [p.code for p in got]
        done = pb.CampaignSweepRsp.FromString(next(p.body for p in got if p.code == 4425))
        assert done.status == sw.DONE
        goods = {r.cIndex: [(i.templateId, i.count) for i in r.items] for r in done.result}
        assert goods == {1: [], 2: [], 3: [], 4: [], 5: [(2050501, 2), (208009, 2)]}
        assert codes.index(115) < codes.index(4425) and codes.index(83) < codes.index(4425)
        assert _tower(g).items == [[2050501, 2], [208009, 2]]
        assert sum(i.count for i in g.server.online.get(g.user_id).snapshot.items if i.template_id == 208009) == 2  # type: ignore[union-attr]


async def test_morte_no_labirinto_manda_o_custo_do_reviver(tmp_path: Path) -> None:
    """(visto) 10/25 #10593 msg 0 e #11400 msg 25: a primeira morte da entrada sai grátis, a seguinte pede 25."""
    async with logged_in(tmp_path, novice=READY) as g:
        _set(g, mz.Tower(index=3, record=60, enters=1))
        s = g.server.online.get(g.user_id)
        assert s is not None
        await s.ctx.characters.save(tw.died(s))
        assert pb.TowerDiedMsg.FromString((await g.until(4207))[-1].body).msg == "0"
        await s.ctx.characters.save(tw.died(s))
        died = pb.TowerDiedMsg.FromString((await g.until(4207))[-1].body)
        assert (died.title, died.msg) == ("Respawn Note", "25")
        assert _tower(g).deaths == 2


async def test_subir_andar_avanca_a_missao_38(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """(dedução) o portal para o andar seguinte conta a condição 38 (Para1 8001) uma vez."""
    async with logged_in(tmp_path, novice=READY) as g:
        s = g.server.online.get(g.user_id)
        assert s is not None
        seen: list[tuple[int, int, int]] = []

        def spy(snap: object, templates: object, kind: int, para1: int, value: int) -> list:  # type: ignore[type-arg]
            seen.append((kind, para1, value))
            return []

        monkeypatch.setattr(rules, "quest_event", spy)
        rows = tw.floor_entered(s, 8002)
        assert seen == [(rules.CATACOMBS_CONDITION, 8001, 1)]
        assert len(rows) == 1
