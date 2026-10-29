"""Guarda de batalha (8742/4631): abrir encaixe, encaixar e tirar gema, resistências no herói, a missão 926
(tipo 90) e o login com o estado gravado. Composição/nível das gemas é a receita comum do 5153
(ComposeTempInfos Types 6). Ver docs/salas-campanha.md."""

from datetime import UTC, datetime
from pathlib import Path

import pytest

from tests.game.harness import Game, logged_in
from tests.test_end_to_end import TEMPLATES
from wartune_server.domain.models import Item, PlayerSnapshot, Quest
from wartune_server.game import bag
from wartune_server.protocol.messages import wartune_pb2 as pb

pytestmark = pytest.mark.skipif(not TEMPLATES.exists(), reason="precisa de data/templates")
FIRE_1, FIRE_2, WILL_1, MARK = 3120101, 3120102, 3120001, 2100032  # Lvl. 1/2 Fire Resistance, Will Crystal, Mark
ESSENCE = 208028  # Material1 da receita 254 (100 -> Lvl. 1 Fire Resistance Crystal)


def _snap(g: Game) -> PlayerSnapshot:
    s = g.server.online.get(g.user_id)
    assert s is not None and s.snapshot is not None
    return s.snapshot


async def _grow(g: Game, grades: int, *items: Item) -> PlayerSnapshot:
    snap = _snap(g)
    snap.character.grades = grades
    snap.items.extend(items)
    await g.server.services.characters.save(snap.character, *items)
    return snap


def _guard(got: list) -> list[tuple[int, int, int, int, int]]:
    msg = pb.HeroWatchMsg.FromString([p for p in got if p.code == 4631][-1].body)
    return [(w.gridType, w.gridPos, w.jion1, w.jion2, w.jion3) for w in msg.watchInfo]


def _op(g: Game, op: int, grid: int, pos: int, jion: int = 0, item: int = 0) -> None:
    g.client.send(8742, pb.HeroWatchOpMsg(opType=op, gridType=grid, gridPos=pos, jionPos=jion, itemPos=item))


async def test_abre_encaixa_tira_e_soma_resistencia(tmp_path: Path) -> None:
    async with logged_in(tmp_path, novice=33000) as g:
        snap = await _grow(g, 56, Item(g.user_id, FIRE_1, pos=0, count=2), Item(g.user_id, FIRE_2, pos=1))
        snap.quests.append(Quest(g.user_id, 926, datetime.now(UTC)))

        _op(g, 2, 2, 1, 1, 0)  # encaixe fechado: recusa e manda o estado (vazio)
        assert _guard(await g.until(4631)) == []
        _op(g, 1, 2, 2)  # entalhe 2 pede nível 60
        assert _guard(await g.until(4631)) == []
        _op(g, 1, 2, 1)
        assert _guard(await g.until(150)) == [(2, 1, 0, 0, 0)]

        _op(g, 2, 2, 1, 1, 0)
        got = await g.until(112)
        assert _guard(got) == [(2, 1, FIRE_1, 0, 0)]
        hero = pb.ArmyArmyMsg.FromString([p.body for p in got if p.code == 150][-1]).simpleHeroInfo
        assert hero.fireResi == 10  # Lvl. 1 Fire Resistance Crystal: FireResi 10
        quest = pb.QuestUpdatedRspMsg.FromString(got[-1].body).quest
        assert [(q.templateId, q.condition_1) for q in quest] == [(926, 1)]
        assert bag.count_of(snap, FIRE_1) == 1

        _op(g, 2, 2, 1, 2, 0)  # outra de fogo no mesmo entalhe: recusa (existSameGoods)
        assert _guard(await g.until(4631)) == [(2, 1, FIRE_1, 0, 0)]
        _op(g, 2, 2, 1, 1, 1)  # troca: a Lvl. 2 entra, a Lvl. 1 volta
        got = await g.until(150)
        assert _guard(got) == [(2, 1, FIRE_2, 0, 0)] and bag.count_of(snap, FIRE_1) == 2
        assert pb.ArmyArmyMsg.FromString(got[-1].body).simpleHeroInfo.fireResi == 18

        _op(g, 3, 2, 1, 1)
        got = await g.until(150)
        assert _guard(got) == [(2, 1, 0, 0, 0)] and bag.count_of(snap, FIRE_2) == 1
        assert pb.ArmyArmyMsg.FromString(got[-1].body).simpleHeroInfo.fireResi == 0

        _op(g, 2, 2, 1, 3, 0)
        await g.until(150)
        saved = await g.server.services.characters.snapshot(g.user_id)
        assert saved.systems.battle_guard == f"2:1:0:0:{FIRE_1}"  # type: ignore[union-attr]

        # relogin: o 4631 do login leva o estado gravado
        g2 = await g.connect()
        g2.client.send(8224, pb.PlayerDataMsg(army=True))
        assert _guard(await g2.until(4631)) == [(2, 1, 0, 0, FIRE_1)]


async def test_kingdom_mark_e_willpower(tmp_path: Path) -> None:
    """Entalhes 3 a 5 gastam 1 Kingdom Mark; a Willpower (ActiveObject 7) pede 300 de resistência somada."""
    async with logged_in(tmp_path, novice=33000) as g:
        snap = await _grow(g, 80, Item(g.user_id, WILL_1, pos=0), Item(g.user_id, MARK, pos=1))
        _op(g, 1, 1, 1)
        assert _guard(await g.until(4631)) == []  # sem resistência
        _op(g, 1, 2, 3)
        got = await g.until(150)
        assert _guard(got) == [(2, 3, 0, 0, 0)] and bag.count_of(snap, MARK) == 0
        _op(g, 1, 2, 4)  # sem outra Mark
        assert _guard(await g.until(4631)) == [(2, 3, 0, 0, 0)]
        _op(g, 1, 2, 6)  # o 6º nunca abre ("unopen")
        assert _guard(await g.until(4631)) == [(2, 3, 0, 0, 0)]
        _op(g, 2, 2, 3, 1, 0)  # Will Crystal só na Willpower
        assert _guard(await g.until(4631)) == [(2, 3, 0, 0, 0)]


async def test_gema_tirada_com_mochila_cheia_vai_pelo_correio(tmp_path: Path) -> None:
    async with logged_in(tmp_path, novice=33000) as g:
        snap = await _grow(g, 56, Item(g.user_id, FIRE_1, pos=0))
        _op(g, 1, 2, 1)
        await g.until(150)
        _op(g, 2, 2, 1, 1, 0)
        await g.until(150)
        filler = [Item(g.user_id, MARK, pos=p) for p in bag.free_positions(snap, datetime.now(UTC))]
        snap.items.extend(filler)
        await g.server.services.characters.save(*filler)
        _op(g, 3, 2, 1, 1)
        got = await g.until(150)
        got += await g.idle()
        assert _guard(got) == [(2, 1, 0, 0, 0)] and 148 in [p.code for p in got]  # aviso de correio novo
        saved = await g.server.services.characters.snapshot(g.user_id)
        assert bag.count_of(saved, FIRE_1) == 0


async def test_compor_e_subir_nivel_das_gemas(tmp_path: Path) -> None:
    """ComposeTempInfos Types 6: 100 Essence -> Lvl. 1 (receita 254); a de nível 2 sai das de nível 1."""
    async with logged_in(tmp_path, novice=33000) as g:
        snap = await _grow(g, 56, Item(g.user_id, ESSENCE, pos=0, count=100))
        snap.character.gold = 10_000
        g.client.send(5153, pb.StoreReqMsg(composeId=254, composeNum=1))
        await g.until(89)
        assert bag.count_of(snap, FIRE_1) == 1 and bag.count_of(snap, ESSENCE) == 0
        templates = g.server.services.templates
        assert next(templates.find("ComposeTempInfos", Types="6", NewMaterial=FIRE_2))["Material1"] == str(FIRE_1)


def test_golpe_elemental_tira_menos_com_gema_de_resistencia() -> None:
    """Mascote de fogo (Amazon Queen, PetType 101) contra o herói: com FireResi da guarda o mesmo golpe (mesmo
    sorteio) tira menos; o ReduceResi (Willpower) do autor desconta a resistência."""
    import random

    from tests.game.test_batalha import _battle, _unit
    from wartune_server.game import battle as bt

    pet = {"livingId": 6, "tempId": 101101, "side": 2, "pos": 6, "maxHp": 500, "hp": 500, "defaultSkill": 30000}
    b, _ = _battle(pets=[pet])
    queen, hero = _unit(b, 6), _unit(b, 3)
    assert queen.element == "FireResi"
    row = {"Parameter1": "100", "Parameter2": "50"}

    def hit() -> int:
        b.rng = random.Random(7)
        return b._hit(queen, hero, row, 1)[0]

    plain = hit()
    hero.resists = {"FireResi": 72}  # Lvl. 6 Fire Resistance Crystal
    resisted = hit()
    assert resisted < plain
    queen.resists["ReduceResi"] = 72
    assert hit() == plain
    assert bt.resist_factor(hero, queen) == 1.0  # golpe sem elemento não muda
