"""Masmorra Kurt İni (campanha 1001, mapas 1011 e 1021) com cliente falso: entrar, lutar, Pandora, baú, fim."""

from __future__ import annotations

from pathlib import Path

import pytest

from tests.game.harness import Game, logged_in
from tests.test_end_to_end import DATA
from wartune_server.content import dungeon
from wartune_server.game import battle as battle_mod
from wartune_server.game import drops
from wartune_server.game.campaign import DONE, CampaignMap
from wartune_server.protocol import Packet
from wartune_server.protocol.messages import wartune_pb2 as pb

pytestmark = pytest.mark.skipif(not (DATA / "xml/tempinfos.xml").exists(), reason="precisa de data/overlay")

WOLVES_1011 = (101102, 101103, 101105, 101106)  # o 101109 também é lobo, mas espera o 5180 (``finish_fight``)
WOLVES_1021 = (102102, 102103, 102105, 102106)  # o 102106 traz o param4 que libera o chefe 102109
END = [137, 4151, 83, 20, 135, 4165, 150, 150, 140, 115, 26, 83, 134]  # fim do mapa com carta (replay #1215-#1243)


@pytest.fixture(autouse=True)
def fast_battles(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(battle_mod, "FRAME_SECONDS", 0.001)


def codes(packets: list[Packet]) -> list[int]:
    return [p.code for p in packets]


async def enter(g: Game) -> list[Packet]:
    g.client.send(5039, pb.CampaignReqMsg(paraInt1=1, paraInt2=1001))  # sem tipo C>S no opcodes.json: corpo cru
    return await g.idle()


async def win(g: Game, prepare: pb.BattlePrepareMsg) -> list[Packet]:
    got = await g.fight(prepare)
    assert pb.BattleReportMsg.FromString(next(p.body for p in got if p.code == 4103)).battleResult == 1
    return got


async def battle(g: Game, camp: int) -> list[Packet]:
    """Chegada ao lobo, vitória e os pacotes da luta (4103 incluso)."""
    g.client.send(5125, pb.CampaignReqMsg(paraInt1=camp, paraBool1=True))
    return await win(g, pb.BattlePrepareMsg.FromString((await g.until(157))[-1].body))


async def finish_fight(g: Game, camp: int, card_index: int) -> list[Packet]:
    """Luta que só começa com o 5180 (último lobo e chefe). O 5122 com a carta vem antes do fim do mapa."""
    g.client.send(5125, pb.CampaignReqMsg(paraInt1=camp, paraBool1=True))
    assert await g.idle() == []  # chegada guardada, sem 157 até o 5180 (replay #1169 -> #1186)
    g.client.send(5122, pb.CampaignReqMsg(paraInt2=card_index))
    g.client.send(5180, pb.CampaignReqMsg())
    return await win(g, pb.BattlePrepareMsg.FromString((await g.until(157))[-1].body))


async def play_1011(g: Game, card_index: int) -> list[Packet]:
    """Entra no 1011 e vence os quatro lobos; o 101109 fecha o mapa e devolve os pacotes do fim."""
    await enter(g)
    for camp in WOLVES_1011:
        await battle(g, camp)
    return await finish_fight(g, 101109, card_index)


async def test_entrada_manda_o_mapa_1011(tmp_path: Path) -> None:
    async with logged_in(tmp_path, novice=25500) as g:
        got = await enter(g)
        assert codes(got) == [125, 140, 21, 127, 130, 143, 138]
        assert pb.RoomCreatedMsg.FromString(got[0].body).room.campaignId == 1011
        assert len(pb.CampaignNodeListMsg.FromString(got[3].body).node) == 10
        fog = pb.CampaignFogMsg.FromString(got[4].body)
        assert (fog.row, fog.col) == (24, 19)  # névoa da captura, não a de 'tudo visível'


async def test_lobo_comeca_a_luta_na_chegada_e_da_exp(tmp_path: Path) -> None:
    async with logged_in(tmp_path, novice=25500) as g:
        await enter(g)
        g.client.send(5125, pb.CampaignReqMsg(paraInt1=101102, paraBool1=True))
        start = await g.until(157)
        assert codes(start) == [140, 131, 128, 157]
        prepare = pb.BattlePrepareMsg.FromString(start[-1].body)
        assert prepare.mapTempId == 1011
        got = await win(g, prepare)
        node = pb.CampaignNodeUpdateMsg.FromString([p for p in got if p.code == 128][-1].body)
        assert (node.nodeId, node.nodeState) == (9561, DONE)  # nó do 101102 vira DONE
        assert pb.FightOverMoiveMsg.FromString(next(p.body for p in got if p.code == 4382)).gp == 35


async def test_ultimo_lobo_so_comeca_com_o_5180(tmp_path: Path) -> None:
    async with logged_in(tmp_path, novice=25500) as g:
        await enter(g)
        g.client.send(5125, pb.CampaignReqMsg(paraInt1=101109, paraBool1=True))
        assert await g.idle() == []
        g.client.send(5180, pb.CampaignReqMsg())
        assert codes(await g.until(157)) == [140, 131, 128, 157]


async def test_pandora_pede_confirmacao_e_da_buff_uma_vez(tmp_path: Path) -> None:
    async with logged_in(tmp_path, novice=25500) as g:
        await enter(g)
        g.client.send(5125, pb.CampaignReqMsg(paraInt1=101107, paraBool1=True))
        assert codes(await g.until(29)) == [29]

        g.client.send(5033, pb.CampaignReqMsg(paraInt1=880, paraInt2=101107, paraBool1=True))  # mapa da 1021
        assert await g.idle() == []  # confirmação de outro mapa não abre a caixa

        g.client.send(5033, pb.CampaignReqMsg(paraInt1=879, paraInt2=101107, paraBool1=True))
        got = await g.until(111)
        assert codes(got) == [4126, 4165, 128, 111]
        stand = pb.StandPosMsg.FromString(got[0].body)
        assert (stand.posX, stand.posY) == (26, 26)  # nó (24, 24) + 2, como nas duas Pandoras da captura
        assert pb.CampaignBufferMsg.FromString(got[1].body).bufferInfo[0].bufferTempId == 1301
        assert pb.ChatChannelMsg.FromString(got[3].body).encodeMsg == dungeon()["maps"]["1011"]["pandora"]["alert"]

        g.client.send(5033, pb.CampaignReqMsg(paraInt1=879, paraInt2=101107, paraBool1=True))
        assert await g.idle() == []  # nó já DONE: sem segunda caixa


async def test_bau_de_ouro_da_500_uma_vez_e_grava(tmp_path: Path) -> None:
    async with logged_in(tmp_path, novice=25500) as g:
        await enter(g)
        characters = g.server.services.characters
        before = (await characters.snapshot(g.user_id)).character.gold
        g.client.send(5125, pb.CampaignReqMsg(paraInt1=101108, paraBool1=True))
        got = await g.until(126)
        assert codes(got) == [128, 126]
        assert pb.CampaignNotifyMsg.FromString(got[1].body).body == "Kazanılan: Altın 500"
        assert (await characters.snapshot(g.user_id)).character.gold == before + 500

        g.client.send(5125, pb.CampaignReqMsg(paraInt1=101108, paraBool1=True))
        assert await g.idle() == []  # nó DONE: o ouro sai uma vez só
        assert (await characters.snapshot(g.user_id)).character.gold == before + 500


def test_chefe_so_aparece_com_o_grupo_caido() -> None:
    camp = CampaignMap.enter_dungeon(1021)
    assert camp.locked(102109)  # 102106 libera o chefe (param4 "102109,1") e o grupo está vivo
    assert not camp.locked(102107)  # a Pandora não depende de grupo
    for wolf in WOLVES_1021:
        camp.nodes[wolf]["state"] = DONE
    assert not camp.locked(102109)


async def test_mapa_1011_fecha_com_carta_gravada(tmp_path: Path) -> None:
    async with logged_in(tmp_path, novice=25500) as g:
        end = await play_1011(g, card_index=2)
        assert codes(end)[-len(END) :] == END
        take = pb.CampaignTakeCardsMsg.FromString(next(p.body for p in end if p.code == 26))
        card = pb.ItemMovedListMsg.FromString(next(p.body for p in end if p.code == 115)).moved[0].item
        assert (take.index, take.templateId) == (2, card.templateId)
        assert card.templateId in drops.pool(g.server.services.templates, 1001)
        snap = await g.server.services.characters.snapshot(g.user_id)
        assert card.templateId in [i.template_id for i in snap.items]  # gravada: lida do banco, não da sessão


async def test_grupo_de_1021_libera_o_chefe_e_fecha_a_masmorra(tmp_path: Path) -> None:
    async with logged_in(tmp_path, novice=25500) as g:
        await play_1011(g, card_index=2)
        got = await enter(g)
        assert codes(got) == [125, 140, 21, 127, 130, 143]  # sem plot: o diálogo é só do 1011
        assert pb.RoomCreatedMsg.FromString(got[0].body).room.campaignId == 1021

        g.client.send(5125, pb.CampaignReqMsg(paraInt1=102109, paraBool1=True))
        assert await g.idle() == []  # chefe travado enquanto o grupo vive

        for camp in WOLVES_1021[:-1]:
            await battle(g, camp)
        last = await battle(g, WOLVES_1021[-1])
        after = codes(last)[codes(last).index(4382) + 1 :]
        assert after == [126, 143, 143, 128]  # aviso, DISAPPEARD do gatilho, FLICKER do chefe, nó novo
        movies = [pb.PlayerMovieMsg.FromString(p.body) for p in last if p.code == 143]
        assert [(m.movieType, m.targetId) for m in movies] == [("DISAPPEARD", 9579), ("FLICKER", 9578)]
        notice = next(p.body for p in last if p.code == 126)
        assert pb.CampaignNotifyMsg.FromString(notice).body == dungeon()["notices"]["1021"]

        characters = g.server.services.characters
        strategy = (await characters.snapshot(g.user_id)).character.strategy
        boss = await finish_fight(g, 102109, card_index=1)
        assert codes(boss)[-len(END) :] == END
        assert (await characters.snapshot(g.user_id)).character.strategy == strategy + 72  # "Ruh" do chefe


async def test_5126_devolve_a_nevoa_revelada(tmp_path: Path) -> None:
    async with logged_in(tmp_path, novice=25500) as g:
        await enter(g)
        req = pb.CampaignFogDataListReqMsg(
            dataList=[pb.CampaignFogDataReqMsg(index=5, fogByte=1), pb.CampaignFogDataReqMsg(index=9, fogByte=0)]
        )
        g.client.send(5126, req)
        got = await g.until(19)
        update = pb.CampaignFogUpdateMsg.FromString(got[-1].body).fogUpdate
        assert [(u.index, u.fogByte) for u in update] == [(5, 1), (9, 0)]
