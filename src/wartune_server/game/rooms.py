"""Salas em grupo (campanha PvE, ``roomType`` 0, e veículo, 2): quem está em qual sala, dono e lugares.

Estado só de sala, em memória do processo (como ``Guilds``): cada jogador continua com o próprio
``s.campaign``. Por isso o registro fica no ``GameContext``, e a sessão que sai tira o jogador
daqui (``on_disconnect``). Os pacotes estão em ``handlers/room.py``. Regras em docs/salas-campanha.md.
"""

from __future__ import annotations

import itertools
from dataclasses import dataclass, field

PVE, VEHICLE = 0, 2  # RoomMsg.roomType das salas de campanha e de veículo (PvP, 1, não tem sala aqui)
MAX_SEATS = 4  # o oficial tem 4 lugares (visto: ek sahne, capacity 4)
# texto deduzido (sem fonte no cliente/captura)
NAME_NEW = "No battle selected"  # nome de sala sem campanha escolhida (visto: 12/32)
OPEN, CLOSED = 0, -1  # valor de um lugar livre aberto ou fechado (PlaceStateRspMsg); userId = ocupado
# RoomState do cliente: 0 sem uso, 1 em uso (esperando), 2 competindo, 3 jogando. O PVERoomItem só entra com 1.
IN_USE, PLAYING = 1, 3  # (só turco: exp_kitabi #25) o 125 do começo da campanha leva o 3


@dataclass
class Room:
    id: int
    master: int
    capacity: int
    password: str = ""
    campaign: int = 0  # Campaigns.CampaignId escolhida; 0 = ainda não escolhida
    seats: list[int] = field(default_factory=list)  # MAX_SEATS entradas: userId, OPEN ou CLOSED
    ready: set[int] = field(default_factory=set)  # membros (não o dono) que apertaram "pronto" (5036)
    rewarded: set[int] = field(default_factory=set)  # prontos com o ``isGet`` (usar a entrada do dia)
    state: int = IN_USE  # RoomMsg/RoomStateRspMsg.roomState (5037)
    type: int = PVE  # RoomMsg.roomType

    def __post_init__(self) -> None:
        if not self.seats:  # o dono entra no lugar 0; lugares além da capacidade ficam fechados
            self.seats = [self.master] + [OPEN] * (self.capacity - 1) + [CLOSED] * (MAX_SEATS - self.capacity)

    @property
    def members(self) -> list[int]:
        return [p for p in self.seats if p > 0]


class Rooms:
    """Registro das salas. Um jogador está em no máximo uma sala."""

    def __init__(self) -> None:
        self._rooms: dict[int, Room] = {}
        self._of: dict[int, int] = {}  # userId -> roomId
        self._ids = itertools.count(1)

    def get(self, room_id: int) -> Room | None:
        return self._rooms.get(room_id)

    def of(self, player_id: int) -> Room | None:
        room_id = self._of.get(player_id)
        return self._rooms.get(room_id) if room_id is not None else None

    def visible(self) -> list[Room]:
        return list(self._rooms.values())

    def create(self, master: int, capacity: int, password: str, room_type: int = PVE) -> Room:
        capacity = min(max(capacity, 1), MAX_SEATS)  # capacity vem do cliente
        room = Room(next(self._ids), master, capacity, password, type=room_type)
        self._rooms[room.id] = room
        self._of[master] = room.id
        return room

    def join(self, room: Room, player_id: int) -> bool:
        """Ocupa o primeiro lugar aberto. ``False`` se a sala está cheia ou o jogador já está numa."""
        if player_id in self._of or OPEN not in room.seats:
            return False
        room.seats[room.seats.index(OPEN)] = player_id
        self._of[player_id] = room.id
        return True

    def leave(self, player_id: int) -> tuple[Room, bool] | None:
        """Tira o jogador da sala. Devolve (sala, dissolvida); o dono sair dissolve a sala."""
        room = self.of(player_id)
        if room is None:
            return None
        if room.master == player_id:
            for other in room.members:
                self._of.pop(other, None)
            del self._rooms[room.id]
            return room, True
        room.seats[room.seats.index(player_id)] = OPEN
        room.ready.discard(player_id)
        del self._of[player_id]
        return room, False

    def close(self, room: Room) -> None:
        """A sala acabou sem aviso de saída (a de veículo entrando na partida: o 125 descarta a sala no cliente)."""
        for pid in room.members:
            self._of.pop(pid, None)
        self._rooms.pop(room.id, None)

    def hand_over(self, room: Room, player_id: int) -> bool:
        """Dono passa o comando para outro membro da sala."""
        if player_id not in room.members or player_id == room.master:
            return False
        room.master = player_id
        room.ready.discard(player_id)  # o dono não tem "pronto"
        return True

    def toggle_seat(self, room: Room, index: int, open_: bool) -> bool:
        """Abre ou fecha um lugar livre que não é o do dono; ``False`` se não dá."""
        if not 0 < index < MAX_SEATS:
            return False
        # abrir: só lugar fechado dentro da capacidade; fechar: só lugar livre
        allowed = (room.seats[index] == CLOSED and index < room.capacity) if open_ else room.seats[index] == OPEN
        if not allowed:
            return False
        room.seats[index] = OPEN if open_ else CLOSED
        return True
