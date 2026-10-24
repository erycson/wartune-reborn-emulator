"""Opcodes do mapa-múndi e dos sistemas vizinhos (cidade externa, gancho, passe, tesouro): todo código tem
handler, corpo vazio não derruba a sessão, e as respostas que o cliente espera (docs/cidade-externa.md)."""

from pathlib import Path

from tests.game.harness import Game, logged_in
from wartune_server.domain.models import PlayerSnapshot, TreasureMap
from wartune_server.game import arena as A
from wartune_server.game import handlers  # noqa: F401  (registra os handlers)
from wartune_server.game.router import router
from wartune_server.protocol.messages import wartune_pb2 as pb

CODES = (5004, 5160, 5161, 5176, 5181, 8254, 8293, 8488, 8525, 8636, 8637, 8699, 8744, 8745, 9506)


async def _subir(g: Game, grades: int) -> PlayerSnapshot:
    session = g.server.online.get(g.user_id)
    assert session is not None and session.snapshot is not None
    session.snapshot.character.grades = grades
    await g.server.services.characters.save(session.snapshot.character)
    return session.snapshot


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
        assert (state.leftWeay, state.isStartHangup, state.addWeay) == (50, False, 0)  # sem meditar: nada cobrado
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
        assert (state.userId, state.joinCount, state.rewardCount, list(state.templateIds)) == (
            g.user_id, 0, 0, [2190001, 2190002, 2190003, 2190004]
        )  # fmt: skip
        g.client.send(8745, pb.GuildMsg(param1=1))  # reforço de mapa de guilda: não há mapa, só registra
        assert await g.idle() == []


async def test_mapa_do_tesouro_exige_o_nivel_do_item(tmp_path: Path) -> None:
    async with logged_in(tmp_path, novice=19000) as g:
        snap = await _subir(g, 54)  # o mapa pede NeedGrades 55
        g.client.send(8744, pb.PlayerTreasureMsg(opType=1))
        got = await g.until(4633)
        assert [p.code for p in got] == [4633]  # recusado: só o estado
        assert pb.PlayerTreasureMsg.FromString(got[-1].body).joinCount == 0
        assert not any(i.template_id == 2190001 for i in snap.items)


async def test_mapa_do_tesouro_entrega_ate_o_limite_do_dia(tmp_path: Path) -> None:
    async with logged_in(tmp_path, novice=19000) as g:
        await _subir(g, 55)
        for _ in range(5):  # join_tremap_count = 5
            g.client.send(8744, pb.PlayerTreasureMsg(opType=1))
            got = await g.until(4633)
        assert pb.PlayerTreasureMsg.FromString(got[-1].body).joinCount == 5
        g.client.send(8744, pb.PlayerTreasureMsg(opType=1))  # sexto no dia: recusado, só o estado
        assert [p.code for p in await g.until(4633)] == [4633]
        saved = await g.server.services.characters.snapshot(g.user_id)  # a conta foi gravada junto com os itens
        assert saved.treasure[0].join_count == 5
        assert sum(i.template_id == 2190001 for i in saved.items) == 5


async def test_contagem_do_mapa_zera_no_dia_seguinte(tmp_path: Path) -> None:
    async with logged_in(tmp_path, novice=19000) as g:
        session = g.server.online.get(g.user_id)
        assert session is not None and session.snapshot is not None
        session.snapshot.character.grades = 55  # o mapa pede nível 55
        book = TreasureMap(g.user_id, day="2000-01-01", join_count=5)  # ontem já tinha dado os 5
        session.snapshot.treasure.append(book)
        await g.server.services.characters.save(book)
        g.client.send(8744, pb.PlayerTreasureMsg(opType=1))
        assert pb.PlayerTreasureMsg.FromString((await g.until(4633))[-1].body).joinCount == 1
        assert (book.day, book.join_count) == (A.today(g.server.services.clock.now()), 1)
