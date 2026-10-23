"""Masmorra Worg Lair (campanha 1001, mapas 1011 e 1021) com cliente falso: entrar, lutar, Pandora, baú, fim.

Ordem e textos da captura inglesa (``captures/tutorial_en.txt``); o conteúdo vem do banco (migração 0034).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

import wartune_server
from tests.game.harness import Game, logged_in
from tests.game.test_missoes_fazenda_pets_simbolos import _done
from tests.test_end_to_end import TEMPLATES
from wartune_server.domain.models import BagType, Item
from wartune_server.game import bag, buffs, drops
from wartune_server.game import battle as battle_mod
from wartune_server.game.campaign import DONE, CampaignMap
from wartune_server.game.handlers import campaign as handlers
from wartune_server.protocol import Packet
from wartune_server.protocol.messages import wartune_pb2 as pb

pytestmark = pytest.mark.skipif(not TEMPLATES.exists(), reason="precisa de data/templates")

SEED = Path(wartune_server.__file__).parent / "persistence/migrations/versions/0034_campanhas.json"
WOLVES_1011 = (101102, 101103, 101105, 101106, 101109)  # o 101109 fecha o grupo e o mapa
WOLVES_1021 = (102102, 102103, 102105, 102106)  # o 102106 traz o param4 que libera o chefe 102109
# (visto) inglesa #1096-#1107, sem o 20 do 5038. O 4152 e o 83 do fim são a devoção do leed 4: o personagem do teste
# não passou pela saída do tutorial, onde a inglesa ganhou o leed 4 do dia (#521)
END = [4382, 3, 137, 4151, 83, 135, 4165, 150, 150, 140, 4152, 83]
END_COM_70 = [4382, 3, 137, 4151, 83, 135, 112, 4165, 150, 150, 140, 4152, 83]  # com a 70: o 112 entre o 135 e o 4165
CARD = [115, 4476, 26, 83]  # resposta do 5122 (inglesa #1111-#1123, sem os 4484); o 134 vem no 5180
WORG_TOOTH, LUCK_STONE = 2100001, 2040101  # drops dos lobos do 1021


def content(campaign_id: int) -> dict[str, Any]:
    return json.loads(SEED.read_text(encoding="utf-8"))[str(campaign_id)]  # type: ignore[no-any-return]


class Sure:
    """``random`` dos handlers sem sorte: todo drop sai, o primeiro buff, o mínimo da coleta."""

    @staticmethod
    def random() -> float:
        return 0.0

    @staticmethod
    def choice(seq: list[int]) -> int:
        return seq[0]

    @staticmethod
    def randint(low: int, high: int) -> int:
        return low


def _undying(self: battle_mod.Battle, target: battle_mod.Unit, value: int) -> int:
    return min(value, max(0, target.hp - 1)) if target.side == battle_mod.PLAYER_SIDE else value


@pytest.fixture(autouse=True)
def fast_battles(monkeypatch: pytest.MonkeyPatch) -> None:
    """Lutas rápidas, sem sorte nos drops e sem derrota: estes testes são do fluxo da masmorra, e o personagem de
    teste é nível 1 sem tropa (na inglesa #893 ele chega aos lobos no nível 6 com duas pilhas de Lancers)."""
    monkeypatch.setattr(battle_mod, "FRAME_SECONDS", 0.001)
    monkeypatch.setattr(handlers, "random", Sure)
    monkeypatch.setattr(battle_mod.Battle, "_floor_hp", _undying)


def codes(packets: list[Packet]) -> list[int]:
    return [p.code for p in packets]


async def enter(g: Game, campaign_id: int = 1001) -> list[Packet]:
    g.client.send(5039, pb.CampaignReqMsg(paraInt1=1, paraInt2=campaign_id))  # inglesa #843: 08 01 10 e9 07
    return await g.idle()


async def back_to_map(g: Game) -> list[Packet]:
    g.client.send(5035, pb.LoginStateMsg(state=4))  # o cliente volta da cena da luta
    return await g.idle()


async def battle(g: Game, camp: int) -> list[Packet]:
    """Chegada ao nó, vitória, a volta ao mapa e tudo o que vem depois (4382 e o fim da etapa)."""
    g.client.send(5125, pb.CampaignReqMsg(paraInt1=camp, paraBool1=True))
    return await won(g)


async def won(g: Game) -> list[Packet]:
    got = await g.fight(pb.BattlePrepareMsg.FromString((await g.until(157))[-1].body))
    assert pb.BattleReportMsg.FromString(next(p.body for p in got if p.code == 4103)).battleResult == 1
    return got + await g.idle() + await back_to_map(g)


async def take(g: Game, index: int) -> list[Packet]:
    g.client.send(5122, pb.CampaignReqMsg(paraInt2=index))
    return await g.idle()


async def leave(g: Game) -> None:
    await take(g, 2)
    g.client.send(5180, pb.CampaignReqMsg(paraInt1=1))
    assert codes(await g.idle()) == [134]  # (visto) inglesa #1124 -> #1126
    g.client.send(5035, pb.LoginStateMsg(state=0))
    g.client.send(8747, pb.SimplePropertyMsg(param7=True))
    await g.idle()


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
        assert codes(got) == [125, 140, 21, 127, 130, 143, 138, 3, 83]  # inglesa #844-#853
        assert pb.RoomCreatedMsg.FromString(got[0].body).room.campaignId == 1011
        assert len(pb.CampaignNodeListMsg.FromString(got[3].body).node) == 10
        fog = pb.CampaignFogMsg.FromString(got[4].body)
        assert (fog.row, fog.col) == (24, 19)  # névoa da captura, não a de 'tudo visível'


async def test_campanha_que_nao_existe_nao_entra(tmp_path: Path) -> None:
    async with logged_in(tmp_path, novice=25500) as g:
        assert codes(await enter(g, 4242)) == []
        assert codes(await enter(g, 6001)) == []  # a pedreira entra pelo 8258


async def test_cada_etapa_gasta_20_de_estamina_e_sem_estamina_nao_entra(tmp_path: Path) -> None:
    async with logged_in(tmp_path, novice=25500) as g:
        characters = g.server.services.characters
        before = (await characters.snapshot(g.user_id)).character.weary
        got = await enter(g)
        assert pb.PlayerMsg.FromString(got[-2].body).weary == before - 20
        assert pb.ChatChannelMsg.FromString(got[-1].body).encodeMsg == "Entered [Worg Lair] and deducted 20 stamina."
        assert (await characters.snapshot(g.user_id)).character.weary == before - 20  # gravado

        session = g.server.online.get(g.user_id)
        assert session is not None and session.snapshot is not None
        session.snapshot.character.weary = 19
        session.campaign = None  # fora da masmorra, com 19 de estamina
        assert codes(await enter(g)) == []
        assert session.snapshot.character.weary == 19 and session.campaign is None


async def test_lobo_comeca_a_luta_na_chegada_e_o_4382_espera_a_volta(tmp_path: Path) -> None:
    async with logged_in(tmp_path, novice=25500) as g:
        await enter(g)
        g.client.send(5125, pb.CampaignReqMsg(paraInt1=101102, paraBool1=True))
        start = await g.until(157)
        assert codes(start) == [140, 131, 128, 157]
        prepare = pb.BattlePrepareMsg.FromString(start[-1].body)
        assert prepare.mapTempId == 1011
        got = await g.fight(prepare) + await g.idle()
        assert 4382 not in codes(got)  # (visto) inglesa #915 -> #920: só depois do 5035 state 4
        exp = next(p for p in got if p.code == 83)
        assert pb.ChatChannelMsg.FromString(exp.body).encodeMsg == "Received 35 EXP "
        node = pb.CampaignNodeUpdateMsg.FromString([p for p in got if p.code == 128][-1].body)
        assert (node.nodeId, node.nodeState) == (14053, DONE)  # nó do 101102 vira DONE
        back = await back_to_map(g)
        assert codes(back) == [4382]
        assert pb.FightOverMoiveMsg.FromString(back[0].body).gp == 35
        assert codes(await back_to_map(g)) == []  # um 4382 por luta


async def test_pandora_pede_confirmacao_e_da_buff_uma_vez(tmp_path: Path) -> None:
    async with logged_in(tmp_path, novice=25500) as g:
        await enter(g)
        g.client.send(5125, pb.CampaignReqMsg(paraInt1=101107, paraBool1=True))
        got = await g.idle()
        assert codes(got) == [29, 4126]  # inglesa #1428-#1429
        confirm = pb.CampaignConfirmMsg.FromString(got[0].body)
        assert confirm.nodeId == 101107 and "Pandora" in confirm.body  # o 29 da 102107, com o nó trocado
        stand = pb.StandPosMsg.FromString(got[1].body)
        assert (stand.posX, stand.posY) == (26, 26)  # nó (24, 24) + 2

        g.client.send(5033, pb.CampaignReqMsg(paraInt1=confirm.mapId, paraInt2=101107, paraBool1=False))
        assert await g.idle() == []  # "não"

        g.client.send(5033, pb.CampaignReqMsg(paraInt1=confirm.mapId, paraInt2=101107, paraBool1=True))
        got = await g.idle()
        assert codes(got) == [4165, 150, 150, 111, 128, 83]  # inglesa #1433-#1438
        assert pb.CampaignBufferMsg.FromString(got[0].body).bufferInfo[0].bufferTempId == 1301  # 1º do "1301|1701"
        texts = [pb.ChatChannelMsg.FromString(p.body).encodeMsg for p in (got[3], got[5])]
        assert texts == ["Received: Lvl. 1 PDEF Boost"] * 2  # CampaignBufferTemps.TemplateName

        g.client.send(5033, pb.CampaignReqMsg(paraInt1=confirm.mapId, paraInt2=101107, paraBool1=True))
        assert await g.idle() == []  # nó já DONE: sem segunda caixa


async def test_bau_de_ouro_da_500_uma_vez_e_grava(tmp_path: Path) -> None:
    async with logged_in(tmp_path, novice=25500) as g:
        await enter(g)
        characters = g.server.services.characters
        before = (await characters.snapshot(g.user_id)).character.gold
        g.client.send(5125, pb.CampaignReqMsg(paraInt1=101108, paraBool1=True))
        got = await g.idle()
        assert codes(got) == [109, 126, 128, 83]  # inglesa #945-#948
        assert pb.CampaignNotifyMsg.FromString(got[1].body).body == "Received: 500 Gold"
        assert (await characters.snapshot(g.user_id)).character.gold == before + 500

        g.client.send(5125, pb.CampaignReqMsg(paraInt1=101108, paraBool1=True))
        assert await g.idle() == []  # nó DONE: o ouro sai uma vez só
        assert (await characters.snapshot(g.user_id)).character.gold == before + 500

        # baú de bronze do 1011, nunca aberto na captura: (dedução) o do 102104, 500 sem aviso (#1295: 111 e 83)
        g.client.send(5125, pb.CampaignReqMsg(paraInt1=101104, paraBool1=True))
        assert codes(await g.idle()) == [109, 111, 128, 83]
        assert (await characters.snapshot(g.user_id)).character.gold == before + 1000


def test_chefe_so_aparece_com_o_grupo_caido() -> None:
    camp = CampaignMap.enter_dungeon(content(1001), 1021)
    assert camp.locked(102109)  # 102106 libera o chefe (param4 "102109,1") e o grupo está vivo
    assert not camp.locked(102107)  # a Pandora não depende de grupo
    for wolf in WOLVES_1021:
        camp.nodes[wolf]["state"] = DONE
    assert not camp.locked(102109)


async def test_pergaminho_de_exp_dobra_a_exp_do_fim_da_etapa(tmp_path: Path) -> None:
    """Lvl. 2 Bonus EXP Scroll (2030, grau 100): "Increases EXP received from instances by 100%"; o 137 leva 630 x 2 e o
    grau no propJoin (dedução)."""
    async with logged_in(tmp_path, novice=25500) as g:
        s = g.server.online.get(g.user_id)
        assert s is not None and s.snapshot is not None
        buffs.apply(s.snapshot, buffs.EXP_BOOST, 2013002, 100, 60, s.ctx.clock.now())
        end = await play_1011(g)
        report = pb.CampaignReportMsg.FromString(next(p.body for p in end if p.code == 137))
        assert (report.totalGp, report.propJoin) == (1260, 100)
        assert "Received 1,260 EXP " in [pb.ChatChannelMsg.FromString(p.body).encodeMsg for p in end if p.code == 83]


async def test_5122_so_vira_carta_depois_do_fim(tmp_path: Path) -> None:
    async with logged_in(tmp_path, novice=25500) as g:
        await enter(g)
        assert codes(await take(g, 2)) == []  # antes do 135 não há carta
        g.client.send(5180, pb.CampaignReqMsg(paraInt1=1))
        assert await g.idle() == []  # nem 134 no meio da etapa


async def test_mapa_1011_fecha_e_a_carta_do_5122_fica_gravada(tmp_path: Path) -> None:
    async with logged_in(tmp_path, novice=25500) as g:
        end = await play_1011(g)
        assert codes(end)[-len(END) :] == END  # sem 115/26: a carta espera o clique
        report = pb.CampaignReportMsg.FromString(next(p.body for p in end if p.code == 137))
        assert report.totalGp == 630 and report.failedCount == 0  # BaseGp 600 * 1,05
        assert report.woundValue > 0 and report.totalAppraisal == round((report.woundAppraisal + report.hurtAppraisal
                                                                         + report.failedAppraisal) / 3)  # fmt: skip
        rank = pb.RankListRspMsg.FromString(next(p.body for p in end if p.code == 4151))
        assert [(r.campaignId, r.rank) for r in rank.rankInfo] == [(1001, report.totalAppraisal)]
        exp = [pb.ChatChannelMsg.FromString(p.body).encodeMsg for p in end if p.code == 83][-2:]
        assert exp == ["Received 630 EXP ", "Your devotion level has increased to 10."]
        assert codes(await take(g, 5)) == []  # index fora das 5 cartas (0..4)

        got = await take(g, 2)
        assert codes(got) == CARD
        take_msg = pb.CampaignTakeCardsMsg.FromString(got[2].body)
        card = pb.ItemMovedListMsg.FromString(got[0].body).moved[0].item
        assert (take_msg.index, take_msg.templateId) == (2, card.templateId)
        assert card.templateId in drops.pool(g.server.services.templates, 1001)
        name = g.server.services.templates.get("ItemTempInfos", card.templateId)["TemplateName"]
        assert pb.ChatChannelMsg.FromString(got[3].body).encodeMsg == f"Received: {name} x1"
        snap = await g.server.services.characters.snapshot(g.user_id)
        assert [i.template_id for i in snap.items].count(card.templateId) == 1  # lida do banco, não da sessão

        assert codes(await take(g, 3)) == []  # uma carta por etapa
        snap = await g.server.services.characters.snapshot(g.user_id)
        assert [i.template_id for i in snap.items].count(card.templateId) == 1
        assert {e.key: e.value for e in snap.events}["campaign_stage:1001"] == 1  # o próximo 5039 leva ao 1021


async def test_grupo_de_1021_libera_o_chefe_e_fecha_a_masmorra(tmp_path: Path) -> None:
    async with logged_in(tmp_path, novice=25500) as g:
        await play_1011(g)
        await leave(g)
        got = await enter(g)
        assert codes(got) == [125, 140, 21, 127, 130, 143, 3, 83]  # sem plot: o diálogo é só do 1011
        assert pb.RoomCreatedMsg.FromString(got[0].body).room.campaignId == 1021

        g.client.send(5125, pb.CampaignReqMsg(paraInt1=102104, paraBool1=True))  # baú sem 126
        chest = await g.idle()
        assert codes(chest) == [109, 111, 128, 83]
        assert pb.ChatChannelMsg.FromString(chest[1].body).encodeMsg == "Received: 500 Gold"

        g.client.send(5125, pb.CampaignReqMsg(paraInt1=102109, paraBool1=True))
        assert await g.idle() == []  # chefe travado enquanto o grupo vive

        for camp in WOLVES_1021[:-1]:
            await battle(g, camp)
        last = await battle(g, WOLVES_1021[-1])
        # drop (83), aviso, DISAPPEARD, FLICKER, chefe novo; desvio: o oficial (#1408-#1422) solta antes do 128 do lobo
        # e manda o 128 do chefe depois do 4382 (docs/salas-campanha.md)
        assert codes(last)[-6:] == [83, 126, 143, 143, 128, 4382]
        movies = [pb.PlayerMovieMsg.FromString(p.body) for p in last if p.code == 143]
        assert [(m.movieType, m.targetId) for m in movies] == [("DISAPPEARD", 14074), ("FLICKER", 14073)]
        notice = next(p.body for p in last if p.code == 126)
        assert pb.CampaignNotifyMsg.FromString(notice).body == "Defeat all the worgs to remove the obstacle."

        characters = g.server.services.characters
        strategy = (await characters.snapshot(g.user_id)).character.strategy
        boss = await battle(g, 102109)
        assert codes(boss)[-len(END) + 2 :] == END[:-2]  # a devoção do leed 4 já saiu no fim do 1011
        assert (await characters.snapshot(g.user_id)).character.strategy == strategy + 88  # inglesa #1509
        assert codes(await take(g, 1)) == CARD  # a carta do 1021 é outra, uma também
        snap = await characters.snapshot(g.user_id)
        assert {e.key: e.value for e in snap.events}["campaign_stage:1001"] == 0  # (dedução) volta ao 1011


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


async def test_5038_manda_o_exercito_do_mapa_do_banco(tmp_path: Path) -> None:
    async with logged_in(tmp_path, novice=25500) as g:
        g.client.send(5038, pb.CampaignReqMsg(paraInt1=1021))
        army = pb.SystemArmyMsg.FromString((await g.until(20))[-1].body)
        assert (list(army.heroTemplated), list(army.soldierTemplated)) == ([1011], [2011])  # inglesa #1524


def _quests(packets: list[Packet]) -> dict[int, pb.QuestInfo]:
    """Último estado de cada missão nos 112 recebidos."""
    out: dict[int, pb.QuestInfo] = {}
    for p in packets:
        if p.code == 112:
            for q in pb.QuestUpdatedRspMsg.FromString(p.body).quest:
                out[q.templateId] = q
    return out


async def tooth_piles(g: Game) -> list[tuple[int, int]]:
    """(posição, quantidade) de cada pilha de Worg Tooth no banco."""
    snap = await g.server.services.characters.snapshot(g.user_id)
    return [(i.pos, i.count) for i in snap.items if i.template_id == WORG_TOOTH]


async def worg_teeth(g: Game) -> int:
    return sum(n for _, n in await tooth_piles(g))


async def entrega(g: Game, template_id: int) -> list[Packet]:
    g.client.send(5014, pb.QuestFinishedReqMsg(templateId=template_id))
    got = await g.idle()
    assert [pb.QuestFinishedRspMsg.FromString(p.body).templateId for p in got if p.code == 52] == [template_id]
    return got


async def test_missoes_70_80_90_fecham_jogando_a_1001_do_comeco_ao_fim(tmp_path: Path) -> None:
    # (visto) 70 (passar a campanha) fecha com o 137 do 1011 (inglesa #1103); 80 (chefe Wulfgar) com o 102109
    # (#1513); 90 com 8 Worg Tooth na bolsa (os lobos do 1021 deram 10). Entrega pelo 5014, como o oficial.
    async with logged_in(tmp_path, novice=25500) as g:
        _done(g, 60)  # pré da 70; 80 e 90 pedem a 70 concluída (PreQuestId), então entram depois da entrega
        g.client.send(5012, pb.QuestAddedMsg(questId=[70]))
        assert 70 in _quests(await g.until(112))
        characters = g.server.services.characters
        assert await worg_teeth(g) == 0

        await enter(g)
        for camp in WOLVES_1011[:-1]:
            await battle(g, camp)
        end = await battle(g, WOLVES_1011[-1])
        assert codes(end)[-len(END_COM_70) :] == END_COM_70
        assert _quests(end)[70].condition_1 == 1 and not _quests(end)[70].isComplete
        await entrega(g, 70)
        g.client.send(5012, pb.QuestAddedMsg(questId=[80, 90]))
        assert {80, 90} <= set(_quests(await g.until(112)))

        await leave(g)
        await enter(g)
        totals, stacks = [], set()
        for camp in WOLVES_1021:
            got = await battle(g, camp)
            totals.append(await worg_teeth(g))
            assert len(await tooth_piles(g)) == 1  # uma pilha só, como o oficial
            moved = [m for p in got if p.code == 115 for m in pb.ItemMovedListMsg.FromString(p.body).moved]
            stacks |= {m.changePos for m in moved if m.HasField("item") and m.item.templateId == WORG_TOOTH}
            if camp == 102102:  # Luck Stone (chance 0,5; aqui sem sorte, sai sempre): cai num baú (inglesa #2910)
                report = pb.BattleReportMsg.FromString(next(p.body for p in got if p.code == 4103))
                assert [(i.templateId, i.count) for i in report.baseItem] == [(LUCK_STONE, 1)] and report.signId
                assert LUCK_STONE not in {m.item.templateId for m in moved if m.HasField("item")}
                g.client.send(5129, pb.CampaignReqMsg(paraString1=report.signId))
                chest = await g.idle()
                assert codes(chest) == [115, 4476, 111, 83]  # inglesa #2924-#2939
                assert pb.ChatChannelMsg.FromString(chest[3].body).encodeMsg == "Received: Lvl. 1 Luck Stone x1"
                g.client.send(5129, pb.CampaignReqMsg(paraString1=report.signId))
                assert await g.idle() == []  # já pego
        assert totals == [2, 4, 7, 10]
        [(pos, count)] = await tooth_piles(g)
        assert count == 10 and stacks == {pos}  # os 115 reusam a posição da pilha

        boss = await battle(g, 102109)
        assert _quests(boss)[80].condition_1 == 1  # 26: o chefe 1011 (Wulfgar) morto
        await entrega(g, 80)

        strategy = (await characters.snapshot(g.user_id)).character.strategy
        [(pos, _)] = await tooth_piles(g)
        got = await entrega(g, 90)
        assert _quests(got)[90].isComplete
        assert await tooth_piles(g) == []  # a entrega tirou a pilha inteira
        removed = [m for p in got if p.code == 115 for m in pb.ItemMovedListMsg.FromString(p.body).moved]
        assert [m.changePos for m in removed if not m.HasField("item")] == [pos]
        last = [p for p in got if p.code == 3][-1]
        assert pb.PlayerMsg.FromString(last.body).strategy == strategy + 1000  # Daru da 90 no PlayerMsg
        assert (await characters.snapshot(g.user_id)).character.strategy == strategy + 1000

        done = {q.template_id for q in (await characters.snapshot(g.user_id)).quests if q.completed}
        assert {70, 80, 90} <= done  # gravado no banco


async def test_guia_depois_da_70_aprende_a_skill_e_avanca_o_novice(tmp_path: Path) -> None:
    # (visto) inglesa: 5185 (30111) e 5017 (25500) logo após a entrega da 70 (#1141, #1144). Respostas: 60 com
    # {30111, index 2, type 0} (#1143) e 1, o U_C_PLAYER_NOVICE vazio (#1146). O novice vinha de 24000 (5017 de #875).
    async with logged_in(tmp_path, novice=24000) as g:
        _done(g, 60)
        g.client.send(5012, pb.QuestAddedMsg(questId=[70]))
        await g.until(112)
        await play_1011(g)
        await entrega(g, 70)
        # (visto, só turco) replay #1202: herói no nível 7 com 30711 e 30811 aprendidas e 1 ponto de skill (30111 gasta o ponto)
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


async def test_bau_da_luta_pega_um_item_ou_volta_com_a_mochila_cheia(tmp_path: Path) -> None:
    async with logged_in(tmp_path, novice=25500) as g:
        s = g.server.online.get(g.user_id)
        assert s is not None and s.snapshot is not None
        s.campaign = CampaignMap(map_id=1011, nodes={}, pos=(0, 0))
        s.campaign.fallen["1"] = [(LUCK_STONE, 1), (1080011, 1)]
        g.client.send(5129, pb.CampaignReqMsg(paraString1="1", paraInt1=1080011))  # BattleFallGoodsView: um item
        got = await g.idle()
        assert codes(got) == [115, 4476, 111, 83]
        assert pb.ItemMovedListMsg.FromString(got[0].body).moved[0].item.templateId == 1080011
        assert s.campaign.fallen == {"1": [(LUCK_STONE, 1)]}

        snap = s.snapshot
        cid = snap.character.id or 0
        snap.items.extend(Item(cid, 1080011, pos=p) for p in range(bag.BAG_BASE) if not bag.at(snap, BagType.BAG, 0, p))
        g.client.send(5129, pb.CampaignReqMsg(paraString1="1"))
        got = await g.idle()
        assert codes(got) == [4268]  # __resetFallHandler: o baú volta com o que tem
        fail = pb.BattleReportMsg.FromString(got[0].body)
        assert (fail.signId, [(i.templateId, i.count) for i in fail.baseItem]) == ("1", [(LUCK_STONE, 1)])
        assert s.campaign.fallen == {"1": [(LUCK_STONE, 1)]}
