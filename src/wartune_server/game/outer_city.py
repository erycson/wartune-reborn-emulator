"""Cidade externa (mapa-múndi): posição do exército, grade visível e castelo que muda de lugar.

Regras vindas do cliente (`OuterCityController`, `WorldMapControler`, `WorldMapHelper`) e da captura
`transfer_kampi_sistemi.json` (só turco: 5176 -> 140, 152, 105; a inglesa não muda o castelo de mapa).
O mapa 100000xxx do castelo é uma instância
de cada jogador (o próprio castelo, os 2 castelos-robô e as 4 minas do mapa 100); nos mapas 1 a 5,
compartilhados, aparecem os castelos dos outros jogadores e as minas do mundo (ver docs/cidade-externa.md).
Exército andando de outro jogador não existe aqui. Minas em ``mines.py``, castelos-robô em
``robots.py`` e chefes do mapa em ``bosses.py``.
"""

from __future__ import annotations

import math
from xml.sax.saxutils import quoteattr

from ..domain.models import Castle, Pawn, PlayerSnapshot
from ..protocol.messages import wartune_pb2 as pb
from ..templates.repository import GameTemplates, Row
from . import rules
from .arena import npc_hero

TILE = 20  # o cliente manda pixels (PosMoveMsg.routes); curPosX * 20 é o pixel do cliente
GRID = 50  # a grade pedida pelo cliente é "x_y" de 50 × 50 tiles (OuterCitySocketOutManager)
HOME_OFFSET = 2  # army_msg: o exército fica 2 tiles antes do castelo
# sem a linha AddAttck_Point (395 nos templates EN; language EN AttackAlertFrame.content "cost 395 Balens");
# o AttackAlertFrame inglês só confere 98 de saldo antes de mandar o 9506
ATTACK_PRICE = 100
ENERGY_SAME_MAP = 100  # MapPhysicsCastle: energia para mudar de posição no mesmo mapa
ENERGY_OTHER_MAP = 200  # WorldMapControler: energia para mudar de mapa (só turco: transfer, 500 -> 300)
BASE_MAP, INSTANCE_MAP = 100, 100_000  # mapas do castelo começam em 100000xxx (characters.GridCastlePlacement)
# luta com o castelo-robô (inglês #1657): battleType 4 no MapInfos 993 "Plunder City"; o 4103 vem com battleScene 6
ROBOT_BATTLE_TYPE, ROBOT_MAP, ROBOT_SCENE = 4, 993, 6
ROBOT_HERO_BASE = 11000  # GameHeroTemp 11001-11030 "Warrior (M)" com Grades = id - 11000 (11008 no robô de grau 8)
ROBOT_HERO_TOP = 30
ROBOT_HERO_LIVING, ROBOT_PAWN_LIVINGS = 6, ((4, 1), (5, 7))  # (livingId, pos) das 2 pilhas do robô
# ponytail: 2 pilhas de 10102 com 282 de vida cada, as do robô de grau 8 (o único do catálogo); outro grau sem captura
ROBOT_PAWN, ROBOT_PAWN_HP = 10102, 282


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
    """O mapa do castelo (100000xxx) é uma cópia do modelo 100 (Twilight Sands), como no OuterCityController."""
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

    ponytail: o oficial escolhe um ponto livre; usamos o centro (só turco: transfer, mapa 2 em 2191,1952, perto do
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


FRONT_HERO_POS = 4  # o herói na fileira da frente, no meio (inglês #727); a formação o leva para a 6


def column(fight_pos: int) -> int:
    """Fileira da formação (8276: 1 frente, 3 trás; outro valor = o padrão de cada um)."""
    return fight_pos if fight_pos in (1, 3) else 0


def hero_pos(fight_pos: int) -> int:
    """(visto) o herói fica no meio da fileira dele: 4 com ``fightPos`` 1 (tutorial_en #727) e 6 com 3
    (oficial_20261023-171155-1, todas as 25 lutas)."""
    return 3 + (column(fight_pos) or 1)


def army_soldiers(snap: PlayerSnapshot, templates: GameTemplates) -> tuple[list[dict[str, object]], int]:
    """As tropas do exército na luta (inglês #727): duas pilhas (livingId 1 e 2) em cima e embaixo da fileira da
    tropa: pos 3 e 9 com ``fightPos`` 3 (tutorial_en #727), 1 e 7 com 1 (oficial_20261023-171155-1). A vida total
    Live × soldados / 100 se divide arredondando para cima na primeira (visto tutorial_en: 523 -> 262/261,
    637 -> 319/318). Devolve as pilhas e o template da tropa (0 sem tropa)."""
    soldiers: list[dict[str, object]] = []
    pawn = next((p for p in snap.pawns if p.army_count > 0), None)
    tpl = templates.get("PawnTempInfos", pawn.template_id) if pawn else None
    if pawn is not None and tpl is not None:
        # inglês #727: [DefaultSkill, HighSkill] repetido 5 vezes (10,11 do Lancer)
        skills = [int(s) for s in (tpl["DefaultSkill"], tpl.get("HighSkill", "")) if s] * 5
        tech = rules.troop_tech(snap, templates)  # (dedução) as tecnologias de tropa valem na luta, como no pawnLive
        stats = {k: int(tpl.get(col) or 0) + tech.get(col, 0) for k, col in TROOP_STATS.items()}
        total = max(1, troop_live(snap, templates, tpl) * pawn.army_count // 100)
        first = (total + 1) // 2 if pawn.army_count > 1 else total
        row = column(pawn.fight_pos) or 3
        for living, pos, hp in ((1, row, first), (2, row + 6, total - first)):
            if hp <= 0:
                continue
            soldiers.append(
                {"livingId": living, "tempId": pawn.template_id, "type": 1, "side": 1, "pos": pos,
                 "initHp": hp, "hp": hp, "qteTime": 0, "castTime": 4000,
                 "skillId": skills, "stats": stats}
            )  # fmt: skip
    return soldiers, pawn.template_id if soldiers and pawn else 0


# atributos da spec de batalha (``battle.STATS``) -> coluna do PawnTempInfos
TROOP_STATS = {"PhyAttack": "Attack", "PhyDefence": "Defence", "MagicAttack": "MagicAttack",
               "MagicDefence": "MagicDefence", "ForceHit": "ForceHit", "Parry": "Parry"}  # fmt: skip


def troop_live(snap: PlayerSnapshot, templates: GameTemplates, tpl: Row) -> int:
    """Vida por 100 soldados com a tecnologia de tropa (Troop HP)."""
    return int(tpl["Live"]) + rules.troop_tech(snap, templates).get("Live", 0)


def lose_troops(
    snap: PlayerSnapshot, templates: GameTemplates, troops: tuple[int, int] | None
) -> tuple[Pawn, int] | None:
    """Tropas que morreram na luta saem do exército: ficam ``ceil(vida que sobrou × 100 / Live)`` (visto tutorial_en
    #1466: 162 Lancers, Live 323, 238 de vida no fim -> 74 vivos, a reserva caiu 88; #1657: as 172 morreram).
    Devolve a tropa e quantas morreram, ou ``None`` sem perda."""
    pawn = next((p for p in snap.pawns if p.army_count > 0), None)
    tpl = templates.get("PawnTempInfos", pawn.template_id) if pawn else None
    if troops is None or pawn is None or tpl is None or troops[0] >= troops[1]:
        return None
    alive = min(pawn.army_count, math.ceil(troops[0] * 100 / troop_live(snap, templates, tpl)))
    lost = pawn.army_count - alive
    if lost <= 0:
        return None
    pawn.army_count = alive
    return pawn, lost


def refill(pawn: Pawn, lost: int) -> None:
    """O exército se completa com a reserva do castelo depois da luta (visto #1511: 738 -> 650 com o exército em
    162 de novo; #1760 -> #1764: 0 -> 172 e a reserva 640 -> 468). Sem reserva bastante, fica menor."""
    take = min(lost, pawn.castle_count)
    pawn.castle_count -= take
    pawn.army_count += take


def guard_battle(snap: PlayerSnapshot, templates: GameTemplates, guard: int) -> dict[str, object]:
    """Spec da luta contra um guarda no mapa 100 (inglês #727, a mina): battleType 1, as tropas do exército
    (``army_soldiers``), o herói na 4 e o guarda na 5 com a vida de um soldado (Live / 100)."""
    soldiers, pawn_tpl = army_soldiers(snap, templates)
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
        "player": {"livingId": 3, "pos": 4, "pawnTempId": pawn_tpl},
    }


def holder_battle(
    snap: PlayerSnapshot, templates: GameTemplates, hero: dict[str, object], map_id: int
) -> dict[str, object]:
    """Luta pela mina do mundo que outro jogador ocupa (o cliente mostra "Attack" nela: ``PhysicsMenu``).
    TODO(inventado): nenhuma captura; a da mina livre (battleType 1, battleScene 4, oficial_20261023-171155-1 #3041)
    com a cópia do herói de quem ocupa (``arena.copy_hero``) no lugar do guarda (livingId 4, pos 5), em pvp."""
    soldiers, pawn_tpl = army_soldiers(snap, templates)
    return {
        "battleType": 1,
        "mapTempId": map_id,
        "attackModel": 2,
        "battleScene": 4,
        "pvp": True,
        "soldiers": soldiers,
        "heroes": [hero | {"livingId": 4, "pos": 5}],
        "player": {"livingId": 3, "pos": 4, "pawnTempId": pawn_tpl},
    }


def robot_battle(
    snap: PlayerSnapshot,
    templates: GameTemplates,
    grade: int,
    name: str,
    pawn_id: int = ROBOT_PAWN,
    pawn_hp: int = ROBOT_PAWN_HP,
) -> dict[str, object]:
    """Spec da luta com o castelo-robô (inglês #1657): as tropas e o herói do jogador como na mina; do lado 2 o
    herói ``11000 + grau`` (type 2, nome do robô, skills do SkillScript, vida Live) na 6 e 2 pilhas de 10102.
    O castelo NPC do mundo (``npc_castles``) troca as pilhas. TODO(inventado): acima do grau 30 (o último
    GameHeroTemp 110xx) o herói é o 11030 com a vida × grau / 30."""
    soldiers, pawn_tpl = army_soldiers(snap, templates)
    pawn = templates.get("PawnTempInfos", pawn_id) or {}
    skills = [int(s) for s in (pawn.get("DefaultSkill", ""), pawn.get("HighSkill", "")) if s] * 5
    for living, pos in ROBOT_PAWN_LIVINGS:
        soldiers.append(
            {"livingId": living, "tempId": pawn_id, "type": 1, "side": 2, "pos": pos,
             "initHp": pawn_hp, "hp": pawn_hp, "qteTime": 0, "castTime": 4000, "skillId": skills}
        )  # fmt: skip
    hero_id = ROBOT_HERO_BASE + min(grade, ROBOT_HERO_TOP)
    row = templates.get("GameHeroTemp", hero_id) or {}
    hp = max(1, int(row.get("Live") or 1) * max(grade, ROBOT_HERO_TOP) // ROBOT_HERO_TOP)
    hero = npc_hero(
        livingId=ROBOT_HERO_LIVING, tempId=hero_id, nickName=name, grade=grade, maxHp=hp, initHp=hp, hp=hp,
        skillId=[int(x) for x in str(row.get("SkillScript", "")).split(",") if x],
    )  # fmt: skip
    return {
        "battleType": ROBOT_BATTLE_TYPE,
        "mapTempId": ROBOT_MAP,
        "attackModel": 2,
        "battleScene": ROBOT_SCENE,
        "soldiers": soldiers,
        "heroes": [hero],
        "player": {"livingId": 3, "pos": 4, "pawnTempId": pawn_tpl},
    }


def rival_castle_msg(castle: Castle, name: str) -> pb.BaseCastleMsg:
    """Castelo de outro jogador num mapa compartilhado (o do próprio jogador é ``builders.login.castle_msg``).
    (dedução) os mesmos campos do castelo próprio no 4129 (inglês #532); nenhuma captura tem castelo de outro."""
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


def report_contents(info: dict[str, object], me: dict[str, object], he: dict[str, object]) -> str:
    """``Contents`` da carta de relatório de batalha (``MailType`` 3). (cliente) ``BattleReportHelp.covertToBattleInfo``
    lê o XML; (visto) as cartas 11554/11564/11569 do ``maillist`` de oficial_20261023-171155-1: raiz ``infos``,
    ``info`` (type 1, camp 1 = atacante, result 1 = vitória de quem lê, playerName e siteName = o nome do castelo,
    pos "x,y", mapId, time) e ``me``/``he`` (heroId, site1Name/site1Count e site2Name/site2Count vazios, fight, grade,
    gold, crystal), nessa ordem."""

    def attrs(d: dict[str, object]) -> str:
        return " ".join(f"{k}={quoteattr(str(v))}" for k, v in d.items())

    return f"<infos><info {attrs(info)} /><me {attrs(me)} /><he {attrs(he)} /></infos>"
