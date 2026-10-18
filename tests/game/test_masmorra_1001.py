"""Masmorra Kurt İni (campanha 1001, mapas 1011 e 1021) com cliente falso: entrar, lutar, Pandora, baú, fim."""

from __future__ import annotations

from pathlib import Path

import pytest

from tests.game.harness import Game, logged_in
from tests.game.test_missoes_fazenda_pets_simbolos import _done
from tests.test_end_to_end import TEMPLATES
from wartune_server.content import dungeon
from wartune_server.game import battle as battle_mod
from wartune_server.game import drops
from wartune_server.game.campaign import DONE, CampaignMap
from wartune_server.protocol import Packet
from wartune_server.protocol.messages import wartune_pb2 as pb

pytestmark = pytest.mark.skipif(not TEMPLATES.exists(), reason="precisa de data/templates")

WOLVES_1011 = (101102, 101103, 101105, 101106, 101109)  # o 101109 fecha o grupo e o mapa
WOLVES_1021 = (102102, 102103, 102105, 102106)  # o 102106 traz o param4 que libera o chefe 102109
END = [137, 4151, 83, 135, 4165, 150, 150, 140]  # fim do mapa, antes da carta (replay #1215-#1226, #1722-#1729)
END_COM_70 = [137, 4151, 83, 135, 112, 4165, 150, 150, 140]  # com a 70 no fim: o 112 entre o 135 e o 4165
CARD = [115, 26, 83, 134]  # resposta do 5122 (replay #1227-#1243, #1730-#1747, sem 4476/4484)
KURT_DIS, SANS_TASI = 2100001, 2040101  # drops dos lobos do 1021 (replay #1355-#1592)


@pytest.fixture(autouse=True)
def fast_battles(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(battle_mod, "FRAME_SECONDS", 0.001)


def codes(packets: list[Packet]) -> list[int]:
    return [p.code for p in packets]


async def enter(g: Game) -> list[Packet]:
    g.client.send(5039, pb.CampaignReqMsg(paraInt1=1, paraInt2=1001))  # sem tipo C>S no opcodes.json: corpo cru
    return await g.idle()


async def battle(g: Game, camp: int) -> list[Packet]:
    """Chegada ao nó, vitória e os pacotes da luta e do que vem depois (fim do mapa incluso)."""
    g.client.send(5125, pb.CampaignReqMsg(paraInt1=camp, paraBool1=True))
    got = await g.fight(pb.BattlePrepareMsg.FromString((await g.until(157))[-1].body))
    assert pb.BattleReportMsg.FromString(next(p.body for p in got if p.code == 4103)).battleResult == 1
    return got + await g.idle()


async def take(g: Game, index: int) -> list[Packet]:
    g.client.send(5122, pb.CampaignReqMsg(paraInt2=index))
    return await g.idle()


async def play_1011(g: Game) -> list[Packet]:
    """Entra no 1011 e vence os cinco lobos; devolve os pacotes da última luta (com o fim do mapa)."""
    await enter(g)
    got: list[Packet] = []
    for camp in WOLVES_1011:
        got = await battle(g, camp)
    return got


async def test_entrada_manda_o_mapa_1011(tmp_path: Path) -> None:
    async with logged_in(tmp_path, novice=25500) as g:
        got = await enter(g)
        assert codes(got) == [125, 140, 21, 127, 130, 143, 138, 3, 83]
        assert pb.RoomCreatedMsg.FromString(got[0].body).room.campaignId == 1011
        assert len(pb.CampaignNodeListMsg.FromString(got[3].body).node) == 10
        fog = pb.CampaignFogMsg.FromString(got[4].body)
        assert (fog.row, fog.col) == (24, 19)  # névoa da captura, não a de 'tudo visível'


async def test_cada_mapa_gasta_20_de_beden_e_sem_beden_nao_entra(tmp_path: Path) -> None:
    async with logged_in(tmp_path, novice=25500) as g:
        characters = g.server.services.characters
        before = (await characters.snapshot(g.user_id)).character.weary
        got = await enter(g)
        assert pb.PlayerMsg.FromString(got[-2].body).weary == before - 20
        assert (
            pb.ChatChannelMsg.FromString(got[-1].body).encodeMsg == "[Worg Lair] haritasına girildi, 20 can kullanıldı."
        )
        assert (await characters.snapshot(g.user_id)).character.weary == before - 20  # gravado

        session = g.server.online.get(g.user_id)
        assert session is not None and session.snapshot is not None
        session.snapshot.character.weary = 19
        session.campaign = None  # fora da masmorra, com 19 de Beden
        assert codes(await enter(g)) == []
        assert session.snapshot.character.weary == 19 and session.campaign is None


async def test_lobo_comeca_a_luta_na_chegada_e_da_exp(tmp_path: Path) -> None:
    async with logged_in(tmp_path, novice=25500) as g:
        await enter(g)
        g.client.send(5125, pb.CampaignReqMsg(paraInt1=101102, paraBool1=True))
        start = await g.until(157)
        assert codes(start) == [140, 131, 128, 157]
        prepare = pb.BattlePrepareMsg.FromString(start[-1].body)
        assert prepare.mapTempId == 1011
        got = await g.fight(prepare) + await g.idle()
        node = pb.CampaignNodeUpdateMsg.FromString([p for p in got if p.code == 128][-1].body)
        assert (node.nodeId, node.nodeState) == (9561, DONE)  # nó do 101102 vira DONE
        assert pb.FightOverMoiveMsg.FromString(next(p.body for p in got if p.code == 4382)).gp == 35


async def test_ultimo_lobo_comeca_na_chegada_sem_5180(tmp_path: Path) -> None:
    # o 5180 é do quadro das cartas (ChestFrame.dispose), não solta luta: a do 101109 sai no 5125
    async with logged_in(tmp_path, novice=25500) as g:
        await enter(g)
        g.client.send(5125, pb.CampaignReqMsg(paraInt1=101109, paraBool1=True))
        assert codes(await g.until(157)) == [140, 131, 128, 157]


async def test_pandora_pede_confirmacao_e_da_buff_uma_vez(tmp_path: Path) -> None:
    async with logged_in(tmp_path, novice=25500) as g:
        await enter(g)
        g.client.send(5125, pb.CampaignReqMsg(paraInt1=101107, paraBool1=True))
        assert codes(await g.until(29)) == [29]

        g.client.send(5033, pb.CampaignReqMsg(paraInt1=880, paraInt2=101107, paraBool1=True))  # mapa da 1021
        assert await g.idle() == []  # confirmação de outro mapa não abre a caixa

        g.client.send(5033, pb.CampaignReqMsg(paraInt1=879, paraInt2=101107, paraBool1=True))
        got = await g.idle()
        assert codes(got) == [4126, 4165, 150, 150, 128, 111, 83]  # replay #1155-#1161
        stand = pb.StandPosMsg.FromString(got[0].body)
        assert (stand.posX, stand.posY) == (26, 26)  # nó (24, 24) + 2, como nas duas Pandoras da captura
        assert pb.CampaignBufferMsg.FromString(got[1].body).bufferInfo[0].bufferTempId == 1301
        alert = dungeon()["maps"]["1011"]["pandora"]["alert"]
        assert [pb.ChatChannelMsg.FromString(p.body).encodeMsg for p in got[-2:]] == [alert, alert]

        g.client.send(5033, pb.CampaignReqMsg(paraInt1=879, paraInt2=101107, paraBool1=True))
        assert await g.idle() == []  # nó já DONE: sem segunda caixa


async def test_bau_de_ouro_da_500_uma_vez_e_grava(tmp_path: Path) -> None:
    async with logged_in(tmp_path, novice=25500) as g:
        await enter(g)
        characters = g.server.services.characters
        before = (await characters.snapshot(g.user_id)).character.gold
        g.client.send(5125, pb.CampaignReqMsg(paraInt1=101108, paraBool1=True))
        got = await g.idle()
        assert codes(got) == [109, 126, 128, 83]  # replay #1020-#1023
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


async def test_5122_so_vira_carta_depois_do_fim(tmp_path: Path) -> None:
    async with logged_in(tmp_path, novice=25500) as g:
        await enter(g)
        assert codes(await take(g, 2)) == []  # antes do 135 não há carta (o relay engana: S>C atrasado)


async def test_mapa_1011_fecha_e_a_carta_do_5122_fica_gravada(tmp_path: Path) -> None:
    async with logged_in(tmp_path, novice=25500) as g:
        end = await play_1011(g)
        assert codes(end)[-len(END) :] == END  # sem 115/26/134: a carta espera o clique
        assert codes(await take(g, 5)) == []  # index fora das 5 cartas (0..4)

        got = await take(g, 2)
        assert codes(got) == CARD
        take_msg = pb.CampaignTakeCardsMsg.FromString(got[1].body)
        card = pb.ItemMovedListMsg.FromString(got[0].body).moved[0].item
        assert (take_msg.index, take_msg.templateId) == (2, card.templateId)
        assert card.templateId in drops.pool(g.server.services.templates, 1001)
        snap = await g.server.services.characters.snapshot(g.user_id)
        assert [i.template_id for i in snap.items].count(card.templateId) == 1  # lida do banco, não da sessão

        assert codes(await take(g, 3)) == []  # uma carta por mapa
        snap = await g.server.services.characters.snapshot(g.user_id)
        assert [i.template_id for i in snap.items].count(card.templateId) == 1


async def test_grupo_de_1021_libera_o_chefe_e_fecha_a_masmorra(tmp_path: Path) -> None:
    async with logged_in(tmp_path, novice=25500) as g:
        await play_1011(g)
        await take(g, 2)
        g.client.send(5180, pb.CampaignReqMsg(paraInt1=1))  # quadro fechado: sem resposta
        assert await g.idle() == []
        g.client.send(5035, pb.LoginStateMsg(state=0))  # o cliente volta ao castelo (replay #1170, #1171)
        g.client.send(8747, pb.SimplePropertyMsg(param7=True))
        await g.idle()
        got = await enter(g)
        assert codes(got) == [125, 140, 21, 127, 130, 143, 3, 83]  # sem plot: o diálogo é só do 1011
        assert pb.RoomCreatedMsg.FromString(got[0].body).room.campaignId == 1021

        g.client.send(5125, pb.CampaignReqMsg(paraInt1=102104, paraBool1=True))  # baú sem 126 (replay #1475)
        chest = await g.idle()
        assert codes(chest) == [109, 111, 128, 83]
        assert pb.ChatChannelMsg.FromString(chest[1].body).encodeMsg == "Kazanılan:Altın 500"

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
        boss = await battle(g, 102109)
        assert codes(boss)[-len(END) :] == END
        assert (await characters.snapshot(g.user_id)).character.strategy == strategy + 72  # "Ruh" do chefe
        assert codes(await take(g, 1)) == CARD  # a carta do 1021 é outra, uma também


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


def _quests(packets: list[Packet]) -> dict[int, pb.QuestInfo]:
    """Último estado de cada missão nos 112 recebidos."""
    out: dict[int, pb.QuestInfo] = {}
    for p in packets:
        if p.code == 112:
            for q in pb.QuestUpdatedRspMsg.FromString(p.body).quest:
                out[q.templateId] = q
    return out


async def kurt_pilhas(g: Game) -> list[tuple[int, int]]:
    """(posição, quantidade) de cada pilha de Kurt Dişi no banco."""
    snap = await g.server.services.characters.snapshot(g.user_id)
    return [(i.pos, i.count) for i in snap.items if i.template_id == KURT_DIS]


async def kurt_dis(g: Game) -> int:
    return sum(n for _, n in await kurt_pilhas(g))


async def entrega(g: Game, template_id: int) -> list[Packet]:
    g.client.send(5014, pb.QuestFinishedReqMsg(templateId=template_id))
    got = await g.idle()
    assert [pb.QuestFinishedRspMsg.FromString(p.body).templateId for p in got if p.code == 52] == [template_id]
    return got


async def test_missoes_70_80_90_fecham_jogando_a_1001_do_comeco_ao_fim(tmp_path: Path) -> None:
    # (visto) replay: 70 (passar a campanha) fecha com o 137 do 1011; 80 (chefe 1011) com o 102109; 90 com 8
    # Kurt Dişi na bolsa (os lobos do 1021 deram 10). Entrega pelo 5014, como o oficial.
    async with logged_in(tmp_path, novice=25500) as g:
        _done(g, 60)  # pré da 70; 80 e 90 pedem a 70 concluída (PreQuestId), então entram depois da entrega
        g.client.send(5012, pb.QuestAddedMsg(questId=[70]))
        assert 70 in _quests(await g.until(112))
        characters = g.server.services.characters
        assert await kurt_dis(g) == 0

        await enter(g)
        for camp in WOLVES_1011[:-1]:
            await battle(g, camp)
        end = await battle(g, WOLVES_1011[-1])
        assert codes(end)[-len(END_COM_70) :] == END_COM_70  # o 112 da 70 entre o 135 e o 4165 (replay #1221-#1222)
        assert _quests(end)[70].condition_1 == 1 and not _quests(end)[70].isComplete
        await entrega(g, 70)
        g.client.send(5012, pb.QuestAddedMsg(questId=[80, 90]))
        assert {80, 90} <= set(_quests(await g.until(112)))

        # 1021: o drop de cada lobo sai antes do 128 (replay #1360, #1442, #1520, #1578)
        await take(g, 2)
        g.client.send(5180, pb.CampaignReqMsg(paraInt1=1))
        await g.idle()
        g.client.send(5035, pb.LoginStateMsg(state=0))
        g.client.send(8747, pb.SimplePropertyMsg(param7=True))
        await g.idle()
        await enter(g)
        totals, stacks = [], set()
        for camp in WOLVES_1021:
            got = await battle(g, camp)
            totals.append(await kurt_dis(g))
            assert len(await kurt_pilhas(g)) == 1  # uma pilha só, como o oficial (replay pos 6: 2, 4, 7, 10)
            moved = [m for p in got if p.code == 115 for m in pb.ItemMovedListMsg.FromString(p.body).moved]
            stacks |= {m.changePos for m in moved if m.HasField("item") and m.item.templateId == KURT_DIS}
            if camp == 102102:  # desvio: o oficial deixa o Şans Taşı num baú (4103 + pick-up 5129), aqui sai no 115
                assert {m.item.templateId for m in moved if m.HasField("item")} >= {KURT_DIS, SANS_TASI}
        assert totals == [2, 4, 7, 10]
        [(pos, count)] = await kurt_pilhas(g)
        assert count == 10 and stacks == {pos}  # os 115 reusam a posição da pilha

        boss = await battle(g, 102109)
        assert _quests(boss)[80].condition_1 == 1  # 26: o chefe 1011 ('Çene') morto
        await entrega(g, 80)

        strategy = (await characters.snapshot(g.user_id)).character.strategy
        [(pos, _)] = await kurt_pilhas(g)
        got = await entrega(g, 90)
        assert _quests(got)[90].isComplete
        assert await kurt_pilhas(g) == []  # a entrega tirou a pilha inteira
        removed = [m for p in got if p.code == 115 for m in pb.ItemMovedListMsg.FromString(p.body).moved]
        assert [m.changePos for m in removed if not m.HasField("item")] == [pos]  # 115 vazio na posição (replay #1609)
        ao_completar = [
            i
            for i, p in enumerate(got)
            if p.code == 112
            and any(q.templateId == 90 and q.isComplete for q in pb.QuestUpdatedRspMsg.FromString(p.body).quest)
        ]
        assert ao_completar and codes(got).index(115) < ao_completar[-1]  # o 115 sai antes do 112 (replay #1609-#1611)
        last = [p for p in got if p.code == 3][-1]
        assert pb.PlayerMsg.FromString(last.body).strategy == strategy + 1000  # Ruh da 90 no PlayerMsg (replay #1612)
        assert (await characters.snapshot(g.user_id)).character.strategy == strategy + 1000  # Ruh da 90

        done = {q.template_id for q in (await characters.snapshot(g.user_id)).quests if q.completed}
        assert {70, 80, 90} <= done  # gravado no banco


async def test_guia_depois_da_70_aprende_a_skill_e_avanca_o_novice(tmp_path: Path) -> None:
    # (visto) replay: 5185 (30111) e 5017 (25500) logo após a entrega da 70 (#1175-#1176). Respostas: 60 com
    # {30111, index 2, type 0} (#1254) e 1, o U_C_PLAYER_NOVICE vazio (#1257). O novice vinha de 24000 (5017 de #927).
    async with logged_in(tmp_path, novice=24000) as g:
        _done(g, 60)
        g.client.send(5012, pb.QuestAddedMsg(questId=[70]))
        await g.until(112)
        await play_1011(g)
        await entrega(g, 70)
        # (visto) replay #1202: herói no nível 7 com 30711 e 30811 aprendidas e 1 ponto de skill (30111 gasta o ponto)
        session = g.server.online.get(g.user_id)
        assert session is not None and session.snapshot is not None and session.snapshot.leader is not None
        session.snapshot.leader.grades, session.snapshot.leader.skill_script = 7, "30711,30811,"

        g.client.send(5185, pb.HeroAddPointReqMsg(skillTempId=30111, type=0))
        got = await g.idle()
        skill = pb.UpdatedSkillMsg.FromString(next(p.body for p in got if p.code == 60))
        assert (skill.templateId, skill.index, skill.type) == (30111, 2, 0)

        g.client.send(5017, pb.NoviceReqMsgMsg(noviceProcess=25500))
        got = await g.idle()
        assert codes(got)[-1] == 1 and got[-1].body == b""  # U_C_PLAYER_NOVICE vazio, depois do 3
        assert (await g.server.services.characters.snapshot(g.user_id)).character.novice_process == 25500
