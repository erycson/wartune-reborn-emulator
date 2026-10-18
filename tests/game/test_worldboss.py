from datetime import UTC, datetime
from pathlib import Path

from tests.game.harness import logged_in
from wartune_server.game import worldboss
from wartune_server.game.router import router
from wartune_server.protocol.messages import wartune_pb2 as pb
from wartune_server.services.clock import FakeClock
from wartune_server.templates.repository import GameTemplates

WORLD_BOSS_OPCODES = (8258, 8259, 8264, 8271, 8470)
ALERT = 111
BEFORE_OPEN = datetime(2026, 5, 21, 9, 20, tzinfo=UTC)  # 12:20 em UTC+3: 5001 aberto (11:35-12:35), 5003 ainda não
OPEN_5001 = datetime(2026, 5, 21, 8, 40, tzinfo=UTC)  # 11:40 em UTC+3: 5001 aberto (abre 11:35 no inglês)


def _states(msg: pb.WorldBossStateMsg) -> list[tuple[int, int]]:
    return [(i.campaignId, i.state) for i in msg.worldBossInfo]


def test_window_uses_utc_plus_3_and_edges() -> None:
    templates = GameTemplates(
        {
            "Campaigns": [
                {"CampaignId": "5001", "Types": "1", "OpenTime": "11:00", "StopTime": "12:00", "MinLevel": "20"},
                {"CampaignId": "5003", "Types": "1", "OpenTime": "21:35", "StopTime": "22:35", "MinLevel": "20"},
                {"CampaignId": "4602", "Types": "16", "OpenTime": "21:35", "StopTime": "22:35", "MinLevel": "20"},
            ]
        }
    )
    # captura (replay idx 78 -> 102): 5001=2 e 5003=1
    assert _states(worldboss.states_msg(templates, BEFORE_OPEN)) == [(5001, 2), (5003, 1)]
    # captura login.json #120, 20:06 em UTC+3: o mesmo 5001=2 e 5003=1
    assert _states(worldboss.states_msg(templates, datetime(2026, 5, 21, 17, 6, tzinfo=UTC))) == [(5001, 2), (5003, 1)]
    row = worldboss.boss(templates, 5001)
    assert row is not None
    assert worldboss.state(row, datetime(2026, 5, 21, 8, 0, tzinfo=UTC)) == worldboss.OPEN  # 11:00 em UTC+3
    assert worldboss.state(row, datetime(2026, 5, 21, 7, 59, tzinfo=UTC)) == worldboss.BEFORE
    assert worldboss.state(row, datetime(2026, 5, 21, 8, 59, tzinfo=UTC)) == worldboss.OPEN  # 11:59
    assert worldboss.state(row, datetime(2026, 5, 21, 9, 0, tzinfo=UTC)) == worldboss.CLOSED  # 12:00
    assert worldboss.boss(templates, 4602) is None  # Types 16 não é chefe do mundo


async def test_agenda_e_recusas_com_o_relogio_da_captura(tmp_path: Path) -> None:
    async with logged_in(tmp_path, novice=19000, clock=FakeClock(BEFORE_OPEN)) as g:
        c = g.client
        c.send(8271)
        [state] = [pb.WorldBossStateMsg.FromString(p.body) for p in await g.idle() if p.code == 4182]
        assert _states(state) == [(5001, 0), (5003, 1)]  # 5001 já abriu às 11:35 no inglês (fecha 12:35)

        c.send(8258, pb.WorldBossMsg(param1=5003))  # fora da janela: aviso, sem 125
        c.send(8258, pb.WorldBossMsg(param1=4602))  # não é chefe do mundo
        assert [p.code for p in await g.idle()] == [ALERT, ALERT]

        session = g.server.online.get(g.user_id)
        assert session is not None and session.snapshot is not None
        ch = session.snapshot.character
        ch.point, ch.gift_token = 50, 50
        c.send(8264, pb.PayTypeMsg(payType=0))  # reviver: sem morte no chefe, nada cobrado
        c.send(8470, pb.WorldBossBufferMsg(op=2, type=2))  # buff: sem mapa do chefe, nada cobrado
        assert [p.code for p in await g.idle()] == [ALERT, ALERT]
        assert (ch.point, ch.gift_token) == (50, 50)


async def test_entrada_aberta_sem_mapa_recusa_com_aviso(tmp_path: Path) -> None:
    async with logged_in(tmp_path, novice=19000, clock=FakeClock(OPEN_5001)) as g:
        c = g.client
        c.send(8258, pb.WorldBossMsg(param1=5001))  # nível 1 < 20
        assert [p.code for p in await g.idle()] == [ALERT]

        session = g.server.online.get(g.user_id)
        assert session is not None and session.snapshot is not None
        session.snapshot.character.grades = 20
        c.send(8258, pb.WorldBossMsg(param1=5001))  # aberto e nível ok: só falta o mapa
        assert [p.code for p in await g.idle()] == [ALERT]


async def test_campanha_de_mina_nao_e_chefe_e_diz_indisponivel(tmp_path: Path) -> None:
    """O botão ir de uma missão de coleta (NeedFightId 6001, Maden Ocağı, Types 2) manda 8258 com essa campanha
    (cliente: TaskFrameII.as:707-708). Não é chefe e a entrada não existe aqui: aviso de indisponível, sem
    cobrar nada, não o "inválido" de id que não existe."""
    async with logged_in(tmp_path, novice=19000, clock=FakeClock(OPEN_5001)) as g:
        g.client.send(8258, pb.WorldBossMsg(param1=6001))
        [alert] = await g.idle()
        assert alert.code == ALERT
        assert pb.ChatChannelMsg.FromString(alert.body).encodeMsg == "Bu işlem şu an kullanılamıyor."


async def test_corpo_vazio_nao_derruba_a_sessao(tmp_path: Path) -> None:
    async with logged_in(tmp_path, novice=19000, clock=FakeClock(BEFORE_OPEN)) as g:
        c = g.client
        for code in (8258, 8259, 8264, 8470):
            c.send(code)  # corpo vazio: 8258 recusa (id 0), 8259 não tem resposta
        c.send(8271)
        assert [p.code for p in await g.idle()] == [ALERT, ALERT, ALERT, 4182]


def test_todo_opcode_da_lista_tem_handler() -> None:
    for code in WORLD_BOSS_OPCODES:
        assert router.get(code) is not None, code


def test_fuso_do_jogo_da_configuracao() -> None:
    """WARTUNE_GAME_TIMEZONE: deslocamento fixo ou nome IANA (com horário de verão, via tzdata)."""
    from datetime import timedelta

    from wartune_server.game import worldboss as wb

    assert wb.parse_timezone("+03:00").utcoffset(None) == timedelta(hours=3)
    assert wb.parse_timezone("UTC-7").utcoffset(None) == timedelta(hours=-7)
    pacific = wb.parse_timezone("America/Los_Angeles")
    assert datetime(2026, 7, 1, tzinfo=pacific).utcoffset() == timedelta(hours=-7)  # PDT
    assert datetime(2026, 12, 1, tzinfo=pacific).utcoffset() == timedelta(hours=-8)  # PST
