"""Registros de salas e times, sem sessão nem overlay."""

from wartune_server.game.rooms import CLOSED, OPEN, Rooms
from wartune_server.game.teams import TEAM_MAX, Teams


def test_sala_cheia_e_saida_do_dono_dissolve():
    rooms = Rooms()
    room = rooms.create(1, 2, "")
    assert room.seats == [1, OPEN, CLOSED, CLOSED]
    assert rooms.join(room, 2)
    assert not rooms.join(room, 3)  # cheia
    assert not rooms.join(room, 2)  # já está numa sala
    assert rooms.leave(2) == (room, False)
    assert room.seats == [1, OPEN, CLOSED, CLOSED]
    assert rooms.join(room, 3)
    _, dissolved = rooms.leave(1)
    assert dissolved
    assert rooms.of(3) is None and rooms.get(room.id) is None


def test_capacidade_do_cliente_e_limitada():
    rooms = Rooms()
    assert rooms.create(1, 0, "").seats == [1, CLOSED, CLOSED, CLOSED]
    assert rooms.create(2, 10, "").seats == [2, OPEN, OPEN, OPEN]


def test_toggle_so_mexe_em_lugar_livre_dentro_da_capacidade():
    rooms = Rooms()
    room = rooms.create(1, 2, "")
    assert not rooms.toggle_seat(room, 0, False)  # lugar do dono
    assert not rooms.toggle_seat(room, 2, True)  # fora da capacidade
    assert rooms.toggle_seat(room, 1, False)
    assert not rooms.join(room, 5)  # fechado não entra ninguém
    assert rooms.toggle_seat(room, 1, True)


def test_time_convite_aceite_e_limite_de_4():
    teams = Teams()
    assert teams.invite(1, 2) and teams.has_invite(2, 1)
    team = teams.accept(2, 1)
    assert team is not None and team.members == [1, 2] and team.captain == 1
    assert teams.accept(2, 1) is None  # convite já usado
    for p in range(3, 3 + TEAM_MAX - 2):
        assert teams.invite(1, p)
        assert teams.accept(p, 1) is not None
    assert team.members == [1, 2, 3, 4]
    assert not teams.invite(1, 5)  # time cheio


def test_saida_limpa_convites_nos_dois_sentidos():
    teams = Teams()
    assert teams.invite(1, 2) and teams.accept(2, 1)
    assert teams.invite(2, 3)  # 2 convida 3
    assert teams.leave(2) is not None  # 2 sai e o time com 1 acaba
    assert teams.of(1) is None and not teams.has_invite(3, 2)
    assert teams.invite(1, 3)  # 3 continua convidável
