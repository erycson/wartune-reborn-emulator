"""Mapa do tesouro, "Lost Treasure" (8744 ops 1-6, 4634, 8745): handlers/treasure.py, migração 0105."""

from __future__ import annotations

from pathlib import Path

import pytest

from tests.game.harness import Game, logged_in
from tests.test_end_to_end import TEMPLATES
from wartune_server.domain.models import Item
from wartune_server.game import battle as battle_mod
from wartune_server.game import rules
from wartune_server.game.handlers import treasure as T
from wartune_server.game.session import GameSession
from wartune_server.protocol.messages import wartune_pb2 as pb

pytestmark = pytest.mark.skipif(not TEMPLATES.exists(), reason="precisa de data/templates")


def _session(g: Game) -> GameSession:
    s = g.server.online.get(g.user_id)
    assert s is not None and s.snapshot is not None
    return s


async def _pronto(g: Game, point: int = 0) -> GameSession:
    s = _session(g)
    assert s.snapshot is not None
    s.snapshot.character.grades, s.snapshot.character.point = 55, point
    await g.server.services.characters.save(s.snapshot.character)
    return s


def _mapa(s: GameSession) -> Item:
    assert s.snapshot is not None
    return next(i for i in s.snapshot.items if 2190001 <= i.template_id <= 2190004)


async def _estado(g: Game, op: int, **kw: object) -> pb.PlayerTreasureMsg:
    g.client.send(8744, pb.PlayerTreasureMsg(opType=op, **kw))  # type: ignore[arg-type]
    return pb.PlayerTreasureMsg.FromString((await g.until(4633))[-1].body)


async def test_recebe_o_mapa_com_o_lugar_do_tesouro(tmp_path: Path) -> None:
    async with logged_in(tmp_path, novice=19000) as g:
        s = await _pronto(g)
        state = await _estado(g, 1)
        assert (state.joinCount, state.index, state.isFirstGet) == (1, 0, True)
        m = _mapa(s)
        assert m.template_id == 2190001 and m.random_skill == 10000  # Cloud City
        assert 0 < m.random_skill_2 <= 5000 and 0 < m.random_skill_3 <= 5000  # pixels dentro do mapa (5000x5000)


async def test_melhora_direto_a_lendaria_gasta_vinho_e_balens(tmp_path: Path) -> None:
    async with logged_in(tmp_path, novice=19000) as g:
        s = await _pronto(g, point=100)
        assert s.snapshot is not None
        wine = Item(g.user_id, T.WINE, count=3, pos=40)
        s.snapshot.items.append(wine)
        await g.server.services.characters.save(wine)
        state = await _estado(g, 2, refreshType=True, payType=1)
        assert (state.index, state.isFirstQuest) == (T.TOP, True)
        assert s.snapshot.character.point == 100 - (8 - 3) * 5  # treasure_refresh_item 8: 3 vinhos + 25 Balens
        assert not any(i.template_id == T.WINE for i in s.snapshot.items)
        assert (await _estado(g, 2, refreshType=False, payType=1)).index == T.TOP  # já no topo: nada muda
        assert (await _estado(g, 1)).index == 0  # recebe a lendária e recomeça da primeira
        assert _mapa(s).template_id == 2190004


async def test_melhora_sem_saldo_e_recusada(tmp_path: Path) -> None:
    async with logged_in(tmp_path, novice=19000) as g:
        s = await _pronto(g, point=0)
        assert (await _estado(g, 2, refreshType=False, payType=1)).index == 0
        assert s.snapshot is not None and s.snapshot.character.point == 0


async def test_longe_do_tesouro_nao_luta(tmp_path: Path) -> None:
    async with logged_in(tmp_path, novice=19000) as g:
        s = await _pronto(g)
        await _estado(g, 1)
        m = _mapa(s)
        s.space_pos = (m.random_skill_2 // 20 + 16, m.random_skill_3 // 20)  # 16 tiles: fora dos 15
        await _estado(g, 5, index=m.pos)
        assert s.battle is None


async def test_escava_vence_e_leva_o_premio(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    async def win(battle: battle_mod.Battle) -> bool:
        for unit in battle.units:
            if unit.side == 2:
                unit.hp = 0
        return True

    quests: list[int] = []

    async def count(_s: GameSession, kind: int, *_: object) -> None:
        quests.append(kind)

    monkeypatch.setattr(battle_mod, "FRAME_SECONDS", 0.001)
    monkeypatch.setattr(battle_mod.Battle, "_fight", win)
    monkeypatch.setattr(T, "count_quest", count)
    async with logged_in(tmp_path, novice=19000) as g:
        s = await _pronto(g)
        await _estado(g, 1)
        m = _mapa(s)
        s.space_pos = (m.random_skill_2 // 20, m.random_skill_3 // 20)
        g.client.send(8744, pb.PlayerTreasureMsg(opType=5, index=m.pos))
        prepare = pb.BattlePrepareMsg.FromString((await g.until(157))[-1].body)
        assert [h.tempId for h in prepare.heros if h.side == 2] == [72009]  # Master Treasure Thief nível 55
        assert quests == [rules.LOST_TREASURE_CONDITION]
        codes = [p.code for p in await g.fight(prepare) + await g.idle()]
        assert codes.index(4103) < codes.index(4634)
        assert s.snapshot is not None and m in s.snapshot.items  # o mapa só some no 4 com isReward
        state = await _estado(g, 4, index=m.pos, isReward=True)
        assert state.rewardCount == 1
        assert m not in s.snapshot.items
        shards = sum(i.count for i in s.snapshot.items if i.template_id == T.SHARD)
        assert shards == 9  # Property6 do Uncommon
        saved = await g.server.services.characters.snapshot(g.user_id)
        assert saved.treasure[0].reward_count == 1 and m.template_id not in [i.template_id for i in saved.items]


async def test_escavar_ja_cobra_e_derrota_guarda_o_mapa(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    async def lose(battle: battle_mod.Battle) -> bool:
        for unit in battle.units:
            if unit.side == 1:
                unit.hp = 0
        return False

    monkeypatch.setattr(battle_mod, "FRAME_SECONDS", 0.001)
    monkeypatch.setattr(battle_mod.Battle, "_fight", lose)
    async with logged_in(tmp_path, novice=19000) as g:
        s = await _pronto(g, point=30)
        await _estado(g, 1)
        m = _mapa(s)
        s.space_pos = (10, 10)  # longe: o escavar já não olha o lugar
        g.client.send(8744, pb.PlayerTreasureMsg(opType=3, index=m.pos, payType=1))
        prepare = pb.BattlePrepareMsg.FromString((await g.until(157))[-1].body)
        assert s.snapshot is not None and s.snapshot.character.point == 5  # treasure_imm_battle 25
        await g.fight(prepare)
        await g.idle()
        assert m in s.snapshot.items and T._digs.get(g.user_id) is None
        assert (await _estado(g, 4, index=m.pos, isReward=True)).rewardCount == 0
