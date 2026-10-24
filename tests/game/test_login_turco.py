"""Login de personagem alto (só turco: login.json, nível 56) e a primeira senha secundária (oficial_encantar)."""

from __future__ import annotations

from pathlib import Path

import pytest

from tests.game.harness import Game, logged_in
from tests.test_end_to_end import TEMPLATES
from wartune_server.domain.models import PlayerSnapshot
from wartune_server.game import castle as cs
from wartune_server.protocol.messages import wartune_pb2 as pb

pytestmark = pytest.mark.skipif(not TEMPLATES.exists(), reason="precisa de data/templates")
GOLD_5 = 130405  # Gold Production nível 5: 60 x 5 = 300


def _snap(g: Game) -> PlayerSnapshot:
    s = g.server.online.get(g.user_id)
    assert s is not None and s.snapshot is not None
    return s.snapshot


async def _grow(g: Game, grades: int) -> PlayerSnapshot:
    snap = _snap(g)
    snap.character.grades = grades
    s = g.server.online.get(g.user_id)
    assert s is not None
    await g.server.services.characters.save(snap.character, *cs.ensure(snap, s.ctx.templates, s.ctx.clock.now()))
    return snap


async def test_login_do_nivel_56(tmp_path: Path) -> None:
    async with logged_in(tmp_path, novice=33000) as g:
        snap = await _grow(g, 56)
        gold = next(b for b in snap.buildings if b.template_id // 100 == GOLD_5 // 100)
        gold.template_id, snap.character.seminary_effect = GOLD_5, 10

        g.client.send(8224, pb.PlayerDataMsg(build=True, castle=True))
        got = await g.idle()
        codes = [p.code for p in got]
        assert codes.index(152) < codes.index(110) < codes.index(4153)  # (só turco: #19-#21)
        effect = pb.PropertyUpdatedMsg.FromString(got[codes.index(110)].body)
        assert (effect.propertyType, effect.value) == (104, 330)

        g.client.send(8224, pb.PlayerDataMsg(army=True))
        got = await g.idle()
        codes = [p.code for p in got]
        i = codes.index(4544)
        assert codes[i : i + 4] == [4544, 4631, 4633, 4555]  # (só turco: #34-#37)
        treasure = pb.PlayerTreasureMsg.FromString(got[i + 2].body)
        assert (list(treasure.templateIds), treasure.index) == ([2190001, 2190002, 2190003, 2190004], 0)
        dragon = pb.FateListMsg.FromString(got[i + 3].body).fateInfo[0]
        assert (dragon.fateTypes, dragon.grades) == (101, 0)

        g.client.send(8224, pb.PlayerDataMsg(user=True))
        codes = [p.code for p in await g.until(4776)]
        assert codes[codes.index(4686) + 1] == 4495  # (só turco: #39-#40)
        assert codes[codes.index(4598) - 1] == 4696


async def test_login_baixo_nao_manda(tmp_path: Path) -> None:
    """(visto) o inglês (nível 1 a 16) não tem 4631, 4633, 4555 nem 4495 no login."""
    async with logged_in(tmp_path, novice=33000) as g:
        g.client.send(8224, pb.PlayerDataMsg(army=True))
        codes = [p.code for p in await g.idle()]
        assert not {4631, 4633, 4555} & set(codes)
        g.client.send(8224, pb.PlayerDataMsg(user=True))
        assert 4495 not in [p.code for p in await g.until(4776)]


async def test_primeira_senha_secundaria(tmp_path: Path) -> None:
    """(visto) oficial_encantar #95 e #256-#273."""
    async with logged_in(tmp_path, novice=33000) as g:
        g.client.send(8224, pb.PlayerDataMsg(user=True))
        got = await g.until(4776)
        codes = [p.code for p in got]
        assert codes[codes.index(4598) - 1] == 4696
        first = pb.VicePasswordMsg.FromString(got[codes.index(4598) - 1].body)
        assert (first.opType, first.result) == (6, 1)

        gold = _snap(g).character.gold
        g.client.send(8806, pb.VicePasswordMsg(opType=2, inputPass="131313", prePass="0", newPass="131313"))
        got = await g.until(83)
        codes = [p.code for p in got]
        assert codes[:3] == [109, 3, 115] and codes[-4:] == [111, 4696, 4696, 83], codes
        text = "Congrats! You earned: Lvl. 1-3 Gem Pack x1, Mount Training Whip x20, 5,000 Gold, 2,000 Daru"
        assert pb.ChatChannelMsg.FromString(got[-1].body).encodeMsg == text
        assert [(m.opType, m.result) for m in map(pb.VicePasswordMsg.FromString, (got[-3].body, got[-2].body))] == [
            (6, 0),
            (2, 1),
        ]
        assert _snap(g).character.gold == gold + 5000

        g.client.send(8224, pb.PlayerDataMsg(user=True))
        assert 4696 not in [p.code for p in await g.until(4776)]  # (visto) 153200, 171155: depois da senha, nada


async def test_com_senha_sem_recompensa_nao_avisa(tmp_path: Path) -> None:
    """Senha feita sem a recompensa (personagem antigo, mochila cheia): o aviso não teria como ser resgatado."""
    async with logged_in(tmp_path, novice=33000) as g:
        _snap(g).character.vice_password = "x"
        await g.server.services.characters.save(_snap(g).character)
        g.client.send(8224, pb.PlayerDataMsg(user=True))
        assert 4696 not in [p.code for p in await g.until(4776)]
