"""Estado de um jogador conectado e despacho dos pacotes para os handlers."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import datetime
from typing import TYPE_CHECKING, Any

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
from . import events as ev
from . import timebox
from .announcements import Announcer
from .boss_fight import Bosses
from .events import EventCatalog
from .guild import Guilds
from .monsters import Wilds
from .rooms import Rooms
from .router import PacketRouter
from .teams import Teams
from .vehicles import Arena

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
    bosses: Bosses = field(default_factory=Bosses)  # chefe do mundo: vida compartilhada (game/boss_fight.py)
    announcer: Announcer = field(default_factory=Announcer)  # anúncios agendados (game/announcements.py)
    # árvore dourada: andares e sorte por edição (handlers/gold_tree.py)
    gold_tree: dict[str, Any] = field(default_factory=dict)
    vehicles: Arena = field(default_factory=Arena)  # fila e partidas de veículos (game/vehicles.py)
    # fúria da invasão da ilha dos pets por janela (início -> pontos; handlers/pet_defend.py)
    # shortcut: só em memória, um restart no meio da janela zera a fúria; gravar se a janela ficar longa
    pet_rage: dict[datetime, int] = field(default_factory=dict)


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
        self.battle_strategy = 0  # Daru da última luta da cidade externa (4382 na volta ao mapa)
        # derrotas em campanha: (visto) oficial_20261023-153200-1 #778, #1324, #1449 dão failCount 1, 2, 3 e as
        # lutas da cidade externa repetem o valor sem somar (#1623, #1899 perdida, #2007). (dedução) conta na sessão
        self.fail_count = 0
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
        self.vehicle_open: bool | None = None  # último 4512 mandado (o 20008 manda de novo se mudou)
        self.boss_states: dict[int, int] | None = None  # último 4182 mandado (o 20008 manda de novo se mudou)
        self.pet_defend_map: int | None = None  # mapId do último 4686 (handlers.pet_defend.push_state)
        self.pet_defend_nodes: tuple[datetime, bool] | None = None  # (janela, chefe à vista) dos nós 1003
        self.online_since: datetime | None = None  # tempo online ainda não somado (presente online)
        self.box_counting = False  # a caixa por tempo só conta depois do primeiro 5019 (timebox.py)
        self.serven_sent: bytes | None = None  # último 4638 mandado (handlers.events.refresh_serven)
        self.signin_sent: bytes | None = None  # último 513 mandado (handlers.minigames.refresh_signin)
        self.packet = Packet(0)  # o pedido em curso: o 9645 serve o minério e a super assinatura (extend1 35 / 38)
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
        self.packet = packet
        c = self.snapshot.character if self.snapshot is not None else None
        point, gift = (c.point, c.gift_token) if c is not None else (0, 0)
        await handler(self, message)
        # LeedTemp 15 "Consume Balens/Bound Balens": qualquer gasto de diamante, de qualquer pedido. (visto)
        # (só turco) yeralti_labirenti #7-#8: 3 com o vinculado a menos e então o 4152. Aqui, depois do handler inteiro.
        snap = self.snapshot
        if c is not None and snap is not None and snap.character is c and (c.point < point or c.gift_token < gift):
            from .handlers import events  # handlers importa este módulo

            await events.leed_done(self, events.BALEN_LEED)
            # atividade "Spending Bonus" (tipo 1, condição 9): só Balens, não os vinculados (*dedução*: "Spend" no
            # texto, sem captura de gasto na inglesa)
            if c.point < point:
                spent = ev.count(snap, self.ctx.events, ev.SPEND, self.ctx.clock.now(), point - c.point)
                await self.ctx.characters.save(*spent)
        if snap is not None:
            from .handlers import events  # handlers importa este módulo

            events.refresh_serven(self)
            from .handlers import minigames  # handlers importa este módulo

            await minigames.refresh_signin(self)

    async def _save_logout(self) -> None:
        """Hora da saída (recompensa offline) e o tempo online da caixa por tempo."""
        assert self.snapshot is not None
        r = timebox.rule(self.ctx.world.settings)
        timebox.on_logout(self.snapshot.character, self.ctx.clock.now(), counting=self.box_counting, r=r)
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
            from .handlers import events, room, team, vehicle, worldboss  # idem

            try:  # sala e time antes do unbind: quem fica ainda recebe a saída
                room.leave_room(self)
                team.leave_team(self)
                worldboss.leave_boss(self)
                await vehicle.leave_vehicle(self)
            except Exception:
                self.log.exception("falha ao sair da sala ou do time")
            try:
                space.leave(self)
                if self.snapshot.leader is not None:
                    guild.on_logout(
                        self,
                        rules.leader_stats(self.snapshot, self.ctx.templates, self.ctx.clock.now()).fighting_capacity,
                    )
                await self._save_logout()
                await events.leave(self)  # grava o tempo online (presente online)
            finally:  # mesmo se a gravação falhar: senão o próximo login fica esperando o kick
                self.ctx.online.unbind(self.player_id, self)
                if self.ctx.online.get(self.player_id) is None:  # relogin: a sessão nova já avisou o 160
                    social.announce(self, online=False)
                self.log.info("jogador saiu", player=self.player_id)
        self.gone.set()
