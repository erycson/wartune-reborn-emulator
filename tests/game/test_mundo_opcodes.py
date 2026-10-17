"""Opcodes do mapa-múndi e dos sistemas vizinhos (cidade externa, gancho, passe, tesouro): todo código tem
handler, corpo vazio não derruba a sessão, e as respostas que o cliente espera (docs/cidade-externa.md)."""

from pathlib import Path

from tests.game.harness import logged_in
from wartune_server.game import handlers  # noqa: F401  (registra os handlers)
from wartune_server.game.router import router
from wartune_server.protocol.messages import wartune_pb2 as pb

CODES = (5004, 5160, 5161, 5176, 5181, 8254, 8293, 8488, 8525, 8636, 8637, 8699, 8744, 8745, 9506)


def test_every_code_has_a_handler() -> None:
    assert [c for c in CODES if router.get(c) is None] == []


async def test_empty_bodies_do_not_kill_the_session(tmp_path: Path) -> None:
    async with logged_in(tmp_path, novice=19000) as g:
        for code in CODES:
            g.client.send(code)
        g.client.send(20008)
        await g.until(4234)


async def test_gancho_ressincroniza_sem_cobrar(tmp_path: Path) -> None:
    async with logged_in(tmp_path, novice=19000) as g:
        g.client.send(8293, pb.PayTypeMsg(payType=0))
        got = await g.until(4200)
        state = pb.HangupInfoMsg.FromString(got[-1].body)
        assert (state.leftWeay, state.isStartHangup, state.addWeay) == (0, False, 0)
        g.client.send(8525, pb.HangupAttackMsg(op=1, attackId=g.user_id, defenceId=99))  # convite sem batalha
        assert await g.idle() == []


async def test_passe_responde_a_area_atual_e_recusa_a_recompensa(tmp_path: Path) -> None:
    async with logged_in(tmp_path, novice=19000) as g:
        g.client.send(8636)
        state = pb.SinglePassMsg.FromString((await g.until(4552))[-1].body)
        assert (state.userId, state.area, state.maxIndex) == (g.user_id, 1, 0)
        g.client.send(8637)  # sem as fases da área concluídas: volta a 4552 atual
        assert pb.SinglePassMsg.FromString((await g.until(4552))[-1].body).area == 1


async def test_mapa_do_tesouro_responde_o_estado(tmp_path: Path) -> None:
    async with logged_in(tmp_path, novice=19000) as g:
        g.client.send(8744, pb.PlayerTreasureMsg(opType=6))
        state = pb.PlayerTreasureMsg.FromString((await g.until(4633))[-1].body)
        assert (state.userId, state.joinCount, state.rewardCount, list(state.templateIds)) == (g.user_id, 0, 0, [])
        g.client.send(8745, pb.GuildMsg(param1=1))  # reforço de mapa de guilda: não há mapa, só registra
        assert await g.idle() == []
