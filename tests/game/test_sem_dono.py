"""Pedidos do cliente sem resposta conferida com a captura (auditoria "SEM DONO"): a sequência de códigos
tem que sair igual à do oficial, com os mesmos textos 111/83."""

from __future__ import annotations

from pathlib import Path

import pytest

from tests.game.harness import logged_in
from tests.test_end_to_end import TEMPLATES
from wartune_server.domain.models import ArenaRank, Star
from wartune_server.protocol.messages import wartune_pb2 as pb

pytestmark = pytest.mark.skipif(not TEMPLATES.exists(), reason="precisa de data/templates")


def codes(packets: list) -> list[int]:  # type: ignore[type-arg]
    return [p.code for p in packets]


async def test_take_reward_sequence_matches_capture(tmp_path: Path) -> None:
    """(visto) 191924-1 #9064-#9069 (oficial 20261025-232017-1): 109, 3, 4243, 111 e 83 com o mesmo texto."""
    async with logged_in(tmp_path, novice=30011) as g:
        await g.server.services.characters.save(ranks=(ArenaRank(g.user_id, 1),))
        g.client.send(8329)
        got = await g.until(83)
        assert codes(got) == [109, 3, 4243, 111, 83]
        text = "Retrieve Ranking Rewards: Golds x"
        assert pb.ChatChannelMsg.FromString(got[3].body).encodeMsg.startswith(text)
        assert (
            pb.ChatChannelMsg.FromString(got[4].body).encodeMsg == pb.ChatChannelMsg.FromString(got[3].body).encodeMsg
        )


async def test_disband_refunds_daru_and_sends_capture_sequence(tmp_path: Path) -> None:
    """(visto) 191924-1 #20734-#20738: 3, 109, 111 "Disband Successful. You gained 51 Daru." e 100."""
    async with logged_in(tmp_path, novice=30012) as g:
        session = g.server.online.get(g.user_id)
        assert session is not None and session.snapshot is not None
        snap = session.snapshot
        snap.character.gold = 2801
        await g.server.services.characters.save(snap.character)
        g.client.send(5155, pb.ArmyPawnInfoMsg(tempateId=10101, ownPawns=900))
        await g.until(111)
        await g.idle()
        before = snap.character.strategy

        g.client.send(5157, pb.ArmyPawnInfoMsg(tempateId=10101, ownPawns=100))
        got = await g.until(100)
        assert codes(got) == [3, 109, 111, 100]
        assert pb.ChatChannelMsg.FromString(got[2].body).encodeMsg == "Disband Successful. You gained 20 Daru."
        assert snap.character.strategy == before + 20


async def test_lock_star_sends_astral_locked_text(tmp_path: Path) -> None:
    """(visto) 191924-1 #20257: 4178, 112 e 111 "Astral Locked!". Sem a missão 53 aceita não há 112 aqui."""
    async with logged_in(tmp_path, novice=30013) as g:
        session = g.server.online.get(g.user_id)
        assert session is not None and session.snapshot is not None
        snap = session.snapshot
        star = Star(snap.character.id or 0, 1, bag_type=1, pos=0)
        snap.stars.append(star)
        await g.server.services.characters.save(star)
        g.client.send(8330, pb.StarLockReqMsg(starType=1, pos=0))
        got = await g.until(111)
        assert codes(got) == [4178, 111]
        assert pb.ChatChannelMsg.FromString(got[1].body).encodeMsg == "Astral Locked!"


async def test_free_star_draw_has_no_109(tmp_path: Path) -> None:
    """(visto) 191924-1 #19350 (1º sorteio do dia, site 0 grátis): 3, 4152 do leed, 3, 4180 e o 83 da devoção.
    Sem 109: o 109 só sai com ouro gasto (ver stars.star_rand)."""
    async with logged_in(tmp_path, novice=30015) as g:
        g.client.send(8269, pb.StarRandReqMsg(site=0))
        got = await g.until(4180)
        assert 109 not in codes(got)
        assert codes(got)[-1] == 4180


async def test_equip_move_sends_150_then_one_4178_per_slot(tmp_path: Path) -> None:
    """(visto) 191924-1 #19445: 150 e depois dois 4178 (um por casa). Não reproduzidos: 3, 4638 e 4247 do mesmo pedido (TODO: origem não identificada)."""
    async with logged_in(tmp_path, novice=30014) as g:
        session = g.server.online.get(g.user_id)
        assert session is not None and session.snapshot is not None
        snap = session.snapshot
        snap.character.grades = 30  # equipar exige o grau da estrela (NeedGrades)
        star = Star(snap.character.id or 0, 1503, bag_type=1, pos=0)
        snap.stars.append(star)
        await g.server.services.characters.save(star)
        g.client.send(8267, pb.StarMoveReqMsg(beginStarType=1, beginPos=0, endStarType=2, endPos=0, eat=True))
        got = [c for c in codes(await g.idle()) if c in (150, 4178)]
        assert got == [150, 4178, 4178]


async def test_recover_list_sends_4912_then_109(tmp_path: Path) -> None:
    """(visto) 191924-1 #9044, 1026 #2207 e 1027 #745: 4912 e depois 109 (lista de recuperação vazia)."""
    async with logged_in(tmp_path, novice=30016) as g:
        g.client.send(9503, pb.RecoverReqMsg(type=0))
        got = await g.until(109)
        assert codes(got) == [4912, 109]
