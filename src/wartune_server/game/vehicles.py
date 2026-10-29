"""Batalha de veículos (Tank Trials, campanha 3001): janela, fila, partida, tanques, caixas, armadilhas e chefe.

O que o cliente inglês decide fica igual a ele (m17 ``com.map.vehicle``; regras e fontes em ``docs/diversos.md``):

- a vida máxima é ``Hp + (nível do tanque - 1) × 100`` (``PlayerVehicleInfo.totalHp``);
- a partida vai até o fim da janela do ``MatchOfVehicleTime`` (``VehicleModel.remainsTime``);
- o chefe sai aos 300 s, as caixas renovam a cada 180 s e o revive geral é a cada ``revivalTime``
  (``VehicleBossDownTimeView``);
- alcance e área são em pixels (``CastAction``), e são 4 por time.

O que só o servidor oficial sabia (dano, pontos, prêmios, conteúdo das caixas e o alvo do chefe) está em
``game_settings.vehicle_match`` e aguarda dump.
Estado só em memória (``GameContext.vehicles``); os pacotes estão em ``handlers/vehicle.py``.
"""

from __future__ import annotations

import itertools
import json
import math
import random
from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import structlog
from google.protobuf.message import Message

from ..domain import gameday
from ..protocol.messages import wartune_pb2 as pb
from ..templates.repository import GameTemplates, Row

log = structlog.get_logger(__name__)

CAMPAIGN = 3001  # RoomCreatedMsg.room.campaignId que abre a cena VEHICLE (BaseManager.__createCampaignHandler)
TILE = 20
RED, BLUE, BOTH = 1, 2, 3  # PlayerVehicleMsg.team (a bandeira é o quadro 1 ou 2); winner 3 = os dois vencem
TEAM_SIZE = 4  # CampaignInfo 3001 Capacity; VehicleTeamView lista 3 colegas e o ranking 8 linhas
MIN_LEVEL = 35  # CampaignInfo 3001 MinLevel; TopToolsBar só abre o botão com 35
BOSS_TEMPLATE = 2191  # VehicleModel.bossTempId (Derleth)
BOSS_AFTER, REFRESH_EVERY, REVIVE_DEFAULT = 300, 180, 30  # VehicleBossDownTimeView; revivalTime sem linha = 30
LEAD_END = 10_000  # vehicle.helpTxt01: diferença de 10.000 pontos acaba antes
LAST_ENTRY = 300  # VehicleRoomFrame.checkCanEnter: menos de 5 min para o fim não entra
CLOSING = "Tank Trial is about to close, cannot enter."  # language EN CannotEnterVehicle
PROTECT = 4  # buff Invincible, 10 s ao entrar; some ao andar ou atacar (vehicle.helpTxt01)
STUN_BUFF = 5  # Stun 3 s: o que as passivas de atordoar (19, 20, EffectValue 3000) aplicam
NODE_BOSS, NODE_TRAP, NODE_PROP = 0, 1, 2  # VehicleNpcNodeMsg.type (VehicleNode.isBoss, VehicleBoxView)
GONE = 1  # VehicleNpcNodeMsg.state: o cliente tira o nó (VehicleModel.addNode)
NPC_AVATAR = 1  # resource 1 = avatar de NPC (o chefe); outro valor = caixa do mapmaterial/build/<sonType>.swf
SELF, SINGLE, AREA, PASSIVE, TRAP = 0, 1, 2, 3, 4  # VehicleSkillTempInfo.InjuryEffect
ENEMY = 1  # IFF
ATTACK_BY_PLAYER, ATTACK_BY_NODE = 1, 0  # VehicleAttackRspMsg.attackTyep: 1 = attackerId é um playerId
BUFF_ADD, BUFF_REMOVE, BUFF_TICK = 0, 1, 2  # VehicleBuffStateMsg.state (PlayerVehicleInfo/VehicleNode.addBuffDamage)
# VehicleBuffTempInfo.EffectType (nomes dos buffs 1-20 do template inglês)
(E_ATTACK, E_IMMUNE_CONTROL, E_INVINCIBLE, E_STUN, E_IMMUNE_STUN, E_SPEED, E_IMMUNE_SLOW, E_HP_TICK, E_LEECH,
 E_EXTRA, E_HEAL, E_IMMUNE_DAMAGE, E_SHIELD, E_STUN_PROC) = range(1, 15)  # fmt: skip
S_NODES, S_JOIN, S_END, S_LIST, S_DETAIL, S_MOVE, S_ATTACK, S_SKILL, S_BUFF, S_EXIT, S_WARN = (
    4474, 4513, 4514, 4517, 4518, 4519, 4520, 4521, 4522, 4523, 4524)  # fmt: skip
MAP_FILE = Path("data/vehicle_map_3001.json")  # tools/extract_vehicle_map.py do maps/3001/3001.titles
CENTER = (75, 75)  # meio do mapa 3001 (MapInfo 3000 × 3000 px)

# game_settings.vehicle_match (0130): regras do servidor oficial que o cliente não tem (procurado: vehicle.helpTxt01,
# VehicleAccountBottomView, VehicleSkillTempInfo, VehicleObjectTempInfo); TODO(inventado) até haver captura de partida.
# min_players: abre uma partida com 1 de cada lado; boxes: caixas no mapa; box_skills: as de ataque e de apoio, sem a
# do chefe (8); score_*: 1 ponto a cada score_damage de dano, abate, chefe; boss_every_s: golpe do chefe; runestones:
# Small Runestone de quem fica sem pacote; exp_*: Tank EXP do fim = base + 1 a cada exp_per_score pontos
MATCH_RULES: dict[str, Any] = {
    "min_players": 2,
    "boxes": 12,
    "box_skills": [2, 3, 4, 5, 6, 7, 9, 10, 11, 12, 13],
    "score_damage": 10,
    "score_kill": 100,
    "score_boss": 1000,
    "boss_every_s": 5,
    "runestones": 3,
    "exp_win": 100,
    "exp_loss": 50,
    "exp_per_score": 10,
    "defence_div": 2,  # 0135: dano = ataque × Power% - defesa / defence_div
}
FPS = 25  # Loading: frameRate 25; Speed do template é px por quadro (AvatarPathWalkAi)
UNLIMITED = -1  # VehicleSkillTempInfo.Maximum -1: usos sem fim ("--" no VehicleBottomView, sem trava no keyDown)
BOX_SON_TYPE = 5000  # sonType = 5000 + skill (os mapmaterial/build/5001-5018.swf da CDN)
SLACK = 2  # tiles de folga no alcance (o cliente manda a posição de onde atirou, com atraso)
CD_SLACK = timedelta(milliseconds=300)  # folga na recarga, pelo mesmo motivo
BOSS_WARN = timedelta(seconds=2)  # o 4524 mostra o círculo por 2 s
TRAP_DAMAGE = 300  # VehicleSkillTempInfo 7: "When trap activates, deals 300 damage."
TRAP_REACH = 10  # tiles até onde a armadilha (AttackRange 0) pode ser posta
MISS, IMMUNE, ABSORBED = -1, -2, -3  # quadros especiais do HurtNumberAction (o significado de cada um é dedução)
VICTORY, FAILURE = 2131009, 2131010  # Victory Chest / Failure Chest (ItemTempInfo; vehicle.AccountBottomView)
RANK_PACKS = (2131015, 2131014, 2131013, 2131012, 2131011)  # Diamond, Gold, Silver, Bronze, Iron Runestone Pack
RUNESTONE = 3020010  # Small Runestone (o _templateId3 do VehicleAccountBottomView)
LOW_SCORE, LOW_RANK = 200, 8  # VehicleAccountBottomView.getRunking: menos de 200 pontos conta como 8º


def _config(templates: GameTemplates, name: str, default: str) -> str:
    row = templates.get("ConfigInfos", name, key="ConfigName")
    return row["ConfigValue"] if row else default


def _int(row: Row | None, key: str) -> int:
    return int((row or {}).get(key) or 0)


def window(templates: GameTemplates, now: datetime) -> tuple[datetime, datetime] | None:
    """Janela aberta agora (``MatchOfVehicleTime`` nos dias ``Vehicle_Day``, no fuso do jogo), ou ``None``.

    O cliente usa o ``MatchOfVehicleTime`` (``VehicleModel.initStartEndDate``): ``10:00,10:25|16:00,16:25``. O
    ``CampaignInfo`` tem só a primeira e a ajuda diz até 10:30; vale a config, que é o que o relógio do cliente usa.
    """
    local = gameday.local(now)
    days = {d.strip() for d in _config(templates, "Vehicle_Day", "1,2,3,4,5,6,7").split(",")}
    if str(local.isoweekday()) not in days:
        return None
    for part in _config(templates, "MatchOfVehicleTime", "").split("|"):
        try:
            begin, end = ([int(v) for v in hhmm.split(":")] for hhmm in part.split(","))
        except ValueError:
            continue
        start = local.replace(hour=begin[0], minute=begin[1], second=0, microsecond=0)
        stop = local.replace(hour=end[0], minute=end[1], second=0, microsecond=0)
        if start <= local < stop:
            return start, stop
    return None


def tank_grade(templates: GameTemplates, exp: int) -> int:
    """Nível do tanque pela EXP (``PlayerInfo.vehicleGrade``): ``UpGradeTempInfos`` tipo 24, ``Data`` somado."""
    rows = sorted(templates.find("UpGradeTempInfos", Types="24"), key=lambda r: int(r["Grades"]))
    grade, start = 1, 0
    for row in rows:
        end = start + int(row["Data"])
        if start <= exp < end:
            break
        grade, start = int(row["Grades"]), end
    return grade


@dataclass(frozen=True, slots=True)
class TankMap:
    walkable: frozenset[tuple[int, int]]
    marks: tuple[tuple[int, int], ...]

    def walk(self, x: int, y: int) -> bool:
        return (x, y) in self.walkable


_maps: dict[Path, TankMap | None] = {}


def tank_map(path: Path = MAP_FILE) -> TankMap | None:
    """Os tiles do 3001 (andável = valor > 0 e ≠ 2, ``VehicleModel.getWalkable``). Sem o arquivo: ``None``."""
    if path not in _maps:
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except FileNotFoundError:
            log.warning("mapa dos veículos ausente: andar sem conferência", arquivo=str(path))
            _maps[path] = None
        else:
            walk = frozenset(tuple(int(v) for v in k.split("_")) for k in data["walkable"])
            _maps[path] = TankMap(walk, tuple((int(x), int(y)) for x, y in data["marks"]))  # type: ignore[arg-type]
    return _maps[path]


def skill_buffs(row: Row | None) -> list[tuple[int, int]]:
    """``Buffs`` "id,chance%" (``"5,50"``); vazio quando a skill não tem."""
    out = []
    for part in (row or {}).get("Buffs", "").split("|"):
        if "," in part:
            bid, chance = part.split(",")
            out.append((int(bid), int(chance)))
    return out


@dataclass
class Buff:
    id: int  # VehicleBuffStateMsg.id (a instância; o cliente guarda por ele)
    buff_id: int
    effect: int
    value: int
    percent: int
    ends: datetime
    interval: timedelta | None = None
    next_tick: datetime | None = None
    left: int = 0  # o que o escudo (E_SHIELD) ainda absorve
    source: int = 0  # quem pôs (o sangramento dá os pontos e o abate a ele)


@dataclass
class Tank:
    player_id: int
    name: str
    template: int
    team: int
    grade: int
    attack: int
    defence: int
    dodge: int
    max_hp: int
    normal: int
    genius: int
    guild: str = ""
    vip: int = 0
    hp: int = 0
    x: int = 0
    y: int = 0
    extra: int = 0  # skill da caixa, na tecla Q (VehicleSkillbag: posição 3)
    extra_left: int = 0  # UNLIMITED = sem fim
    moved: datetime | None = None  # último passo aceito (ou a entrada): base da conferência de velocidade
    used: dict[int, datetime] = field(default_factory=dict)  # skill -> último uso (recarga)
    buffs: dict[int, Buff] = field(default_factory=dict)
    score: int = 0

    @property
    def alive(self) -> bool:
        return self.hp > 0

    def has(self, effect: int) -> Buff | None:
        return next((b for b in self.buffs.values() if b.effect == effect), None)


def new_tank(
    templates: GameTemplates, player_id: int, name: str, template: int, exp: int, team: int, *, guild: str, vip: int
) -> Tank | None:
    row = templates.get("VehicleObjectTempInfos", template)
    if row is None:
        return None
    grade = tank_grade(templates, exp)
    hp = _int(row, "Hp") + (grade - 1) * 100  # PlayerVehicleInfo.totalHp
    return Tank(player_id, name, template, team, grade, _int(row, "Attack"), _int(row, "Defence"), _int(row, "Dodge"),
                hp, _int(row, "NormalSkill"), _int(row, "GeniusSkill"), guild=guild, vip=vip, hp=hp)  # fmt: skip


@dataclass
class Node:
    node_id: int
    type: int
    x: int
    y: int
    skill: int = 0  # caixa: a skill que dá; armadilha: a que pôs (7)
    owner: int = 0
    team: int = 0
    hp: int = 0
    name: str = ""
    son_type: int = 0
    hero: int = 0
    resource: int = 0
    attack: int = 0
    defence: int = 0
    dodge: int = 0


@dataclass(frozen=True, slots=True)
class Reward:
    player_id: int
    score: int
    exp: int
    items: tuple[tuple[int, int], ...]


def _dist(a: tuple[int, int], b: tuple[int, int]) -> float:
    return math.dist(a, b)


Deliver = Callable[[int, int, Message], None]


class Match:
    """Uma partida: tanques, nós (chefe, armadilhas, caixas), placar e relógio. Sem I/O: tudo sai por ``deliver``."""

    def __init__(
        self,
        templates: GameTemplates,
        start: datetime,
        end: datetime,
        deliver: Deliver,
        *,
        rnd: random.Random | None = None,
        tiles: TankMap | None = None,
        rules: Mapping[str, Any] | None = None,
    ) -> None:
        self.templates, self.start, self.end, self.deliver = templates, start, end, deliver
        self.rules = MATCH_RULES | dict(rules or {})
        self.rnd = rnd or random.Random()
        self.tiles = tiles
        self.seats: dict[int, int] = {}  # player_id -> time (reservado na fila, antes de entrar)
        self.tanks: dict[int, Tank] = {}
        self.nodes: dict[int, Node] = {}
        self.scores = {RED: 0, BLUE: 0}
        self._ids = itertools.count(1)
        revive = int(_config(templates, "revivalTime", str(REVIVE_DEFAULT)) or REVIVE_DEFAULT)
        self.revive_every = timedelta(seconds=max(1, revive))
        self.next_revive = start + self.revive_every
        self.next_refresh = start
        self.boss_at: datetime | None = start + timedelta(seconds=BOSS_AFTER)
        self.boss_next: datetime | None = None
        self.strike: tuple[datetime, int, int] | None = None
        self.over = False
        self._hp: set[int] = set()  # tanques com vida mudada: um 4513 no fim da ação
        self._score = False

    # -- envio ---------------------------------------------------------------------------------------------------

    def all(self, code: int, msg: Message, *, but: int = 0) -> None:
        for pid in list(self.tanks):
            if pid != but:
                self.deliver(pid, code, msg)

    def _flush(self, now: datetime) -> None:
        if self._hp:
            items = [self._hp_msg(self.tanks[p], now) for p in sorted(self._hp) if p in self.tanks]
            self._hp.clear()
            if items:
                self.all(S_JOIN, pb.PlayerVehicleListMsg(vehicles=items))
        if self._score:
            self._score = False
            for pid in list(self.tanks):
                self.deliver(pid, S_DETAIL, self.detail(pid))

    def _hp_msg(self, t: Tank, now: datetime) -> pb.PlayerVehicleMsg:
        """O 4513 é o único jeito de mudar a vida no cliente; morto leva o ``rebornTime`` (s até o revive geral)."""
        msg = pb.PlayerVehicleMsg(playerId=t.player_id, hp=t.hp)
        if not t.alive:
            msg.rebornTime = max(1, math.ceil((self.next_revive - now).total_seconds()))
        return msg

    def tank_msg(self, t: Tank, now: datetime) -> pb.PlayerVehicleMsg:
        msg = pb.PlayerVehicleMsg(
            playerId=t.player_id, id=t.player_id, templateId=t.template, team=t.team, grade=t.grade, hp=t.hp,
            name=t.name, x=t.x, y=t.y, consortia=t.guild, vip=t.vip, buffState=[b.buff_id for b in t.buffs.values()],
        )  # fmt: skip
        if not t.alive:
            msg.rebornTime = self._hp_msg(t, now).rebornTime
        return msg

    def node_msg(self, n: Node, *, gone: bool = False) -> pb.VehicleNpcNodeMsg:
        if gone:
            return pb.VehicleNpcNodeMsg(nodeId=n.node_id, state=GONE)
        return pb.VehicleNpcNodeMsg(
            nodeId=n.node_id, type=n.type, curX=n.x, curY=n.y, state=0, hp=n.hp, name=n.name, sonType=n.son_type,
            heroTempId=n.hero, resource=n.resource, nameColor=1, restX=n.x, restY=n.y, team=n.team,
        )  # fmt: skip

    def detail(self, player_id: int) -> pb.VehicleCampaignDetailMsg:
        """4518: placar e relógio. ``remainsTiem`` é fim da janela - início da partida: o cliente põe o
        ``campaiganStartTime`` em fim - ``remainsTiem`` e conta dali o chefe, as caixas e o revive (*dedução*)."""
        me = self.tanks.get(player_id)
        return pb.VehicleCampaignDetailMsg(
            campaignId=CAMPAIGN, redTeamScroe=self.scores[RED], blueTeamScroe=self.scores[BLUE],
            myScroe=me.score if me else 0, remainsTiem=int((self.end - self.start).total_seconds()),
            scroeList=[pb.VehicleScroeListMsg(playerId=t.player_id, playerScroe=t.score) for t in self.tanks.values()],
        )  # fmt: skip

    # -- lugares -------------------------------------------------------------------------------------------------

    def count(self, team: int) -> int:
        return sum(1 for t in self.seats.values() if t == team)

    def team_for(self, size: int) -> int | None:
        """O time com menos gente que ainda cabe ``size`` (um grupo da sala fica junto)."""
        teams = sorted((RED, BLUE), key=lambda t: (self.count(t), self.scores[t]))
        return next((t for t in teams if self.count(t) + size <= TEAM_SIZE), None)

    def _free_spot(self, taken: Iterable[tuple[int, int]] = ()) -> tuple[int, int]:
        busy = set(taken)
        spots = [m for m in (self.tiles.marks if self.tiles else ()) if m not in busy]
        return self.rnd.choice(spots) if spots else CENTER

    # -- entrar e sair -------------------------------------------------------------------------------------------

    def join(self, tank: Tank, now: datetime) -> None:
        """Entrada (``VehicleSceneController``; o 125 vai antes, de quem chama): 4474 antes do 4517 (a vida do
        chefe só pega com o nó já criado), 4517 com todos (o próprio com ``templateId`` e ``hp``: sem eles o
        ``VehicleSkillbag`` quebra e -1 é morto), 4518, e o 4513 do novo para os outros. Nasce num ponto sorteado
        com 10 s de proteção (vehicle.helpTxt01)."""
        tank.x, tank.y = self._free_spot((t.x, t.y) for t in self.tanks.values())
        tank.moved = now
        self.seats[tank.player_id] = tank.team
        self.tanks[tank.player_id] = tank
        pid = tank.player_id
        self.deliver(
            pid, S_NODES, pb.VehicleNpcNodeListMsg(vehicleNpcNode=[self.node_msg(n) for n in self.nodes.values()])
        )
        roster = [self.tank_msg(t, now) for t in self.tanks.values()]
        if (boss := self.boss()) is not None:
            roster.append(pb.PlayerVehicleMsg(hp=boss.hp))  # sem playerId: a vida do chefe (__initPlayerListHandler)
        self.deliver(pid, S_LIST, pb.PlayerVehicleListMsg(vehicles=roster))
        self.deliver(pid, S_DETAIL, self.detail(pid))
        self.all(S_JOIN, pb.PlayerVehicleListMsg(vehicles=[self.tank_msg(tank, now)]), but=pid)
        self.add_buff(tank, PROTECT, now)
        self._score = True
        self._flush(now)

    def leave(self, player_id: int, now: datetime) -> bool:
        """8610 ou desconexão: 4523 para todos (o próprio volta à cidade, ``__playerExitHandler``); as armadilhas
        dele somem."""
        self.seats.pop(player_id, None)
        if player_id not in self.tanks:
            return False
        exit_msg = pb.VehicleExitMsg(playerId=player_id)
        self.all(S_EXIT, exit_msg)
        del self.tanks[player_id]
        traps = [n for n in self.nodes.values() if n.type == NODE_TRAP and n.owner == player_id]
        for n in traps:
            self._remove_node(n)
        self._score = True
        self._flush(now)
        return True

    # -- ações do jogador ----------------------------------------------------------------------------------------

    def move(self, player_id: int, path: list[tuple[int, int]], now: datetime) -> bool:
        """8615: até 3 pontos à frente (``AvatarPathWalkAi``); os outros recebem o 4519 e andam até ``path[0]``.
        Morto também anda (vehicle.helpTxt01). A velocidade é a do cliente: ``Speed`` do template em px por quadro
        (25 fps, ``AvatarPathWalkAi``), com os buffs 6 (``PlayerVehicleInfo.checkSpeed``); passo mais longo que isso
        desde o último (ou a entrada), com ``SLACK`` tiles de folga, é recusado.
        """
        t = self.tanks.get(player_id)
        if t is None or not path or len(path) > 10:
            return False
        if self.tiles is not None and not all(self.tiles.walk(x, y) for x, y in path):
            return False
        reach = self._speed(t) * FPS * (now - (t.moved or now)).total_seconds() / TILE + SLACK
        if _dist((t.x, t.y), path[0]) > reach:
            return False
        t.x, t.y = path[0]
        t.moved = now
        self._unprotect(t, now)
        msg = pb.VehicleMoveMsg(playerId=player_id, path=[pb.Position(x=x, y=y) for x, y in path])
        self.all(S_MOVE, msg, but=player_id)
        self._traps(now)
        self._flush(now)
        return True

    def cast(self, player_id: int, req: pb.VehicleAttackReqMsg, now: datetime) -> bool:
        """8616, na metade do ``CastTime`` (``CastAction.send``). O servidor refaz as travas do cliente
        (``VehicleCharacterController.keyDownHandler``): vivo, sem atordoamento, skill que ele tem, recarga, quantas
        restam, alcance, inimigo vivo e sem o buff 4; a área é calculada aqui (o cliente só manda 1 NPC)."""
        t = self.tanks.get(player_id)
        sid = req.skillId
        row = self.templates.get("VehicleSkillTempInfos", sid)
        if (
            self.over
            or t is None
            or not t.alive
            or t.has(E_STUN)
            or row is None
            or sid not in (t.normal, t.genius, t.extra)
        ):
            return False
        kind, cd = _int(row, "InjuryEffect"), timedelta(milliseconds=_int(row, "CoolDown"))
        last = t.used.get(sid)
        if (
            kind == PASSIVE
            or (sid == t.extra and t.extra_left == 0)
            or (last is not None and now - last < cd - CD_SLACK)
        ):
            return False
        reach = _int(row, "AttackRange") / TILE + SLACK
        point = (req.effectX, req.effectY)
        players: list[Tank] = []
        npcs: list[Node] = []
        if kind == SINGLE:
            target = self.tanks.get(req.suffererId[0]) if req.suffererId else None
            node = self.nodes.get(req.suffererNpcId) if req.HasField("suffererNpcId") else None
            if target is not None:
                if target.team == t.team or not target.alive or target.has(E_INVINCIBLE):
                    return False
                if _dist((t.x, t.y), (target.x, target.y)) > reach:
                    return False
                players, point = [target], (target.x, target.y)
            elif node is not None and node.type == NODE_BOSS:
                if _dist((t.x, t.y), (node.x, node.y)) > reach:
                    return False
                npcs, point = [node], (node.x, node.y)
            elif _dist((t.x, t.y), point) > reach:  # tiro que parou numa barreira: só a animação
                return False
        elif kind == AREA:
            if _dist((t.x, t.y), point) > reach:
                return False
            radius = _int(row, "DamageCoverage")
            players = [o for o in self.tanks.values()
                       if o.team != t.team and o.alive and _dist((o.x, o.y), point) * TILE < radius]  # fmt: skip
            npcs = [n for n in self.nodes.values()
                    if n.type == NODE_BOSS and _dist((n.x, n.y), point) * TILE < radius]  # fmt: skip
        elif kind == TRAP:
            if _dist((t.x, t.y), point) > TRAP_REACH or (self.tiles is not None and not self.tiles.walk(*point)):
                return False
        elif kind == SELF:
            point = (t.x, t.y)
        t.used[sid] = now
        self._unprotect(t, now)
        self._spend(t, sid)
        rsp = pb.VehicleAttackRspMsg(skillId=sid, effectX=point[0], effectY=point[1], attackerId=player_id,
                                     attackTyep=ATTACK_BY_PLAYER)  # fmt: skip
        if kind == SELF:
            for bid, chance in skill_buffs(row):
                if self.rnd.randrange(100) < chance:
                    self.add_buff(t, bid, now, source=player_id)
        elif kind == TRAP:
            self._add_node(Node(next(self._ids), NODE_TRAP, point[0], point[1], skill=sid, owner=player_id, team=t.team,
                                name=row.get("TemplateName", ""), son_type=BOX_SON_TYPE + sid))  # fmt: skip
        else:
            power = _int(row, "Power")
            for o in players:
                value = self._attack(t, o, power, now)
                rsp.playerHurtDataList.add(affecteId=o.player_id, value=value)
                if value > 0:
                    for bid, chance in skill_buffs(row):
                        if self.rnd.randrange(100) < chance:
                            self.add_buff(o, bid, now, source=player_id)
            for n in npcs:
                value = self._hit_node(t, n, self._raw(t.attack, power, n.defence, t), now)
                rsp.npcHurtDataList.add(affecteId=n.node_id, value=value)
        self.all(S_ATTACK, rsp)
        self._flush(now)
        return True

    def pickup(self, player_id: int, node_id: int, now: datetime) -> bool:
        """8617 (``PickupAction``, 0,8 s num canal de 1,5 s): a skill da caixa vai para a tecla Q (4521; skill nova
        cai na posição 3, ``VehicleSkillbag.updateSkill``) e a caixa some para todos. Morto não pega
        ("vehicle.waitRiver")."""
        t, n = self.tanks.get(player_id), self.nodes.get(node_id)
        if t is None or not t.alive or n is None or n.type != NODE_PROP or _dist((t.x, t.y), (n.x, n.y)) > 4 + SLACK:
            return False
        row = self.templates.get("VehicleSkillTempInfos", n.skill)
        if t.extra and t.extra != n.skill:
            self.deliver(player_id, S_SKILL, pb.VehicleSkillListMsg(skillId=t.extra, state=1, curSum=0))
        limit = _int(row, "Maximum")  # o cliente só trava com Maximum > 0 (VehicleCharacterController.keyDownHandler)
        t.extra, t.extra_left = n.skill, limit if limit > 0 else UNLIMITED
        self._remove_node(n)
        self.deliver(player_id, S_SKILL, pb.VehicleSkillListMsg(skillId=t.extra, state=0, curSum=t.extra_left))
        self._unprotect(t, now)
        return True

    # -- relógio -------------------------------------------------------------------------------------------------

    def tick(self, now: datetime) -> bool:
        """Um segundo de partida: buffs, revive geral, caixas, chefe, armadilhas e o fim. ``True`` = acabou."""
        if self.over:
            return True
        for t in list(self.tanks.values()):
            self._tick_buffs(t, now)
        while now >= self.next_revive:
            for t in self.tanks.values():
                if not t.alive:
                    t.hp = t.max_hp
                    self._hp.add(t.player_id)
                    self.add_buff(t, PROTECT, now)
            self.next_revive += self.revive_every
        if now >= self.next_refresh:
            self._refresh_boxes()
            while now >= self.next_refresh:
                self.next_refresh += timedelta(seconds=REFRESH_EVERY)
        self._boss(now)
        self._traps(now)
        self._flush(now)
        return self.ended(now)

    def ended(self, now: datetime) -> bool:
        if self.over:
            return True
        sides = {t.team for t in self.tanks.values()}
        return now >= self.end or abs(self.scores[RED] - self.scores[BLUE]) >= LEAD_END or len(sides) < 2

    def winner(self) -> int:
        sides = {t.team for t in self.tanks.values()}
        if len(sides) == 1:
            return sides.pop()  # o outro lado saiu todo
        if self.scores[RED] == self.scores[BLUE]:
            return BOTH
        return RED if self.scores[RED] > self.scores[BLUE] else BLUE

    def finish(self, rewarded: set[int]) -> list[Reward]:
        """4514 para todos (o cliente fecha a cena sozinho, ``AccountAction``) e os prêmios de quem ainda não ganhou
        nesta janela ("one round of settlement rewards per event session"). Quem já ganhou recebe o placar com 0.

        A posição é a do cliente (pontos, ``getRunking``): 1º-5º um pacote de Runestone, 6º em diante ou menos de 200
        pontos a Runestone pequena. Quantidades e a EXP do tanque são config (vehicle_match: runestones, exp_*; 0130),
        aguarda dump.
        """
        self.over = True
        win = self.winner()
        ranked = sorted(self.tanks.values(), key=lambda t: t.score, reverse=True)
        rewards: dict[int, Reward] = {}
        for index, t in enumerate(ranked):
            if t.player_id in rewarded:
                continue
            won = win in (t.team, BOTH)
            rank = LOW_RANK if t.score < LOW_SCORE else index + 1
            pack = (RANK_PACKS[rank - 1], 1) if rank <= len(RANK_PACKS) else (RUNESTONE, int(self.rules["runestones"]))
            rule = self.rules
            exp = int(rule["exp_win"] if won else rule["exp_loss"]) + t.score // int(rule["exp_per_score"])
            rewards[t.player_id] = Reward(t.player_id, t.score, exp, ((VICTORY if won else FAILURE, 1), pack))
            rewarded.add(t.player_id)
        lines = []
        for t in ranked:
            line = pb.VehicleScroeListMsg(playerId=t.player_id, playerScroe=t.score)
            if (r := rewards.get(t.player_id)) is not None:
                (chest, chests), (pack_id, packs) = r.items
                line.playerExp, line.awardPropId, line.awardSum = r.exp, chest, chests
                line.ladderPropId, line.ladderSum = pack_id, packs
            lines.append(line)
        for t in ranked:
            self.deliver(t.player_id, S_END, pb.VehicleCampaignDetailMsg(
                campaignId=CAMPAIGN, redTeamScroe=self.scores[RED], blueTeamScroe=self.scores[BLUE], myScroe=t.score,
                remainsTiem=0, winner=win, scroeList=lines))  # fmt: skip
        self.tanks.clear()
        self.seats.clear()
        return list(rewards.values())

    # -- regras --------------------------------------------------------------------------------------------------

    def _raw(self, attack: int, power: int, defence: int, src: Tank | None = None) -> int:
        """Dano = ataque × Power% - defesa / ``defence_div`` (mínimo 1), com os buffs de ataque (EffectType 1).
        O divisor é config (vehicle_match, 0135), aguarda dump."""
        if src is not None:
            for b in src.buffs.values():
                if b.effect == E_ATTACK:
                    attack += b.value + attack * b.percent // 100
        return max(1, attack * power // 100 - defence // max(1, int(self.rules["defence_div"])))

    def _speed(self, t: Tank) -> int:
        """``PlayerVehicleInfo.checkSpeed``: Speed do template + o maior buff 6 positivo + o menor negativo."""
        base = _int(self.templates.get("VehicleObjectTempInfos", t.template), "Speed") or 7  # PlayerVehicleInfo.speed
        up = down = 0
        for b in t.buffs.values():
            if b.effect == E_SPEED:
                delta = base * b.percent // 100 if b.percent else b.value
                up, down = max(up, delta), min(down, delta)
        return max(0, base + up + down)

    def _passive(self, t: Tank) -> Row | None:
        """O buff da passiva do ``GeniusSkill`` (InjuryEffect 3); a chance é o ``TogglePercent`` dele."""
        row = self.templates.get("VehicleSkillTempInfos", t.genius)
        if _int(row, "InjuryEffect") != PASSIVE:
            return None
        pairs = skill_buffs(row)
        return self.templates.get("VehicleBuffTempInfos", pairs[0][0]) if pairs else None

    def _attack(self, src: Tank, target: Tank, power: int, now: datetime) -> int:
        dmg = self._raw(src.attack, power, target.defence, src)
        proc = self._passive(src)
        hit = proc is not None and self.rnd.randrange(100) < _int(proc, "TogglePercent")
        effect = _int(proc, "EffectType") if hit else 0
        if effect == E_EXTRA:
            dmg += dmg * _int(proc, "EffectPercent") // 100
        value = self._hit_tank(src, target, dmg, now, dodge=True)
        if value > 0 and effect == E_LEECH and src.alive:
            src.hp = min(src.max_hp, src.hp + value * _int(proc, "EffectPercent") // 100)
            self._hp.add(src.player_id)
        if value > 0 and effect == E_STUN_PROC and target.alive:
            self.add_buff(target, STUN_BUFF, now, source=src.player_id)
        return value

    def _hit_tank(self, src: Tank | None, target: Tank, dmg: int, now: datetime, *, dodge: bool) -> int:
        """Dano num tanque: invencível ou imune mostra -2, esquiva -1, escudo que segura tudo -3."""
        if not target.alive:
            return 0
        if target.has(E_INVINCIBLE) or target.has(E_IMMUNE_DAMAGE):
            return IMMUNE
        if dodge and self.rnd.randrange(100) < target.dodge:
            return MISS
        if (shield := target.has(E_SHIELD)) is not None:
            taken = min(shield.left, dmg)
            shield.left -= taken
            dmg -= taken
            if shield.left <= 0:
                self._remove_buff(target, shield)
            if dmg <= 0:
                return ABSORBED
        target.hp = max(0, target.hp - dmg)
        self._hp.add(target.player_id)
        if src is not None and src.team != target.team:
            self._points(src, dmg // self.rules["score_damage"] + (self.rules["score_kill"] if not target.alive else 0))
        if not target.alive:
            for b in list(target.buffs.values()):  # o cliente limpa os buffs sozinho com a vida em 0
                del target.buffs[b.id]
        return dmg

    def _hit_node(self, src: Tank | None, n: Node, dmg: int, now: datetime) -> int:
        if n.node_id not in self.nodes or n.hp <= 0:
            return 0
        dmg = min(dmg, n.hp)
        n.hp -= dmg
        if src is not None:
            self._points(src, dmg // self.rules["score_damage"] + (self.rules["score_boss"] if n.hp <= 0 else 0))
        if n.hp <= 0:
            self._remove_node(n)
        else:
            self.all(
                S_NODES, pb.VehicleNpcNodeListMsg(vehicleNpcNode=[pb.VehicleNpcNodeMsg(nodeId=n.node_id, hp=n.hp)])
            )
        return dmg

    def _points(self, t: Tank, points: int) -> None:
        if points > 0:
            t.score += points
            self.scores[t.team] += points
            self._score = True

    def _spend(self, t: Tank, sid: int) -> None:
        if sid != t.extra or t.extra_left == UNLIMITED:
            return
        t.extra_left -= 1
        if t.extra_left <= 0:
            self.deliver(t.player_id, S_SKILL, pb.VehicleSkillListMsg(skillId=sid, state=1, curSum=0))
            t.extra = 0

    def add_buff(self, t: Tank, buff_id: int, now: datetime, *, source: int = 0) -> None:
        """Buff num tanque (4522 estado 0). Imunes (3, 6, 9, 15, 16) barram atordoar e lentidão; o mesmo buff de novo
        troca o antigo; ``Duration`` 0 é instantâneo (a cura de 1500) e -1 é traço de passiva (não entra)."""
        row = self.templates.get("VehicleBuffTempInfos", buff_id)
        if row is None or not t.alive:
            return
        effect, value, percent, duration = (
            _int(row, k) for k in ("EffectType", "EffectValue", "EffectPercent", "Duration")
        )
        immune_control = t.has(E_IMMUNE_CONTROL) is not None
        if effect == E_STUN and (immune_control or t.has(E_IMMUNE_STUN)):
            return
        if effect == E_SPEED and (value < 0 or percent < 0) and (immune_control or t.has(E_IMMUNE_SLOW)):
            return
        if duration < 0:
            return
        state = pb.VehicleBuffStateMsg(id=next(self._ids), buffId=buff_id, state=BUFF_ADD, playerId=t.player_id,
                                       effectValue=value)  # fmt: skip
        if duration == 0:
            if effect == E_HEAL:
                t.hp = min(t.max_hp, t.hp + value)
                self._hp.add(t.player_id)
            self.all(S_BUFF, pb.VehicleBuffListMsg(playerBuffStates=[state]))
            return
        for old in [b for b in t.buffs.values() if b.buff_id == buff_id]:
            self._remove_buff(t, old)
        interval = timedelta(milliseconds=_int(row, "Interval")) if _int(row, "Interval") > 0 else None
        t.buffs[state.id] = Buff(state.id, buff_id, effect, value, percent, now + timedelta(milliseconds=duration),
                                 interval, now + interval if interval else None, value, source)  # fmt: skip
        self.all(S_BUFF, pb.VehicleBuffListMsg(playerBuffStates=[state]))

    def _remove_buff(self, t: Tank, b: Buff) -> None:
        t.buffs.pop(b.id, None)
        state = pb.VehicleBuffStateMsg(id=b.id, buffId=b.buff_id, state=BUFF_REMOVE, playerId=t.player_id)
        self.all(S_BUFF, pb.VehicleBuffListMsg(playerBuffStates=[state]))

    def _unprotect(self, t: Tank, now: datetime) -> None:
        for b in [b for b in t.buffs.values() if b.buff_id == PROTECT]:
            self._remove_buff(t, b)

    def _tick_buffs(self, t: Tank, now: datetime) -> None:
        """Sangramento e restauração (EffectType 8, ``Interval``): 4522 estado 2 com o valor (o número aparece) e a
        vida no 4513; depois do ``Duration``, estado 1."""
        for b in list(t.buffs.values()):
            while b.next_tick is not None and b.interval is not None and now >= b.next_tick and b.next_tick <= b.ends:
                b.next_tick += b.interval
                if not t.alive:
                    break
                if b.value < 0:
                    self._hit_tank(self.tanks.get(b.source), t, -b.value, now, dodge=False)
                else:
                    t.hp = min(t.max_hp, t.hp + b.value)
                    self._hp.add(t.player_id)
                state = pb.VehicleBuffStateMsg(id=b.id, buffId=b.buff_id, state=BUFF_TICK, playerId=t.player_id,
                                               effectValue=b.value)  # fmt: skip
                self.all(S_BUFF, pb.VehicleBuffListMsg(playerBuffStates=[state]))
            if b.id in t.buffs and now >= b.ends:
                self._remove_buff(t, b)

    def _add_node(self, n: Node) -> None:
        self.nodes[n.node_id] = n
        self.all(S_NODES, pb.VehicleNpcNodeListMsg(vehicleNpcNode=[self.node_msg(n)]))

    def _remove_node(self, n: Node) -> None:
        if self.nodes.pop(n.node_id, None) is not None:
            self.all(S_NODES, pb.VehicleNpcNodeListMsg(vehicleNpcNode=[self.node_msg(n, gone=True)]))

    def boss(self) -> Node | None:
        return next((n for n in self.nodes.values() if n.type == NODE_BOSS), None)

    def _refresh_boxes(self) -> None:
        """Caixas a cada 180 s ("Skills Refresh"): completa até ``boxes`` nos pontos marcados do mapa."""
        props = [n for n in self.nodes.values() if n.type == NODE_PROP]
        taken = [(n.x, n.y) for n in props]
        for _ in range(int(self.rules["boxes"]) - len(props)):
            x, y = self._free_spot(taken)
            if (x, y) in taken:
                break
            taken.append((x, y))
            sid = int(self.rnd.choice(self.rules["box_skills"]))
            row = self.templates.get("VehicleSkillTempInfos", sid)
            self._add_node(Node(next(self._ids), NODE_PROP, x, y, skill=sid, name=(row or {}).get("TemplateName", ""),
                                son_type=BOX_SON_TYPE + sid))  # fmt: skip

    def _boss(self, now: datetime) -> None:
        """Derleth aos 300 s (``VehicleObjectTempInfo`` 2191: vida 10000, ataque 200, skill 8 com 600 px de alcance e
        300 de área). O 4524 marca o alvo por 2 s, depois a área bate em todo tanque dentro dela.

        Parado no meio do mapa como no cliente: o ``VehicleNpcAvatarView`` não anda (não tem ``AvatarPathWalkAi``
        nem pacote de movimento de nó), só vira para o alvo (``changeDirectionTo``) ao atirar. O cliente não escolhe
        alvo (só desenha o 4524): um tanque vivo ao alcance (``AttackRange`` da skill), sorteado e sem time, a cada
        ``vehicle_match.boss_every_s`` (0130); aguarda dump.
        """
        if self.boss_at is not None and now >= self.boss_at:
            self.boss_at = None
            row = self.templates.get("VehicleObjectTempInfos", BOSS_TEMPLATE)
            x, y = CENTER
            spawn = Node(next(self._ids), NODE_BOSS, x, y, hp=_int(row, "Hp"), name=(row or {}).get("TemplateName", ""),
                        hero=BOSS_TEMPLATE, resource=NPC_AVATAR, attack=_int(row, "Attack"),
                        defence=_int(row, "Defence"), dodge=_int(row, "Dodge"))  # fmt: skip
            self._add_node(spawn)
            self.boss_next = now + timedelta(seconds=self.rules["boss_every_s"])
        boss = self.boss()
        if boss is None:
            return
        skill = self.templates.get(
            "VehicleSkillTempInfos", _int(self.templates.get("VehicleObjectTempInfos", BOSS_TEMPLATE), "NormalSkill")
        )
        if self.strike is not None and now >= self.strike[0]:
            _, x, y = self.strike
            self.strike = None
            radius = _int(skill, "DamageCoverage")
            rsp = pb.VehicleAttackRspMsg(skillId=_int(skill, "TemplateId"), effectX=x, effectY=y,
                                         attackerId=boss.node_id, attackTyep=ATTACK_BY_NODE)  # fmt: skip
            for t in self.tanks.values():
                if t.alive and math.dist((t.x * TILE, t.y * TILE), (x * TILE, y * TILE)) < radius:
                    dmg = self._raw(boss.attack, _int(skill, "Power"), t.defence)
                    rsp.playerHurtDataList.add(
                        affecteId=t.player_id, value=self._hit_tank(None, t, dmg, now, dodge=True)
                    )
            self.all(S_ATTACK, rsp)
        if self.boss_next is not None and now >= self.boss_next and self.strike is None:
            self.boss_next = now + timedelta(seconds=self.rules["boss_every_s"])
            reach = _int(skill, "AttackRange") / TILE
            near = [t for t in self.tanks.values() if t.alive and _dist((t.x, t.y), (boss.x, boss.y)) <= reach]
            if near:
                aim = self.rnd.choice(near)
                self.strike = (now + BOSS_WARN, aim.x, aim.y)
                self.all(S_WARN, pb.VehicleAttackRspMsg(effectX=aim.x, effectY=aim.y))

    def _traps(self, now: datetime) -> None:
        """Armadilha (skill 7, 100 px de área): inimigo vivo dentro dela dispara 300 de dano em todos os inimigos da
        área. Vai como 4520 do dono, ``attackTyep`` 1 e skill 7: o ``VehicleBoxView`` não toca a explosão, o tanque
        dono sim (InjuryEffect 4 toca na hora, ``ShootAction``)."""
        for n in [n for n in self.nodes.values() if n.type == NODE_TRAP]:
            row = self.templates.get("VehicleSkillTempInfos", n.skill)
            radius = _int(row, "DamageCoverage")
            owner = self.tanks.get(n.owner)
            hit = [t for t in self.tanks.values()
                   if t.team != n.team and t.alive and _dist((t.x, t.y), (n.x, n.y)) * TILE < radius]  # fmt: skip
            if not hit:
                continue
            rsp = pb.VehicleAttackRspMsg(skillId=n.skill, effectX=n.x, effectY=n.y, attackerId=n.owner,
                                         attackTyep=ATTACK_BY_PLAYER)  # fmt: skip
            for t in hit:
                rsp.playerHurtDataList.add(
                    affecteId=t.player_id, value=self._hit_tank(owner, t, TRAP_DAMAGE, now, dodge=False)
                )
            self._remove_node(n)
            self.all(S_ATTACK, rsp)


class Arena:
    """Fila e partidas do processo. Um grupo (sozinho no 8608 ou a sala de veículo inteira no 5039) entra junto, no
    mesmo time."""

    def __init__(self) -> None:
        self.matches: list[Match] = []
        self.queue: list[list[int]] = []
        self.rewarded: dict[datetime, set[int]] = {}  # início da janela -> quem já recebeu o prêmio dela
        self.task: object | None = None  # o relógio das partidas (handlers/vehicle.py)

    def match_of(self, player_id: int) -> Match | None:
        return next((m for m in self.matches if player_id in m.seats), None)

    def queued(self, player_id: int) -> list[int] | None:
        return next((g for g in self.queue if player_id in g), None)

    def enqueue(self, group: list[int]) -> bool:
        if any(self.queued(p) is not None or self.match_of(p) is not None for p in group):
            return False
        self.queue.append(list(group))
        return True

    def dequeue(self, player_id: int) -> list[int] | None:
        group = self.queued(player_id)
        if group is not None:
            self.queue.remove(group)
        return group

    def place(
        self,
        templates: GameTemplates,
        window: tuple[datetime, datetime],
        now: datetime,
        deliver: Deliver,
        *,
        rnd: random.Random | None = None,
        tiles: TankMap | None = None,
        rules: Mapping[str, Any] | None = None,
    ) -> list[tuple[Match, list[int], int]]:
        """Encaixa a fila: primeiro nas partidas desta janela com lugar no time mais vazio; o resto abre uma partida
        nova quando dá um lado contra o outro (``min_players``). Os lugares ficam reservados (``Match.seats``)."""
        placed: list[tuple[Match, list[int], int]] = []
        for group in list(self.queue):
            for m in self.matches:
                if m.over or m.end != window[1]:
                    continue
                team = m.team_for(len(group))
                if team is not None:
                    m.seats.update(dict.fromkeys(group, team))
                    self.queue.remove(group)
                    placed.append((m, group, team))
                    break
        sides: dict[int, list[list[int]]] = {RED: [], BLUE: []}
        for group in self.queue:
            size = {t: sum(len(g) for g in sides[t]) for t in sides}
            team = min(sides, key=lambda t: size[t])
            if size[team] + len(group) <= TEAM_SIZE:
                sides[team].append(group)
        total = sum(len(g) for gs in sides.values() for g in gs)
        if sides[RED] and sides[BLUE] and total >= int((MATCH_RULES | dict(rules or {}))["min_players"]):
            m = Match(templates, now, window[1], deliver, rnd=rnd, tiles=tiles, rules=rules)
            self.matches.append(m)
            for team, groups in sides.items():
                for group in groups:
                    m.seats.update(dict.fromkeys(group, team))
                    self.queue.remove(group)
                    placed.append((m, group, team))
        return placed
