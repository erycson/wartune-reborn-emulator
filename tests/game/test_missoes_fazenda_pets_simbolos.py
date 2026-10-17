"""Missões da fazenda, da montaria, dos símbolos (runas), do torneio de fadas e do mapa da cidade (tipos 59,
60, 61, 71, 76, 77, 78, 37 e 87). Cada tipo: a ação do cliente, o 112 com o progresso e, nos de estado
(76, 78, 37), a missão aceita depois do fato já nascendo cumprida (``rules.update_state_quests``).
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest

from tests.game.harness import Game, logged_in
from tests.game.test_pvp import body, give_pet
from wartune_server.domain.models import Item, PlayerSnapshot, Quest
from wartune_server.game import arena as A
from wartune_server.game import battle as battle_mod
from wartune_server.game import farm
from wartune_server.protocol.messages import wartune_pb2 as pb
from wartune_server.services.clock import FakeClock

SEED = 2160001  # Ucuz Altın İnciri: amadurece em 59 min (como em test_castelo)
BOOK, STONE, FOOD = 3020002, 3020010, 208017  # livro da runa 201 (tipo 2), pedra de EXP das runas, comida de montaria


def codes(packets: list[Any]) -> list[int]:
    return [p.code for p in packets]


def snap_of(g: Game) -> PlayerSnapshot:
    session = g.server.online.get(g.user_id)
    assert session is not None and session.snapshot is not None
    return session.snapshot


async def _set(g: Game, **fields: int) -> PlayerSnapshot:
    snap = snap_of(g)
    for name, value in fields.items():
        setattr(snap.character, name, value)
    await g.server.services.characters.save(snap.character)
    return snap


def quest_msgs(packets: list[Any]) -> dict[int, int]:
    """Missão -> condition_1 (progresso) de cada 112 recebido."""
    return {
        q.templateId: q.condition_1
        for p in packets
        if p.code == 112
        for q in pb.QuestUpdatedRspMsg.FromString(p.body).quest
    }


def _accepted(g: Game, *template_ids: int) -> None:
    now = datetime.now(UTC)
    snap_of(g).quests.extend(Quest(g.user_id, t, now) for t in template_ids)


# --- fazenda (59, 60, 61) --------------------------------------------------------------------------


async def _seed_in_bag(g: Game, count: int) -> None:
    seeds = Item(g.user_id, SEED, pos=0, count=count)
    snap_of(g).items.append(seeds)
    await g.server.services.characters.save(seeds)


def _plant(pos: int) -> pb.FarmOperReqMsg:
    return pb.FarmOperReqMsg(friendId=0, opType=1, pos=pos, bagPos=0, templateId=SEED)


async def test_quest_59_plantar_na_fazenda(tmp_path: Path) -> None:
    """59 (QuestTemps 262/859, Para1 0, Para2 1): plantar uma semente na própria fazenda conta 1."""
    clock = FakeClock()
    async with logged_in(tmp_path, novice=20000, clock=clock) as g:
        _accepted(g, 262)
        await _seed_in_bag(g, 2)
        g.client.send(15044, _plant(0))
        got = await g.until(112)
        assert codes(got)[-2:] == [4387, 112]  # o 112 vem depois da resposta da terra (como o 4387 do plantio)
        assert quest_msgs(got) == {262: 1}


async def test_quest_60_colher_a_propria_fazenda(tmp_path: Path) -> None:
    """60 (QuestTemps 263, Para1 0, Para2 2): colher a própria terra madura conta 1 por colheita."""
    clock = FakeClock()
    async with logged_in(tmp_path, novice=20000, clock=clock) as g:
        _accepted(g, 263)
        await _seed_in_bag(g, 2)
        g.client.send(15044, _plant(0))
        await g.until(4387)
        clock.advance(59 * 60)
        g.client.send(15044, pb.FarmOperReqMsg(friendId=g.user_id, opType=4, pos=0))
        assert quest_msgs(await g.until(112)) == {263: 1}


async def test_quest_61_praga_conta_e_o_mato_nao(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """61 (QuestTemps 267, Para1 1, Para2 2): tirar a praga (2) conta; o mato (3) não é praga."""
    monkeypatch.setattr(farm, "has_worm", lambda land, now: True)
    monkeypatch.setattr(farm, "has_grass", lambda land, now: True)
    clock = FakeClock()
    async with logged_in(tmp_path, novice=20000, clock=clock) as g:
        _accepted(g, 267)
        await _seed_in_bag(g, 2)
        g.client.send(15044, _plant(0))
        await g.until(4387)
        g.client.send(15044, pb.FarmOperReqMsg(friendId=g.user_id, opType=3, pos=0))  # mato
        assert 112 not in codes(await g.idle())
        g.client.send(15044, pb.FarmOperReqMsg(friendId=g.user_id, opType=2, pos=0))  # praga
        assert quest_msgs(await g.until(112)) == {267: 1}


# --- montaria (71) ---------------------------------------------------------------------------------


async def test_quest_71_treino_de_montaria(tmp_path: Path) -> None:
    """71 (QuestTemps 753, Para2 1): uma ação de treino (Kültür) conta, qualquer que seja a quantidade."""
    async with logged_in(tmp_path, novice=19000) as g:
        snap = snap_of(g)
        sy = snap.systems
        assert sy is not None
        sy.mount_avatars, sy.mount_template, sy.mount_gp = "1000,1103", 1103, "1610,270,970,1160"
        food = Item(g.user_id, FOOD, pos=0, count=9)
        snap.items.append(food)
        _accepted(g, 753)
        await g.server.services.characters.save(sy, food)
        g.client.send(8529, pb.MountEditMsg(op=1, propertyType=0, payType=1, param1=9))
        got = await g.until(112)
        assert codes(got)[-1] == 112 and codes(got)[-2] == 4426  # o 112 sai depois da montaria
        assert quest_msgs(got) == {753: 1}


# --- símbolos (76, 77, 78) -------------------------------------------------------------------------


async def _learn_attack_rune(g: Game) -> None:
    leader = snap_of(g).leader
    assert leader is not None
    leader.grades = 41  # grau 3 da runa exige 41
    book, stones = Item(g.user_id, BOOK, pos=0), Item(g.user_id, STONE, pos=1, count=25)
    snap_of(g).items.extend([book, stones])
    await g.server.services.characters.save(leader, book, stones)
    g.client.send(8605, pb.HeroRuneOpMsg(opType=1, runeId=201, learnRunePos=0, learnRuneCount=1))
    assert pb.HeroRuneOpMsg.FromString((await g.until(4495))[-1].body).opResult


async def test_quest_76_aprender_simbolo_e_aceitar_depois(tmp_path: Path) -> None:
    """76 (QuestTemps 906, Para1 2 = Saldırma/ataque, Para2 1): aprender a runa conta. Aceita depois de
    aprendida, a missão nasce com 1 (o cliente julga pelo símbolo que o herói tem: checkRuneStudy)."""
    async with logged_in(tmp_path, novice=19000) as g:
        await _learn_attack_rune(g)
        g.client.send(5012, pb.QuestAddedMsg(questId=[906]))
        assert quest_msgs(await g.until(112)) == {906: 1}


async def test_quest_77_pedras_gastas_no_simbolo(tmp_path: Path) -> None:
    """77 (QuestTemps 186, Para1 3020010, Para2 5): cada pedra gasta no símbolo conta 1 (a quantidade
    que o cliente manda); aprender a runa não conta."""
    async with logged_in(tmp_path, novice=19000) as g:
        await _learn_attack_rune(g)
        _accepted(g, 186)
        g.client.send(8605, pb.HeroRuneOpMsg(opType=2, runeId=201, count=11))  # 11 pedras: 550 EXP, sobe ao 202
        assert quest_msgs(await g.until(112)) == {186: 11}


async def test_quest_78_grau_do_simbolo_e_aceitar_depois(tmp_path: Path) -> None:
    """78 (QuestTemps 910, Para1 0, Para2 3): o símbolo chegar ao grau 3 (o maior valor). Aceita depois,
    nasce com o grau que o símbolo já tem, e o 5014 fecha a missão."""
    async with logged_in(tmp_path, novice=19000) as g:
        await _learn_attack_rune(g)
        g.client.send(8605, pb.HeroRuneOpMsg(opType=2, runeId=201, count=11))  # 202
        await g.until(4495)
        g.client.send(8605, pb.HeroRuneOpMsg(opType=2, runeId=202, count=13))  # 650 EXP: 202 -> 203 (grau 3)
        op = pb.HeroRuneOpMsg.FromString((await g.until(4495))[-1].body)
        assert [r.runeId for r in op.runeInfo.runeinfo] == [203]
        g.client.send(5012, pb.QuestAddedMsg(questId=[910]))
        assert quest_msgs(await g.until(112)) == {910: 3}
        g.client.send(5014, pb.QuestFinishedReqMsg(templateId=910))
        assert 52 in codes(await g.until(52))


# --- cidade (37) -----------------------------------------------------------------------------------


async def test_quest_37_cidade_no_mapa_da_missao(tmp_path: Path) -> None:
    """37 (QuestTemps 390 = mapa 2 'Sis Ormanı', Para2 2): transferir a cidade para o mapa 2 conta; mudar de
    ponto dentro do mapa da instância (100000xxx) não conta; o 5014 fecha a missão."""
    async with logged_in(tmp_path, novice=19000) as g:
        snap = await _set(g, grades=25)
        castle = snap.castle
        assert castle is not None
        castle.energy = 500
        g.client.send(5012, pb.QuestAddedMsg(questId=[390]))
        assert quest_msgs(await g.until(112)) == {390: 0}

        g.client.send(5176, pb.CastleReqMsg(magId=castle.map_id, posX=10, posY=12, payType=1))  # mesmo mapa
        assert 112 not in codes(await g.until(105))

        g.client.send(5176, pb.CastleReqMsg(magId=2, posX=0, posY=0, payType=1))  # mapa 2: pede nível 21
        assert quest_msgs(await g.until(112)) == {390: 2}
        g.client.send(5014, pb.QuestFinishedReqMsg(templateId=390))
        assert 52 in codes(await g.until(52))


async def test_quest_37_aceita_depois_de_estar_no_mapa(tmp_path: Path) -> None:
    """37: a cidade já está no mapa 2 quando a 390 é aceita: nasce com 2 e fecha no 5014 (checkMapId)."""
    async with logged_in(tmp_path, novice=19000) as g:
        snap = await _set(g, grades=25)
        castle = snap.castle
        assert castle is not None
        castle.energy = 500
        g.client.send(5176, pb.CastleReqMsg(magId=2, posX=0, posY=0, payType=1))
        await g.until(105)
        g.client.send(5012, pb.QuestAddedMsg(questId=[390]))
        assert quest_msgs(await g.until(112)) == {390: 2}
        g.client.send(5014, pb.QuestFinishedReqMsg(templateId=390))
        assert 52 in codes(await g.until(52))


# --- torneio de fadas (87) -------------------------------------------------------------------------


async def test_quest_87_torneio_de_fadas(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """87 (QuestTemps 504, Para2 1): participar do torneio conta ao fim da luta. Capturado: o 112 vem depois do
    4103 (peri_turnuvasi #47 -> #52); só a vitória foi capturada, a derrota conta também (dedução)."""
    monkeypatch.setattr(battle_mod, "FRAME_SECONDS", 0.004)
    monkeypatch.setattr(A, "PET_NOTICE_FRAME", 150)
    async with logged_in(tmp_path, novice=30001) as g:
        pet_id = await give_pet(g, 104101, 60)
        snap_of(g).character.grades = 55
        _accepted(g, 504)
        g.client.send(8725, pb.PlayerPetMsg(chaPos=f"{pet_id},-1,-1"))
        await g.until(4540)
        g.client.send(8256, pb.ChallengeRequestMsg(type=1))
        listed = body(await g.until(4611), 4611, pb.PetChallengeInfoMsg)
        g.client.send(8724, pb.PlayerChallengeMsg(tarUserId=listed.playerPets[0].userId))
        prepare = body(await g.until(157), 157, pb.BattlePrepareMsg)
        g.client.send(10007, pb.LoadOverMsg(armyId=g.user_id, battleId=prepare.battleId))
        got = await g.until(112)
        assert codes(got).index(112) > codes(got).index(4103)
        assert quest_msgs(got) == {504: 1}
