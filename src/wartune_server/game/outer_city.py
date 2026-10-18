"""Cidade externa (mapa-múndi): posição do exército, grade visível e castelo que muda de lugar.

Regras vindas do cliente (`OuterCityController`, `WorldMapControler`, `WorldMapHelper`) e da captura
`transfer_kampi_sistemi.json` (5176 -> 140, 152, 105). O mapa 100000xxx do castelo é uma instância
de cada jogador (o próprio castelo, os 2 castelos-robô e as 4 minas do mapa 100); nos mapas 1 a 5,
compartilhados, aparecem os castelos dos outros jogadores (ver docs/cidade-externa.md). Exército andando
de outro jogador e terra selvagem fora das 4 minas não existem aqui.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from ..domain.models import Castle, PlayerSnapshot, WildLand
from ..protocol.messages import wartune_pb2 as pb
from ..templates.repository import GameTemplates
from . import worldboss

TILE = 20  # o cliente manda pixels (PosMoveMsg.routes); curPosX * 20 é o pixel do cliente
GRID = 50  # a grade pedida pelo cliente é "x_y" de 50 × 50 tiles (OuterCitySocketOutManager)
HOME_OFFSET = 2  # army_msg: o exército fica 2 tiles antes do castelo
ATTACK_PRICE = 100  # ConfigInfos AddAttck_Point: diamantes por ataque extra (AttackAlertFrame)
ENERGY_SAME_MAP = 100  # MapPhysicsCastle: energia para mudar de posição no mesmo mapa
ENERGY_OTHER_MAP = 200  # WorldMapControler: energia para mudar de mapa (captura: 500 -> 300)
BASE_MAP, INSTANCE_MAP = 100, 100_000  # mapas do castelo começam em 100000xxx (characters.GridCastlePlacement)
DATE = "%Y-%m-%d %H:%M:%S"


def home(castle: Castle) -> tuple[int, int, int]:
    """(mapa, x, y) do exército parado no castelo."""
    return castle.map_id, castle.pos_x - HOME_OFFSET, castle.pos_y - HOME_OFFSET


def position(castle: Castle, moved: tuple[int, int, int] | None) -> tuple[int, int, int]:
    """Onde está o exército: o último ponto andado nesta sessão, ou o castelo."""
    return moved if moved is not None and moved[0] == castle.map_id else home(castle)


def grid_of(x: int, y: int) -> str:
    return f"{x // GRID}_{y // GRID}"


def map_allowed(map_id: int, grade: int) -> bool:
    """WorldMapHelper.chcekMapId: mapas 1 a 5 têm nível mínimo 11, 21, 31, 41 e 51; o -1 não abre."""
    if map_id == -1:
        return False
    needs = {1: 11, 2: 21, 3: 31, 4: 41, 5: 51}.get(map_id)
    return needs is None or grade >= needs


def template_of(map_id: int) -> int:
    """O mapa do castelo (100000xxx) é uma cópia do modelo 100 (Loş Sahil), como no OuterCityController."""
    return BASE_MAP if map_id >= INSTANCE_MAP else map_id


def map_size(templates: GameTemplates, map_id: int) -> tuple[int, int] | None:
    """Tamanho do mapa em tiles (MapInfos.Width/Height estão em pixels)."""
    row = templates.get("MapInfos", template_of(map_id), key="Id")
    if row is None:
        return None
    return int(row["Width"]) // TILE, int(row["Height"]) // TILE


def inside(templates: GameTemplates, map_id: int, x: int, y: int) -> bool:
    size = map_size(templates, map_id)
    return size is not None and 0 <= x < size[0] and 0 <= y < size[1]


def centre(templates: GameTemplates, map_id: int) -> tuple[int, int]:
    """Onde o castelo cai ao chegar num mapa novo.

    ponytail: o oficial escolhe um ponto livre; usamos o centro (captura: mapa 2 em 2191,1952, perto do
    centro de 4000×4000 tiles), então dois castelos que mudam para o mesmo mapa ficam no mesmo ponto até um
    deles se mover (5176 no mesmo mapa). Subir: procurar ponto livre com ``CastleRepository.on_map``.
    """
    size = map_size(templates, map_id) or (0, 0)
    return size[0] // 2, size[1] // 2


def energy_diamonds(castle: Castle, top: int, need: int) -> int:
    """Diamantes para completar a energia de teleporte (``ceil((máximo - atual) / 5)``, como o cliente).
    Zero quando já basta para ``need``."""
    if castle.energy >= need:
        return 0
    return math.ceil((top - castle.energy) / 5)


# -- minas de ouro ---------------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class Mine:
    """Mina de ouro do mapa 100 (``WildLandMsg`` type 20). O guarda é um soldado só (``ownPawns`` 1)."""

    id: int
    x: int
    y: int


# As 4 minas do mapa 100 nas capturas (replay #706, cevre #11): mesmos ids e posições para contas
# diferentes, então são do modelo do mapa. Mas cada conta tem a sua cópia: a instância (100000313 no
# replay, 100000714 na cevre), os robôs, os ids do armyPawn e o createDate mudam de uma para a outra.
# Ocupação de outro jogador não aparece nem bloqueia. O guia do tutorial (m8 NewbieBaseActionMediator,
# alvo 80) procura as duas primeiras pelos pixels (320,680) e (720,680).
MINES = (Mine(853876, 16, 34), Mine(853877, 36, 34), Mine(853874, 71, 54), Mine(853875, 54, 64))
MINE_TYPE, MINE_SON_TYPE = 20, 2006  # WildLandMsg.type; MapPhysicsTempInfos.SonType (missão 60, Para1)
MINE_FREE, MINE_FIGHTING = 1, 4  # WildLandMsg.state
MINE_CAPACITY = 324  # fightCapaity da mina livre nas capturas
# Refresh: RefreshTime 43200 s em todas as minas (MapPhysicsTempInfos). O ciclo é do jogador
# (``Castle.mines_at``): o createDate vem no fuso do jogo (UTC+3) e cai na entrada da conta, não numa
# hora do mundo. Replay: 12:19:54 = 09:19:54 UTC, 1 s antes do primeiro pacote; cevre: 19:48:57 =
# 16:48:57 UTC, 73 s antes do signDate 19:50:10 do mesmo asiesat (login.json), e o relogin das 17:05
# UTC não mudou o createDate. As duas fases ficam 7 h 29 min distantes: não há hora do mundo.
# ponytail: (dedução) o ciclo vencido só renova no próximo acerto de ouro, login, 8201 ou 5160 e começa nessa hora;
# quem fica online pode ver o oficial renovar na hora certa (sem captura de um refresh ao vivo).
MINE_PERIOD = timedelta(hours=12)
# (dedução) nível sorteado a cada refresh: as duas capturas têm 8, 9 e 10 (replay: 8, 9, 10, 10; cevre:
# 9, 9, 10, 10). Template = MapPhysicsTempInfos (Grades = nível, Property4 = ouro por hora).
MINE_TEMPLATE = {8: 200408, 9: 200409, 10: 200410}
# guarda por nível: visto 6504 no nível 8 (replay) e 6505 nos níveis 9 e 10 (replay e cevre)
MINE_GUARD = {8: 6504, 9: 6505, 10: 6505}


def mine_at(map_id: int, x: int, y: int) -> Mine | None:
    if template_of(map_id) != BASE_MAP:
        return None
    return next((m for m in MINES if (m.x, m.y) == (x, y)), None)


def mines_in(grids: set[str]) -> list[Mine]:
    return [m for m in MINES if grid_of(m.x, m.y) in grids]


def cycle_start(snap: PlayerSnapshot) -> datetime:
    """Começo do ciclo de minas do jogador. Castelo de antes da migração 0018 (``mines_at`` vazio):
    a ocupação mais velha, para a mina dele não vencer na hora (o refresh do login grava o valor)."""
    castle = snap.castle
    assert castle is not None
    if castle.mines_at is not None:
        return castle.mines_at
    return min((w.occupied_at for w in snap.wild_lands), default=datetime.fromtimestamp(0, UTC))


def cycle_end(snap: PlayerSnapshot) -> datetime:
    return cycle_start(snap) + MINE_PERIOD


def game_date(at: datetime) -> str:
    """Data como o oficial manda (createDate): no fuso do jogo."""
    return at.astimezone(worldboss.GAME_TZ).strftime(DATE)


def draw(snap: PlayerSnapshot, mine: Mine) -> tuple[int, int]:
    """(template, guarda) da mina no ciclo atual do jogador. A semente é o jogador, a mina e o começo do
    ciclo: o sorteio fica o mesmo até o refresh e muda a cada um."""
    seed = f"{snap.character.id}:{mine.id}:{int(cycle_start(snap).timestamp())}"
    level = random.Random(seed).choice(tuple(MINE_TEMPLATE))
    return MINE_TEMPLATE[level], MINE_GUARD[level]


def occupied(snap: PlayerSnapshot, mine: Mine) -> WildLand | None:
    """Ocupação do jogador no ciclo atual. A linha de um ciclo vencido fica no banco e é reaproveitada
    por ``occupy`` (unique personagem + mina)."""
    start = cycle_start(snap)
    return next((w for w in snap.wild_lands if w.wild_id == mine.id and w.occupied_at >= start), None)


def mine_msg(snap: PlayerSnapshot, templates: GameTemplates, mine: Mine, state: int, capacity: int) -> pb.WildLandMsg:
    """Como no 4129 e no 140 do oficial: a livre não tem ``occupyPlayerName``; a ocupada leva o nome e o
    poder do jogador em ``fightCapaity``."""
    template, guard = draw(snap, mine)
    row = templates.get("MapPhysicsTempInfos", template) or {}
    msg = pb.WildLandMsg(
        id=mine.id,
        mapId=BASE_MAP,
        posX=mine.x,
        posY=mine.y,
        templateId=template,
        type=MINE_TYPE,
        occupyPlayerId=0,
        level=int(row.get("Grades", 0)),
        refreshTime=int(row.get("RefreshTime", 0)) * 1000,
        state=state,
        createDate=game_date(cycle_start(snap)),
        fightCapaity=MINE_CAPACITY,
        bossType=0,
        size=0,
    )
    if occupied(snap, mine) is not None:
        msg.occupyPlayerId, msg.occupyPlayerName = snap.character.id or 0, snap.character.nickname or ""
        msg.fightCapaity = capacity
    msg.armyPawn.add(id=mine.id, armyId=mine.id, tempateId=guard, ownPawns=1)
    return msg


def mine_yield(snap: PlayerSnapshot, templates: GameTemplates) -> list[pb.WildYieldMsg]:
    """152: uma linha por mina ocupada (replay #743, #794), com o sorteio do ciclo atual."""
    out = []
    for mine in MINES:
        if occupied(snap, mine) is None:
            continue
        row = templates.get("MapPhysicsTempInfos", draw(snap, mine)[0]) or {}
        grade = int(row.get("Grades", 0))
        out.append(
            pb.WildYieldMsg(
                wildPoxName=f"({mine.x},{mine.y})",
                wildPox=f"{mine.x},{mine.y}",
                wildGrade=grade,
                wildName=f"{row.get('MapPhysicsTempName', '')} {grade} seviye",
                wildYield=int(row.get("Property4", 0)),
                wildRefreshTime=int(row.get("RefreshTime", 0)),
                mapId=BASE_MAP,
                createTime=game_date(cycle_start(snap)),
            )
        )
    return out


def mine_gold(snap: PlayerSnapshot, templates: GameTemplates) -> int:
    """Ouro por hora das minas ocupadas (replay: o goldYield do 109 vai de 280 para 960 com a 1ª)."""
    return sum(y.wildYield for y in mine_yield(snap, templates))


def guard_battle(snap: PlayerSnapshot, templates: GameTemplates, guard: int) -> dict[str, object]:
    """Spec da luta contra um guarda no mapa 100 (replay #718, a mina): battleType 1, as tropas do exército em
    duas pilhas (pos 3 e 9), o herói na 4 e o guarda na 5. Vida da pilha = Live × soldados / 100. Serve também
    ao castelo-robô (dedução: não há captura de luta com castelo; o guarda é o da mina do mesmo grau)."""
    soldiers: list[dict[str, object]] = []
    pawn = next((p for p in snap.pawns if p.army_count > 0), None)
    tpl = templates.get("PawnTempInfos", pawn.template_id) if pawn else None
    if pawn is not None and tpl is not None:
        half = (pawn.army_count + 1) // 2
        for living, pos, count in ((1, 3, half), (2, 9, pawn.army_count - half)):
            if count <= 0:
                continue
            hp = max(1, int(tpl["Live"]) * count // 100)
            soldiers.append(
                {"livingId": living, "tempId": pawn.template_id, "type": 1, "side": 1, "pos": pos,
                 "initHp": hp, "hp": hp, "qteTime": 0, "castTime": 4000,
                 "skillId": [int(tpl["DefaultSkill"])]}
            )  # fmt: skip
    guard_row = templates.get("PawnTempInfos", guard) or {}
    hp = max(1, int(guard_row.get("Live", 100)) // 100)
    soldiers.append(
        {"livingId": 4, "tempId": guard, "type": 1, "side": 2, "pos": 5,
         "initHp": hp, "hp": hp, "qteTime": 0, "castTime": 6000}
    )  # fmt: skip
    return {
        "battleType": 1,
        "mapTempId": BASE_MAP,
        "attackModel": 2,
        "battleScene": 4,
        "soldiers": soldiers,
        "heroes": [],
        "player": {"livingId": 3, "pos": 4},
    }


# -- castelos-robô (missões 100, 411 e 765) -----------------------------------------------------------

# Dois castelos de robô no mapa do castelo, nos mesmos tiles em todas as contas: 765958 em (44,22) e 765957
# em (59,56) (visto: replay #706 e cevre #11). O guia da missão 100 procura o de (44,22) (m8, alvo 80_3); sem
# ele a tela escurece, como na missão 60. Grau 8 (visto em 3 dos 4 castelos; o quarto tem grau 7). Id e nome
# mudam de uma conta para outra (visto), então o nome sai da conta. Não tem estado: o robô está sempre lá.
ROBOT_CASTLES = ((765958, 44, 22), (765957, 59, 56))
ROBOT_GRADE = 8
ROBOT_USER_BASE = 1_300_009_000  # (dedução) faixa 13000xxxxx dos robôs, acima das ids da arena (base + 1 a 1400+)
# (visto) os enfeites e nomes das capturas: ♣Chloe♣, ♫Elizabeth♫, ►Abigail◄
ROBOT_NAMES = (("♣", "♣", "Chloe"), ("♫", "♫", "Elizabeth"), ("►", "◄", "Abigail"))


def _in_own_instance(snap: PlayerSnapshot, map_id: int) -> bool:
    """Só na instância do próprio castelo, a mesma regra das minas (``template_of`` == modelo 100): num mapa
    compartilhado (1 a 5) os robôs não aparecem nem lutam."""
    return snap.castle is not None and map_id == snap.castle.map_id and template_of(map_id) == BASE_MAP


def robot_at(snap: PlayerSnapshot, map_id: int, x: int, y: int) -> int | None:
    """Índice do castelo-robô no tile pedido, na instância do próprio castelo."""
    if not _in_own_instance(snap, map_id):
        return None
    return next((i for i, (_, rx, ry) in enumerate(ROBOT_CASTLES) if (rx, ry) == (x, y)), None)


def robots_in(snap: PlayerSnapshot, map_id: int, grids: set[str]) -> list[int]:
    """Robôs das grades pedidas, na instância do próprio castelo (4129 do 8201)."""
    if not _in_own_instance(snap, map_id):
        return []
    return [i for i, (_, x, y) in enumerate(ROBOT_CASTLES) if grid_of(x, y) in grids]


def robot_name(char_id: int, index: int) -> str:
    """Nome do robô nesta conta. Os dois robôs da conta tiram nomes distintos da lista, sem repetir (dedução).
    ponytail: a captura tem só 3 nomes (visto); ampliar ROBOT_NAMES se houver mais robôs."""
    left, right, name = random.Random(f"robo:{char_id}").sample(ROBOT_NAMES, len(ROBOT_CASTLES))[index]
    return f"{left}{name}{right}"


def robot_castle_msg(snap: PlayerSnapshot, index: int) -> pb.BaseCastleMsg:
    """Castelo-robô como no 4129 do oficial (cevre #11): tipo 1, estado 1, sem liga e sem tempo de defesa."""
    assert snap.castle is not None
    castle_id, x, y = ROBOT_CASTLES[index]
    name = robot_name(snap.character.id or 0, index)
    return pb.BaseCastleMsg(
        id=castle_id, mapId=snap.castle.map_id, posX=x, posY=y, type=1,
        occupyPlayerId=ROBOT_USER_BASE + index, occupyPlayerName=name, occupyLeagueName="",
        state=1, defenceLefttime=0, castleName=name, grade=ROBOT_GRADE, vipCastleView=0, vipType=0,
    )  # fmt: skip


def occupy(snap: PlayerSnapshot, mine: Mine, now: datetime) -> WildLand:
    land = next((w for w in snap.wild_lands if w.wild_id == mine.id), None)
    if land is None:
        land = WildLand(snap.character.id or 0, mine.id, now)
        snap.wild_lands.append(land)
    land.occupied_at = now
    return land


def rival_castle_msg(castle: Castle, name: str) -> pb.BaseCastleMsg:
    """Castelo de outro jogador num mapa compartilhado (o do próprio jogador é ``builders.login.castle_msg``).
    (dedução) os mesmos campos do castelo próprio na transfer #14; a captura não tem castelo de outro jogador."""
    return pb.BaseCastleMsg(
        id=castle.id or 0,
        mapId=castle.map_id,
        posX=castle.pos_x,
        posY=castle.pos_y,
        type=1,
        occupyPlayerId=castle.character_id,
        occupyPlayerName=name,
        state=castle.state,
        castleName=castle.name,
        leftEnergy=castle.energy,
        grade=castle.grade,
    )


# Chefes do mapa (9525 -> 4938, painel "Current map BOSS info" da cidade externa).
# Relógio (visto): transfer #8/#10 (mapa 2, 4828 s às 17:39:31 UTC) e cevre #3/#9/#43/#44 (instância do
# castelo, 5775 s às 17:23:44 UTC) caem no mesmo instante, 2026-05-21 19:00:00 UTC (22:00 no fuso do jogo),
# em mapas diferentes. (dedução) é um relógio do mundo de 2 h nas horas pares do fuso do jogo: RefreshTime
# 7200 nos chefes (MapPhysicsTempInfos MasterType 21). As duas capturas são da mesma conta.
BOSS_PERIOD = 7200
# Lista (visto): o bosslist do mapa 2 na transfer, como (template, tile x, tile y). O template saiu do nome e
# do grau no tempinfos turco da captura (Çılgın Garnett 20 = 210106, Ateş Ruhu 70 = 210124, Işık Ruhu 80 =
# 210129, Rüzgar Ruhu 60 = 210120); o nome vai do template atual. x e y em tiles: o radar do cliente faz
# x * 20 (OuterCityBossInfoView) e o mapa 2 tem 4000 tiles. A instância do castelo vem vazia (cevre).
# ponytail: mapas 1, 3, 4 e 5 sem lista (precisa de captura); a lista não muda no refresh (sem captura de
# dois ciclos). O 4129 do mapa 2 (transfer #14) traz outro chefe (210127, bossType 2) fora do bosslist: o
# painel não é a lista inteira dos chefes do mapa.
MAP_BOSSES: dict[int, tuple[tuple[int, int, int], ...]] = {
    2: ((210106, 1540, 3323), (210124, 1239, 2870), (210129, 739, 388), (210129, 2164, 2112), (210120, 1865, 527)),
}
BOSS_ALIVE = 1  # BossMsg.type visto; 0 o cliente pinta como morto e esconde o radar


def boss_left(now: datetime) -> int:
    """Segundos até o próximo refresh dos chefes. Nunca 0: com 0 o cliente (``coolDownBossUpdate``) pede
    o 9525 de novo, e a cada segundo se a resposta voltar 0."""
    local = now.astimezone(worldboss.GAME_TZ)
    into = (local - local.replace(hour=0, minute=0, second=0, microsecond=0)).total_seconds() % BOSS_PERIOD
    return max(1, int(BOSS_PERIOD - into))


def boss_msg(templates: GameTemplates, map_id: int, now: datetime) -> pb.MapBossMsg:
    """4938. ``count1`` a ``count3`` (monstros, elites e chefe do dia) ficam 0: não há monstro do mapa
    nem luta contra chefe que conte. Névoa (``leftFogTime``) sem captura: 0, como nas duas."""
    bosses = []
    for template, x, y in MAP_BOSSES.get(map_id, ()):
        row = templates.get("MapPhysicsTempInfos", template) or {}
        name, grade = row.get("MapPhysicsTempName", ""), int(row.get("Grades", 0))
        bosses.append(pb.BossMsg(bossName=name, grade=grade, type=BOSS_ALIVE, x=x, y=y))
    return pb.MapBossMsg(count1=0, count2=0, count3=0, bosslist=bosses, leftBossTime=boss_left(now), leftFogTime=0)
