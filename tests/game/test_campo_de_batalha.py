"""Campo de batalha (4005/4007) e a mina (30000): um teste por pedido (8332, 5125/5032/5033, 8337, 8338, 8599, fim,
8633, 4185 e a janela do 4248). Horários em UTC (o fuso do jogo nos testes é UTC).
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from tests.game.harness import logged_in
from wartune_server.game import battlefield as bf
from wartune_server.game.handlers import warfield
from wartune_server.protocol.messages import wartune_pb2 as pb
from wartune_server.services.clock import FakeClock

IN_4005 = datetime(2026, 10, 27, 15, 10, tzinfo=UTC)  # 4005 abre 15:00 e fecha 15:25 (template)
IN_4007 = datetime(2026, 10, 27, 17, 10, tzinfo=UTC)  # 4007 abre 17:00 e fecha 17:25
IN_MINE = datetime(2026, 10, 27, 19, 45, tzinfo=UTC)  # carrinho: 19:30 a 20:00 (texto da mina)
BEFORE_4005 = datetime(2026, 10, 27, 14, 0, tzinfo=UTC)


def _codes(got: list) -> list[int]:
    return [p.code for p in got]


def _body(got: list, code: int, cls: type) -> object:
    return cls.FromString(next(p.body for p in got if p.code == code))


def _texts(got: list, code: int = 111) -> list[str]:
    return [pb.ChatChannelMsg.FromString(p.body).encodeMsg for p in got if p.code == code]


async def _at_field(g, campaign: int, grades: int = 35) -> None:
    s = g.server.online.get(g.user_id)
    assert s is not None and s.snapshot is not None
    s.snapshot.character.grades = grades
    g.client.send(8332, pb.WorldBossMsg(param1=campaign))
    await g.idle()


async def test_8332_entra_no_campo_na_janela_com_o_4248_aberto(tmp_path: Path) -> None:
    async with logged_in(tmp_path, novice=30001, clock=FakeClock(IN_4005)) as g:
        s = g.server.online.get(g.user_id)
        assert s is not None and s.snapshot is not None
        s.snapshot.character.grades = 35
        g.client.send(8332, pb.WorldBossMsg(param1=4005))
        got = await g.idle()
        assert {125, 140, 21, 127, 4252, 150} <= set(_codes(got))
        room = _body(got, 125, pb.RoomCreatedMsg)
        assert room.room.campaignId == 4005 and room.isCross is True
        assert s.ctx is not None
        assert _body(got, 4252, pb.WarFightInfoMsg).teamId == s.ctx.warfields.fields[4005].mark(g.user_id).team
        assert s.campaign is not None and s.campaign.warfield == 4005
        # o 4248 do login (o clock de 20008 manda de novo) mostra 4005 aberto
        assert dict(warfield._states_tuple(s.ctx.templates, IN_4005))[4005] == 0


async def test_8332_fora_da_janela_ou_do_nivel_nao_responde(tmp_path: Path) -> None:
    async with logged_in(tmp_path, novice=30001, clock=FakeClock(BEFORE_4005)) as g:
        s = g.server.online.get(g.user_id)
        assert s is not None and s.snapshot is not None
        s.snapshot.character.grades = 35
        g.client.send(8332, pb.WorldBossMsg(param1=4005))  # 14:00, antes de abrir
        assert await g.idle() == []
        assert s.campaign is None


async def test_coleta_e_entrega_do_minerio_no_campo(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(bf.random, "choice", lambda sides: sides[-1])  # o lado sorteado: 2, dono dos nós abaixo
    async with logged_in(tmp_path, novice=30001, clock=FakeClock(IN_4007)) as g:
        await _at_field(g, 4007)
        g.client.send(5125, pb.CampaignReqMsg(paraInt1=4007006, paraBool1=True))  # nó de coleta (superior)
        assert 143 in _codes(await g.idle())
        g.client.send(5032, pb.CallBackReqMsg(mapId=4007, nodeId=4007006, cmd=2))
        got = await g.idle()
        assert _codes(got).count(4175) == 1 and _texts(got) == [warfield.ENTERED_TEXT]
        s = g.server.online.get(g.user_id)
        assert s is not None and s.ctx is not None
        s.ctx.warfields.fields[4007].mark(g.user_id).carry = "superior"  # a qualidade é sorteada na coleta
        g.client.send(5125, pb.CampaignReqMsg(paraInt1=4007012, paraBool1=True))  # entrega
        assert _body(await g.idle(), 29, pb.CampaignConfirmMsg).body == warfield.DELIVER_BODY
        g.client.send(5033, pb.CampaignReqMsg(paraInt1=4007, paraInt2=4007012, paraBool1=True))
        got = await g.idle()
        assert bf.turn_in_text("superior", 30, 3, 3) in _texts(got)
        assert _body(got, 4252, pb.WarFightInfoMsg).score == bf.START_SCORE + 30
        assert _body(got, 4252, pb.WarFightInfoMsg).twoScore == 30  # o lado soma a entrega
        assert 4471 in _codes(got)  # a honra do dia
        assert s.campaign is not None and s.campaign.warfield == 4007


async def test_8337_lista_quem_esta_no_campo(tmp_path: Path) -> None:
    async with logged_in(tmp_path, novice=30001, clock=FakeClock(IN_4007)) as g:
        await _at_field(g, 4007)
        g.client.send(8337)
        order = _body(await g.until(4255), 4255, pb.WarReportListMsg)
        s = g.server.online.get(g.user_id)
        assert s is not None and s.ctx is not None
        team = s.ctx.warfields.fields[4007].mark(g.user_id).team
        assert [(i.userId, i.teamId, i.score) for i in order.info] == [(g.user_id, team, bf.START_SCORE)]


async def test_8338_restaura_vida_so_dentro_do_campo(tmp_path: Path) -> None:
    async with logged_in(tmp_path, novice=30001, clock=FakeClock(IN_4007)) as g:
        g.client.send(8338)
        assert await g.idle() == []  # fora do campo: nada
        await _at_field(g, 4007)
        g.client.send(8338)
        assert _texts(await g.idle()) == [warfield.FULL_HP]


async def test_8599_entradas_do_campo_aberto(tmp_path: Path) -> None:
    async with logged_in(tmp_path, novice=30001, clock=FakeClock(IN_4005)) as g:
        g.client.send(8599, pb.CampaignReqMsg(paraInt1=4005))
        got = await g.idle()
        assert _body(got, 4493, pb.CampaignReqMsg).paraBool1 is False


async def test_fim_da_partida_com_o_premio_e_a_saida(tmp_path: Path) -> None:
    async with logged_in(tmp_path, novice=30001, clock=FakeClock(IN_4005)) as g:
        await _at_field(g, 4005)
        s = g.server.online.get(g.user_id)
        assert s is not None and s.ctx is not None
        field = s.ctx.warfields.fields[4005]
        team = field.mark(g.user_id).team
        field.gain(team, 30)
        await warfield.settle(s.ctx, field)  # o relógio chama isto depois do StopTime
        got = await g.idle()
        assert warfield.END_TEXT in _texts(got, 83)
        assert bf.win_text() in _texts(got, 83)
        assert _body(got, 4254, pb.WarReportListMsg).oneTeamId == team
        assert 22 in _codes(got) and s.campaign is None


async def test_8633_mina_com_carrinho_e_coleta(tmp_path: Path) -> None:
    async with logged_in(tmp_path, novice=30001, clock=FakeClock(IN_MINE)) as g:
        s = g.server.online.get(g.user_id)
        assert s is not None and s.snapshot is not None
        s.snapshot.character.grades = 30
        g.client.send(8633)
        got = await g.idle()
        assert {125, 140, 21, 127, 4548} <= set(_codes(got))
        tram = _body(got, 4548, pb.TramcarInfoMsg)  # 183522 #6036: o que falta até as 20:00, count 2
        assert (tram.activeTime, tram.count, tram.multiple) == (15 * 60, 2, 2)
        enter = _body(got, 21, pb.RoomEnterMsg).player[0]  # 183522 #6034
        assert (enter.curPosX, enter.curPosY) == bf.START == (167, 183)
        g.client.send(5125, pb.CampaignReqMsg(paraInt1=3000003, paraBool1=True))  # carrinho
        assert _body(await g.idle(), 29, pb.CampaignConfirmMsg).mapId == bf.MINE
        g.client.send(5033, pb.CampaignReqMsg(paraInt1=65, paraInt2=3000003, paraBool1=True))
        assert _texts(await g.idle()) == [warfield.CART_GOT]
        g.client.send(5033, pb.CampaignReqMsg(paraInt1=65, paraInt2=3000003, paraBool1=True))
        assert _texts(await g.idle()) == [warfield.CART_HAS]
        g.client.send(5125, pb.CampaignReqMsg(paraInt1=3000006, paraBool1=True))  # coleta
        assert 143 in _codes(await g.idle())
        g.client.send(5032, pb.CallBackReqMsg(mapId=bf.MINE, nodeId=3000006, cmd=2))
        assert _texts(await g.idle()) == ["Collection complete. (4 / 5) collections remaining."]


async def test_4185_leva_o_caminho_a_quem_esta_no_mesmo_mapa(tmp_path: Path) -> None:
    async with logged_in(tmp_path, novice=30001, clock=FakeClock(IN_4005)) as g:
        await _at_field(g, 4005)
        other = await g.join("outro")
        await _at_field(other, 4005)
        move = pb.PosMoveMsg(mapId=4005, armyId=g.user_id)
        move.routes.add(x=200, y=400)
        g.client.send(5124, move)
        got = await other.idle()
        sent = [pb.PosMoveMsg.FromString(p.body) for p in got if p.code == 4185]
        assert sent and sent[0].armyId == g.user_id and sent[0].serverName


def test_pvp_perde_15_por_cento_e_ganha_20_mais_1_a_cada_20() -> None:
    # (visto 152321) 100->15/25, 115->18/25, 127->20/26; 30->21 e 72->23 de ganho
    assert [bf.pvp_loss(n) for n in (100, 115, 127, 110)] == [15, 18, 20, 17]
    assert [bf.pvp_gain(n) for n in (100, 115, 127, 30, 72)] == [25, 25, 26, 21, 23]


def test_4002_tem_guardioes_vivos_do_time_2_e_o_4005_nao() -> None:
    alive = {n % 1000 for n, node in bf.field_nodes(4002).items() if node["masterType"] == 42 and node["state"] == 1}
    assert alive == {13, 14, 15, 16, 17, 18}
    assert not [n for n in bf.field_nodes(4005).values() if n["masterType"] == 42 and n["state"] == 1]


def test_lados_e_vencedor_pelos_pontos_do_lado() -> None:
    field = bf.Field(4005, IN_4005)
    first = field.mark(1).team
    assert field.mark(2).team == 3 - first  # o segundo vai ao lado com menos gente
    assert {bf.Field(4005, IN_4005).mark(1).team for _ in range(64)} == {1, 2}  # empatados: sorteio
    assert field.mark(1).score == bf.START_SCORE and field.score(2) == 0  # entrar não soma ao lado
    assert field.winner() is None  # empate: sem vencedor
    field.gain(1, 30)
    assert field.winner() == 1


def test_frases_de_sequencia_onda_de_renascer_e_posicao_no_caminho() -> None:
    table = [[3, "spree"], [4, "dominating"], [5, "unstoppable"], [7, "god"], [8, "reaper"]]
    assert [bf.streak_text(n, table) for n in (2, 3, 6, 9)] == [
        None,
        bf.STREAK_TEXTS["spree"],
        bf.STREAK_TEXTS["unstoppable"],
        bf.STREAK_TEXTS["reaper"],
    ]
    assert bf.respawn_ms(IN_4005, IN_4005 + timedelta(seconds=65), 30) == 25000
    path = ((10, 10), (11, 10), (12, 10))
    assert bf.position_at(path, 0.15, 10) == (11, 10) and bf.position_at(path, 9, 10) == (12, 10)


def test_minerio_uniforme_e_base_de_cada_lado() -> None:
    from wartune_server.game import taxas

    assert taxas.DEFAULTS["field_ore_weights"] == {"superior": 1, "normal": 1, "inferior": 1}
    assert bf.in_base(1, bf.CAMP[1]) and bf.in_base(2, bf.CAMP[2])
    assert not bf.in_base(1, (100, 75)) and not bf.in_base(2, (100, 75))


async def test_base_inimiga_fechada_e_oficial_inimigo_luta(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(bf.random, "choice", lambda sides: sides[-1])  # lado 2
    async with logged_in(tmp_path, novice=30001, clock=FakeClock(IN_4007)) as g:
        await _at_field(g, 4007)
        g.client.send(5125, pb.CampaignReqMsg(paraInt1=4007124, paraBool1=True))  # entrada da base do time 1
        assert _texts(await g.idle()) == [warfield.ENEMY_BASE]
        g.client.send(5125, pb.CampaignReqMsg(paraInt1=4007011, paraBool1=True))  # oficial do time 1
        got = await g.idle()
        assert 4105 not in _codes(got) and 157 in _codes(got)
        assert _body(got, 128, pb.CampaignNodeUpdateMsg).nodeState == warfield.FIGHTING_NODE


async def test_morto_nao_sai_da_base_ate_a_onda(tmp_path: Path) -> None:
    async with logged_in(tmp_path, novice=30001, clock=FakeClock(IN_4005)) as g:
        await _at_field(g, 4005)
        s = g.server.online.get(g.user_id)
        assert s is not None and s.ctx is not None and s.campaign is not None
        mark = s.ctx.warfields.fields[4005].mark(g.user_id)
        mark.dead = True
        cx, cy = bf.CAMP[mark.team]
        step = 1 if mark.team == 2 else -1  # para fora da base
        move = pb.PosMoveMsg(mapId=4005, armyId=g.user_id)
        for i in range(60):
            move.routes.add(x=(cx + step * i) * bf.TILE, y=cy * bf.TILE)
        g.client.send(5124, move)
        got = await g.idle()
        back = _body(got, 4104, pb.ArmyPosUpdatedMsg)
        assert bf.in_base(mark.team, (back.curPosX, back.curPosY))
        assert not bf.in_base(mark.team, (back.curPosX + step, back.curPosY))
        assert bf.in_base(mark.team, s.campaign.pos)
