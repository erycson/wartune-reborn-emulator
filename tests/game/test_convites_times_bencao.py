"""Os 10 opcodes sem corpo do lote (times, recusas, gancho, PvP, bênção do seminário, transporte).

Registro, corpo vazio e os fluxos com dois ou três jogadores (``g.join``). Regras em docs/salas-campanha.md,
docs/cidade-externa.md, docs/castelo.md, docs/pvp.md e docs/boss-eventos.md.
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest
from google.protobuf.message import Message

from tests.game.harness import Game, logged_in
from wartune_server.game import handlers  # noqa: F401  (registra os handlers)
from wartune_server.game.handlers.login import player_info
from wartune_server.game.router import router
from wartune_server.protocol import Packet
from wartune_server.protocol.messages import wartune_pb2 as pb
from wartune_server.services.clock import FakeClock

CODES = [5027, 8286, 8292, 8294, 8295, 8489, 8535, 8740, 8741, 8746]
INVITE_TEAM, TEAM_CREATE, TEAM_INFO, TEAM_LEFT, TEAM_DISMISS = 4620, 4622, 4624, 4629, 4625
TEAM_AWAY, REFUSE_INVITE, REFUSE_TEAM = 4621, 4194, 4635
HANGUP, HANGUP_ROOM, MATCH, BLESS, CASTLE_YIELD, GUILD_INVITE = 4200, 4204, 4201, 4391, 109, 41
ROOM_LIST = 13


def _session(g: Game):  # type: ignore[no-untyped-def]
    s = g.server.online.get(g.user_id)
    assert s is not None and s.snapshot is not None
    return s


def _codes(got: list[Packet]) -> list[int]:
    return [p.code for p in got]


def _body[M: Message](got: list[Packet], code: int, cls: type[M]) -> M:
    return cls.FromString(next(p.body for p in got if p.code == code))


async def _friends(a: Game, b: Game, nick: str) -> None:
    """Amizade confirmada (como em test_social): os dois ficam de grau 40 para o convite passar."""
    for g in (a, b):
        _session(g).snapshot.character.grades = 40  # type: ignore[union-attr]
    a.client.send(15003, pb.FriendRelationMsg(nickName=nick, relation=1))
    await a.until(78)
    await b.until(84)
    b.client.send(15003, pb.FriendRelationMsg(nickName="Maga", relation=1))
    await b.until(78)
    await a.until(165)


async def _team_de_dois(a: Game, b: Game) -> None:
    """``a`` convida ``b`` (amigo online) e ``b`` aceita: o time nasce com os dois."""
    a.client.send(8738, pb.SimplePropertyMsg(param1=b.user_id))
    assert INVITE_TEAM in _codes(await b.idle())
    b.client.send(8734, pb.SimplePropertyMsg(param1=a.user_id, param7=True))
    assert TEAM_CREATE in _codes(await b.idle())
    assert TEAM_CREATE in _codes(await a.idle())


async def _create_guild(g: Game) -> None:
    c = _session(g).snapshot.character  # type: ignore[union-attr]
    c.grades, c.gold, c.point = 20, 1_000_000, 100
    await g.idle()
    g.client.send(5130, pb.ConsortiaMsg(consortiaName="Lobos"))
    await g.idle()


async def test_os_10_opcodes_tem_handler(tmp_path: Path) -> None:
    assert [code for code in CODES if router.get(code) is None] == []


async def test_corpo_vazio_nao_derruba_a_sessao(tmp_path: Path, capfd: pytest.CaptureFixture[str]) -> None:
    async with logged_in(tmp_path, novice=19000) as g:
        capfd.readouterr()  # descarta o log do login
        for code in CODES:
            g.client.send(code)  # sem corpo
        await g.idle(0.3)
        g.client.send(5026, pb.RoomReqMsg())  # a sessão ainda responde
        assert ROOM_LIST in _codes(await g.idle())
        out = capfd.readouterr()
        assert "erro tratando pacote" not in out.out + out.err


async def test_sair_de_vez_com_dois_jogadores(tmp_path: Path) -> None:
    async with logged_in(tmp_path, novice=19000) as a:
        b = await a.join("Bruxa")
        await _friends(a, b, "Bruxa")
        await _team_de_dois(a, b)
        a.client.send(8741)
        assert TEAM_DISMISS in _codes(await a.idle())  # quem saiu: a tela do time fecha
        assert TEAM_DISMISS in _codes(await b.idle())  # quem ficou: o time acabou com dois
        assert _session(a).ctx.teams.of(a.user_id) is None
        assert _session(b).ctx.teams.of(b.user_id) is None


async def test_sair_com_tres_avisa_quem_ficou(tmp_path: Path) -> None:
    async with logged_in(tmp_path, novice=19000) as a:
        b = await a.join("Bruxa")
        c = await a.join("Terceira")
        await _friends(a, b, "Bruxa")
        await _friends(a, c, "Terceira")
        await _team_de_dois(a, b)
        a.client.send(8738, pb.SimplePropertyMsg(param1=c.user_id))
        assert INVITE_TEAM in _codes(await c.idle())
        c.client.send(8734, pb.SimplePropertyMsg(param1=a.user_id, param7=True))
        await c.idle()
        await a.idle()
        await b.idle()
        b.client.send(8741)
        assert _body(await a.idle(), TEAM_LEFT, pb.SimplePropertyMsg).param1 == b.user_id
        assert _body(await c.idle(), TEAM_LEFT, pb.SimplePropertyMsg).param1 == b.user_id
        assert _body(await b.idle(), TEAM_LEFT, pb.SimplePropertyMsg).param1 == b.user_id  # o próprio id
        assert _session(a).ctx.teams.of(b.user_id) is None
        team = _session(a).ctx.teams.of(a.user_id)
        assert team is not None and sorted(team.members) == sorted([a.user_id, c.user_id])


async def test_sair_por_ora_fica_no_time_marcado(tmp_path: Path) -> None:
    async with logged_in(tmp_path, novice=19000) as a:
        b = await a.join("Bruxa")
        await _friends(a, b, "Bruxa")
        await _team_de_dois(a, b)
        b.client.send(8740)
        got_a = await a.idle()
        assert _body(got_a, TEAM_AWAY, pb.SimplePropertyMsg).param1 == b.user_id
        away = {m.playerId: m.hasLeftForNow for m in _body(got_a, TEAM_INFO, pb.TeamInfoMsg).memberDetail}
        assert away == {a.user_id: False, b.user_id: True}
        team = _session(b).ctx.teams.of(b.user_id)
        assert team is not None and b.user_id in team.members  # continua no time
        b.client.send(8740)  # alterna: volta
        back = {m.playerId: m.hasLeftForNow for m in _body(await a.idle(), TEAM_INFO, pb.TeamInfoMsg).memberDetail}
        assert back[b.user_id] is False


async def test_recusa_de_convite_de_time(tmp_path: Path) -> None:
    async with logged_in(tmp_path, novice=19000) as a:
        b = await a.join("Bruxa")
        await _friends(a, b, "Bruxa")
        b.client.send(8746)
        assert _body(await b.idle(), REFUSE_TEAM, pb.RefuseFriendRspMsg).result is True
        a.client.send(8738, pb.SimplePropertyMsg(param1=b.user_id))
        assert INVITE_TEAM not in _codes(await b.idle())  # recusado: o convite nem chega
        b.client.send(8746)  # volta a aceitar
        assert _body(await b.idle(), REFUSE_TEAM, pb.RefuseFriendRspMsg).result is False
        a.client.send(8738, pb.SimplePropertyMsg(param1=b.user_id))
        assert INVITE_TEAM in _codes(await b.idle())


async def test_recusa_de_convite_de_guilda(tmp_path: Path) -> None:
    async with logged_in(tmp_path, novice=19000) as a:
        await _create_guild(a)
        c = await a.join("clara")
        await c.idle()
        c.client.send(8286)
        assert _body(await c.idle(), REFUSE_INVITE, pb.RefuseFriendRspMsg).result is True
        a.client.send(5142, pb.ConsortiaMsg(otherId=c.user_id))
        assert GUILD_INVITE not in _codes(await c.idle())  # recusado: o 41 não chega


async def test_recusas_e_bencao_voltam_no_login(tmp_path: Path) -> None:
    async with logged_in(tmp_path, novice=19000) as a:
        b = await a.join("Bruxa")
        await _friends(a, b, "Bruxa")
        b.client.send(8746)
        await b.idle()
        b.client.send(8286)
        await b.idle()
        again_b = await b.connect()  # o PlayerMsg do login (3) sai dentro do connect; lemos a sessão
        player_b = player_info(_session(again_b), _session(again_b).snapshot)  # type: ignore[arg-type]
        assert player_b.refuseTeamInvite is True and player_b.refuseInvite is True
        _session(a).snapshot.character.crystals = 5000  # type: ignore[union-attr]
        a.client.send(8489)
        await a.idle()
        again_a = await a.connect()  # e a bênção e a contagem do dia voltam no login
        player_a = player_info(_session(again_a), _session(again_a).snapshot)  # type: ignore[arg-type]
        assert (player_a.blessingBuff, player_a.blessingCount) == (10, 1)


async def test_bencao_do_seminario(tmp_path: Path) -> None:
    async with logged_in(tmp_path, novice=19000) as a:
        c = _session(a).snapshot.character  # type: ignore[union-attr]
        c.crystals, c.seminary_effect = 5000, 195
        a.client.send(8489)
        got = await a.idle()
        bless = _body(got, BLESS, pb.BlessingMsg)
        assert (bless.increase, bless.usedCount) == (200, 1)
        assert c.crystals == 3000
        assert _body(got, CASTLE_YIELD, pb.CastleYieldMsg).crystalsCount == 3000  # o contador do cliente
        a.client.send(8489)  # no teto: recusa, mas responde 4391 com o valor atual
        assert _body(await a.idle(), BLESS, pb.BlessingMsg).increase == 200
        assert c.crystals == 3000
        c.seminary_effect, c.crystals = 0, 100  # sem cristais: recusa
        a.client.send(8489)
        assert _body(await a.idle(), BLESS, pb.BlessingMsg).increase == 0
        assert c.crystals == 100


async def test_gancho_pvp_e_transporte(tmp_path: Path) -> None:
    clock = FakeClock(datetime(2026, 1, 1, 11, 59, 30, tzinfo=UTC))  # o PvP abre às 12h (game_settings.pvp_match)
    async with logged_in(tmp_path, novice=19000, clock=clock) as a:
        a.client.send(8292)  # cancelar sem meditar: 4200 parado com o teto do dia (game_settings.rest_house)
        hang = _body(await a.idle(), HANGUP, pb.HangupInfoMsg)
        assert (hang.isStartHangup, hang.leftWeay) == (False, 50)
        a.client.send(8295)  # salas do gancho (HookFrame): uma por campanha 7001-7009, livres
        rooms = _body(await a.idle(), HANGUP_ROOM, pb.HangupStateListMsg)
        assert rooms.maxCount > 0 and [(r.campaignId, r.curCount) for r in rooms.hangupState] == [
            (7001 + i, 0) for i in range(9)
        ]
        a.client.send(8294)  # 11:59:30: fechado
        assert _body(await a.idle(), MATCH, pb.MatchStateMsg).matchState is False
        clock.advance(60)
        a.client.send(20008)  # o relógio do cliente: abriu, 4201 sem pedir
        assert _body(await a.idle(), MATCH, pb.MatchStateMsg).matchState is True
        a.client.send(20008)  # sem mudança, nada
        assert MATCH not in _codes(await a.idle())
        clock.advance(3600)  # passou a hora
        a.client.send(20008)
        assert _body(await a.idle(), MATCH, pb.MatchStateMsg).matchState is False
        a.client.send(8535)  # transporte do chefe: sem resposta
        a.client.send(5027)  # aba Hall do convite: 4161 (sozinho, vazio)
        a.client.send(5026, pb.RoomReqMsg())
        assert ROOM_LIST in _codes(await a.idle())
