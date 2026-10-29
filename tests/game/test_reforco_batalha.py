"""Reforço de jogador numa luta em curso (``Battle.join``; 8255 e 8745). Ver docs/batalha.md."""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any

import pytest
from google.protobuf.message import Message

from tests.game.harness import logged_in
from tests.game.test_batalha import _battle, needs_templates
from wartune_server.game import battle as bt
from wartune_server.game.handlers import treasure as T
from wartune_server.game.session import GameSession
from wartune_server.protocol.messages import wartune_pb2 as pb

pytestmark = needs_templates


class _Viewer:
    def __init__(self) -> None:
        self.got: list[tuple[int, Message]] = []

    def send(self, code: int, msg: Message) -> None:
        self.got.append((code, msg))


def _hero(user: int) -> dict[str, Any]:
    return {"tempId": 1011, "type": 1, "userId": user, "heroId": user, "maxHp": 500, "hp": 500}


async def test_reforco_entra_na_luta_em_curso_e_aparece_para_os_outros() -> None:
    b, sent = _battle()
    assert not b.join(_hero(7), _Viewer())  # antes do start: nada a reforçar
    b.start()  # sem 10007 a luta espera: está em curso
    try:
        a, c = _Viewer(), _Viewer()
        assert b.join(_hero(7), a)
        code, msg = sent[-1]
        assert code == bt.S_REINFORCE and isinstance(msg, pb.ReinforceMsg)
        assert (msg.side, [(h.userId, h.livingId, h.pos) for h in msg.hero]) == (1, [(7, 6, 7)])  # 4 é do herói
        assert a.got[0][0] == bt.S_PREPARE  # quem chega recebe a luta com ele dentro
        prepare = a.got[0][1]
        assert isinstance(prepare, pb.BattlePrepareMsg) and 6 in [h.livingId for h in prepare.heros]
        assert b.join(_hero(8), c)  # o segundo: outro lugar e outro livingId; o 72 chega também ao primeiro
        assert [(h.livingId, h.pos) for h in a.got[-1][1].hero] == [(7, 2)]  # type: ignore[attr-defined]
        assert {6, 7} <= {u.living_id for u in b._round_order()}  # agem a partir da próxima rodada
        b.send(bt.S_STOP, pb.UserStopMsg(type=1))
        assert a.got[-1][0] == c.got[-1][0] == bt.S_STOP  # o resto da luta chega aos reforços
    finally:
        b.cancel()
    await asyncio.sleep(0)
    assert not b.join(_hero(9), _Viewer())  # acabou: recusado


async def test_reforco_do_tesouro_luta_e_leva_o_premio(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    async def win(battle: bt.Battle) -> bool:
        for unit in battle.units:
            if unit.side == 2:
                unit.hp = 0
        return True

    monkeypatch.setattr(bt, "FRAME_SECONDS", 0.001)
    monkeypatch.setattr(bt.Battle, "_fight", win)
    async with logged_in(tmp_path, novice=19000) as g:
        o = await g.join("ajuda")
        s: GameSession = g.server.online.get(g.user_id)  # type: ignore[assignment]
        mate: GameSession = g.server.online.get(o.user_id)  # type: ignore[assignment]
        for who in (s, mate):
            assert who.snapshot is not None
            who.snapshot.character.grades = 55
        teams = s.ctx.teams
        assert teams.invite(g.user_id, o.user_id) and teams.accept(o.user_id, g.user_id)
        mate.space_pos = None  # longe: não entra no começo da luta
        g.client.send(8744, pb.PlayerTreasureMsg(opType=1))
        await g.until(4633)
        m = next(i for i in s.snapshot.items if 2190001 <= i.template_id <= 2190004)  # type: ignore[union-attr]
        s.space_pos = (m.random_skill_2 // 20, m.random_skill_3 // 20)
        g.client.send(8744, pb.PlayerTreasureMsg(opType=5, index=m.pos))
        prepare = pb.BattlePrepareMsg.FromString((await g.until(157))[-1].body)
        assert o.user_id not in [h.userId for h in prepare.heros]
        o.client.send(8745, pb.GuildMsg(param1=g.user_id))
        joined = pb.BattlePrepareMsg.FromString((await o.until(157))[-1].body)
        assert o.user_id in [h.userId for h in joined.heros if h.side == 1]
        codes = [p.code for p in await g.fight(prepare)]
        assert bt.S_REINFORCE in codes  # o dono viu o reforço chegar
        assert 4103 in [p.code for p in await o.until(4103)]  # o relatório chega ao reforço
        await g.idle()
        g.client.send(8744, pb.PlayerTreasureMsg(opType=4, index=m.pos, isReward=True))
        await g.until(4633)
        await o.idle()
        assert mate.snapshot is not None
        assert sum(i.count for i in mate.snapshot.items if i.template_id == T.SHARD) == 9  # o prêmio junto


async def test_8255_da_campanha_em_grupo(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Sala de 2 na 9000: a ataca o 209102 sem b (b ocupado); b clica no nó em luta (8255) e entra como reforço."""
    from tests.game.test_masmorras_grupo import _start, _weak
    from wartune_server.game.handlers import campaign as ch

    monkeypatch.setattr(bt, "FRAME_SECONDS", 0.004)
    async with logged_in(tmp_path, novice=19000) as a:
        b = await a.join("outro")
        fora = await a.join("fora")
        await _start(a, b, 9000)
        await a.until(83)
        await b.until(83)
        await b.idle()
        sb: GameSession = b.server.online.get(b.user_id)  # type: ignore[assignment]
        assert sb.campaign is not None
        node = sb.campaign.node(209102)
        assert node is not None
        reforco = pb.CampaignNodeMsg(campDataId=node["nodeId"])
        b.client.send(8255, reforco)  # nó sem luta
        assert await b.idle() == []
        _weak(a, 209102)
        sb.campaign.fighting = 1  # ocupado: a luta começa sem ele
        a.client.send(5125, pb.CampaignReqMsg(paraInt1=209102, paraBool1=True))
        prepare = pb.BattlePrepareMsg.FromString((await a.until(157))[-1].body)
        assert b.user_id not in [h.userId for h in prepare.heros]
        await b.idle()
        sb.campaign.fighting = 0
        fora.client.send(8255, reforco)  # fora da sala
        assert await fora.idle() == []
        with monkeypatch.context() as mp:  # Capacity 1: o cliente nem manda; o servidor recusa
            mp.setattr(ch, "_campaign_row", lambda *_: {"Capacity": 1})
            b.client.send(8255, reforco)
            assert await b.idle() == []
        b.client.send(8255, reforco)
        got = await b.idle()
        joined = pb.BattlePrepareMsg.FromString(next(p.body for p in got if p.code == 157))
        assert b.user_id in [h.userId for h in joined.heros if h.side == 1]
        assert {ch.S_MAP_SYNC, ch.S_NODE} <= {p.code for p in got}
        upd = pb.CampaignNodeUpdateMsg.FromString(next(p.body for p in got if p.code == ch.S_NODE))
        assert (upd.nodeState, upd.userId) == (ch.FIGHTING, a.user_id)
        assert bt.S_REINFORCE in {p.code for p in await a.fight(prepare) + await a.idle()}
        report = pb.BattleReportMsg.FromString((await b.until(4103))[-1].body)
        assert report.battleResult == 1 and report.gpBonus > 0  # o prêmio junto
        await b.idle()
        assert not sb.campaign.fighting
