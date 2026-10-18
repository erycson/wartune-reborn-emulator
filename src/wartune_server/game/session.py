"""Estado de um jogador conectado e despacho dos pacotes para os handlers."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import datetime
from typing import TYPE_CHECKING

import structlog
from google.protobuf.message import Message

from ..domain.models import PlayerSnapshot
from ..domain.world import World
from ..net.connection import Connection
from ..protocol import Packet
from ..protocol.registry import Direction, MessageRegistry
from ..services.characters import CharacterService
from ..services.clock import Clock
from ..services.login import LoginService
from ..templates.repository import GameTemplates
from . import timebox
from .events import EventCatalog
from .guild import Guilds
from .monsters import Wilds
from .rooms import Rooms
from .router import PacketRouter
from .teams import Teams

if TYPE_CHECKING:
    from .battle import Battle
    from .campaign import CampaignMap

log = structlog.get_logger(__name__)

LOGIN_CODE = 20001
KICK_TIMEOUT = 5  # segundos para a sessão derrubada terminar o handler em andamento


@dataclass(frozen=True, slots=True)
class GameContext:
    """Dependências compartilhadas por todas as sessões (montadas em ``app``)."""

    registry: MessageRegistry
    router: PacketRouter
    login: LoginService
    characters: CharacterService
    templates: GameTemplates
    clock: Clock
    online: OnlinePlayers
    guilds: Guilds = field(default_factory=Guilds)
    events: EventCatalog = EventCatalog()  # ordem preservada: app.py passa guilds e events posicionais
    rooms: Rooms = field(default_factory=Rooms)  # salas de campanha em grupo (PvE)
    teams: Teams = field(default_factory=Teams)  # times livres (convite de amigos, até 4)
    world: World = World()  # catálogo do mundo (minas, robôs, chefes), do banco
    wilds: Wilds = field(default_factory=Wilds)  # névoa e monstros em luta (game/monsters.py)


class OnlinePlayers:
    """Jogadores com socket autenticado neste processo. Um personagem = uma sessão."""

    def __init__(self) -> None:
        self._by_id: dict[int, GameSession] = {}

    def __len__(self) -> int:
        return len(self._by_id)

    def get(self, player_id: int) -> GameSession | None:
        return self._by_id.get(player_id)

    def bind(self, player_id: int, session: GameSession) -> None:
        old = self._by_id.get(player_id)
        if old is not None and old is not session:
            log.info("login duplicado; derrubando sessão anterior", player=player_id)
            old.connection.close()
        self._by_id[player_id] = session

    def sessions(self) -> list[GameSession]:
        return list(self._by_id.values())

    def broadcast(self, code: int, message: Message, *, exclude: GameSession | None = None) -> None:
        """Manda para todos os jogadores online (sessões saindo só descartam)."""
        for session in self.sessions():
            if session is not exclude:
                session.send(code, message)

    def unbind(self, player_id: int, session: GameSession) -> None:
        if self._by_id.get(player_id) is session:
            del self._by_id[player_id]

    async def kick(self, player_id: int) -> None:
        """Derruba a sessão e espera ela terminar (o handler em andamento conclui e salva antes).

        Depois disso o banco pode ser editado por fora sem o ``merge`` da sessão desfazer.
        ``TimeoutError`` se ela não terminar a tempo.
        """
        session = self._by_id.get(player_id)
        if session is None:
            return
        log.info("derrubando sessão", player=player_id)
        session.connection.close()
        async with asyncio.timeout(KICK_TIMEOUT):
            await session.gone.wait()


class GameSession:
    def __init__(self, connection: Connection, ctx: GameContext) -> None:
        self.connection = connection
        self.ctx = ctx
        self.snapshot: PlayerSnapshot | None = None
        self.login_key: str | None = None
        self.campaign: CampaignMap | None = None
        self.battle: Battle | None = None
        self.hero_sp = 0  # SP do herói entre batalhas (o oficial carrega de uma para a outra)
        self.battle_gp = 0  # EXP da última batalha, mostrada no 4382 quando o cliente volta ao mapa
        self.space_pos: tuple[int, int] | None = None  # tile na cidade do céu; None = fora dela
        self.chat_at: dict[int, datetime] = {}  # canal -> último envio (intervalo mínimo)
        self.vice_confirmed = False  # senha secundária digitada nesta sessão (8806 op 1)
        self.accelerator_at: float | None = None  # último 20010 (time.monotonic)
        self.chat_state = 7  # estado do IM (15029): 7 online; os amigos veem no 4232/4272
        # oponentes da última lista do coliseu/torneio (4169/4611): só esses podem ser desafiados
        self.arena_offer: dict[int, int] = {}
        # exército na cidade externa (mapa, x, y em tiles) depois de andar; None = parado no castelo
        self.outer_army: tuple[int, int, int] | None = None
        self.outer_walk: asyncio.Task[None] | None = None  # chegada do exército andando (140 parado)
        self.outer_fight_over = False  # luta da cidade externa acabou: 4382 na volta (5035 state 3)
        # último 8201 com monstros: (mapa, grades, ciclo), para trocar os monstros na virada (roll_monsters)
        self.outer_view: tuple[int, set[str], datetime] | None = None
        self.pet_offer: dict[int, int] = {}
        self.online_since: datetime | None = None  # tempo online ainda não somado (presente online)
        self.gone = asyncio.Event()  # on_disconnect terminou: a sessão não grava mais nada
        self.log = log.bind(conn=connection.id)

    @property
    def player_id(self) -> int:
        assert self.snapshot is not None and self.snapshot.character.id is not None
        return self.snapshot.character.id

    def send(self, code: int, message: Message | None = None, *, extend2: int = 0) -> None:
        self.connection.send_message(code, message, extend2=extend2)

    async def on_packet(self, packet: Packet) -> None:
        if self.snapshot is None and packet.code != LOGIN_CODE:
            self.log.warning("pacote antes do login; ignorado", code=packet.code)
            return
        handler = self.ctx.router.get(packet.code)
        if handler is None:
            self.log.debug("opcode sem handler", code=packet.code, nome=self.ctx.registry.name(packet.code))
            return
        message = self.ctx.registry.decode(packet.code, Direction.CLIENT_TO_SERVER, packet.body)
        await handler(self, message)

    async def _save_logout(self) -> None:
        """Hora da saída (recompensa offline) e o tempo online da caixa por tempo."""
        assert self.snapshot is not None
        timebox.on_logout(self.snapshot.character, self.ctx.clock.now())
        try:
            await self.ctx.characters.save(self.snapshot.character)
        except Exception:  # banco fora do ar no desligamento: perde só o tempo desta sessão
            self.log.exception("falha ao gravar a saída")

    async def on_disconnect(self) -> None:
        if self.battle is not None:
            self.battle.cancel()
        if self.outer_walk is not None:
            self.outer_walk.cancel()
        if self.snapshot is not None:
            from . import guild, rules, social, space  # importam este módulo
            from .handlers import events, room, team  # idem

            try:  # sala e time antes do unbind: quem fica ainda recebe a saída
                room.leave_room(self)
                team.leave_team(self)
            except Exception:
                self.log.exception("falha ao sair da sala ou do time")
            try:
                space.leave(self)
                if self.snapshot.leader is not None:
                    guild.on_logout(self, rules.leader_stats(self.snapshot, self.ctx.templates).fighting_capacity)
                await self._save_logout()
                await events.leave(self)  # grava o tempo online (presente online)
            finally:  # mesmo se a gravação falhar: senão o próximo login fica esperando o kick
                self.ctx.online.unbind(self.player_id, self)
                if self.ctx.online.get(self.player_id) is None:  # relogin: a sessão nova já avisou o 160
                    social.announce(self, online=False)
                self.log.info("jogador saiu", player=self.player_id)
        self.gone.set()
