"""Estado de um jogador conectado e despacho dos pacotes para os handlers."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING

import structlog
from google.protobuf.message import Message

from ..domain.models import PlayerSnapshot
from ..net.connection import Connection
from ..protocol import Packet
from ..protocol.registry import Direction, MessageRegistry
from ..services.characters import CharacterService
from ..services.clock import Clock
from ..services.login import LoginService
from ..templates.repository import GameTemplates
from .router import PacketRouter

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
        self.chat_state = 7  # estado do IM (15029): 7 online; os amigos veem no 4232/4272
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

    async def on_disconnect(self) -> None:
        if self.battle is not None:
            self.battle.cancel()
        if self.snapshot is not None:
            from . import social, space  # importam este módulo

            space.leave(self)
            self.ctx.online.unbind(self.player_id, self)
            if self.ctx.online.get(self.player_id) is None:  # relogin: a sessão nova já avisou o 160
                social.announce(self, online=False)
            self.log.info("jogador saiu", player=self.player_id)
        self.gone.set()
