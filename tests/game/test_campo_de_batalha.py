"""Campo de batalha (4005/4007) e a mina (30000): um teste por pedido (8332, 5125/5032/5033, 8337, 8338, 8599, fim,
8633, 4185 e a janela do 4248). Horários em UTC (o fuso do jogo nos testes é UTC).
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

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
        assert _body(got, 4252, pb.WarFightInfoMsg).teamId == bf.TEAM
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


async def test_coleta_e_entrega_do_minerio_no_campo(tmp_path: Path) -> None:
    async with logged_in(tmp_path, novice=30001, clock=FakeClock(IN_4007)) as g:
        await _at_field(g, 4007)
        g.client.send(5125, pb.CampaignReqMsg(paraInt1=4007006, paraBool1=True))  # nó de coleta (superior)
        assert 143 in _codes(await g.idle())
        g.client.send(5032, pb.CallBackReqMsg(mapId=4007, nodeId=4007006, cmd=2))
        got = await g.idle()
        assert _codes(got).count(4175) == 1 and _texts(got) == [warfield.ENTERED_TEXT]
        g.client.send(5125, pb.CampaignReqMsg(paraInt1=4007012, paraBool1=True))  # entrega
        assert _body(await g.idle(), 29, pb.CampaignConfirmMsg).body == warfield.DELIVER_BODY
        g.client.send(5033, pb.CampaignReqMsg(paraInt1=4007, paraInt2=4007012, paraBool1=True))
        got = await g.idle()
        assert bf.turn_in_text("superior", 30, 3, 3) in _texts(got)
        assert _body(got, 4252, pb.WarFightInfoMsg).score == 30
        s = g.server.online.get(g.user_id)
        assert s is not None and s.campaign is not None and s.campaign.warfield == 4007


async def test_8337_lista_quem_esta_no_campo(tmp_path: Path) -> None:
    async with logged_in(tmp_path, novice=30001, clock=FakeClock(IN_4007)) as g:
        await _at_field(g, 4007)
        g.client.send(8337)
        order = _body(await g.until(4255), 4255, pb.WarReportListMsg)
        assert [(i.userId, i.teamId, i.score) for i in order.info] == [(g.user_id, bf.TEAM, 0)]


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
        field.mark(g.user_id).score = 30
        await warfield.settle(s.ctx, field)  # o relógio chama isto depois do StopTime
        got = await g.idle()
        assert warfield.END_TEXT in _texts(got, 83)
        assert bf.win_text() in _texts(got, 83)
        assert _body(got, 4254, pb.WarReportListMsg).oneTeamId == bf.TEAM
        assert 22 in _codes(got) and s.campaign is None


async def test_8633_mina_com_carrinho_e_coleta(tmp_path: Path) -> None:
    async with logged_in(tmp_path, novice=30001, clock=FakeClock(IN_MINE)) as g:
        s = g.server.online.get(g.user_id)
        assert s is not None and s.snapshot is not None
        s.snapshot.character.grades = 30
        g.client.send(8633)
        got = await g.idle()
        assert {125, 140, 21, 127, 4548} <= set(_codes(got))
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
