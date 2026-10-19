"""Cidade externa (mapa-múndi): posição do exército, grade visível e castelo que muda de lugar.

Regras vindas do cliente (`OuterCityController`, `WorldMapControler`, `WorldMapHelper`) e da captura
`transfer_kampi_sistemi.json` (5176 -> 140, 152, 105). O mapa 100000xxx do castelo é uma instância
de cada jogador (o próprio castelo, os 2 castelos-robô e as 4 minas do mapa 100); nos mapas 1 a 5,
compartilhados, aparecem os castelos dos outros jogadores (ver docs/cidade-externa.md). Exército andando
de outro jogador e terra selvagem fora das 4 minas não existem aqui. Minas em ``mines.py``, castelos-robô em
``robots.py`` e chefes do mapa em ``bosses.py``.
"""

from __future__ import annotations

import math

from ..domain.models import Castle, PlayerSnapshot
from ..protocol.messages import wartune_pb2 as pb
from ..templates.repository import GameTemplates

TILE = 20  # o cliente manda pixels (PosMoveMsg.routes); curPosX * 20 é o pixel do cliente
GRID = 50  # a grade pedida pelo cliente é "x_y" de 50 × 50 tiles (OuterCitySocketOutManager)
HOME_OFFSET = 2  # army_msg: o exército fica 2 tiles antes do castelo
# sem a linha AddAttck_Point (395 nos templates EN; language EN AttackAlertFrame.content "cost 395 Balens");
# 100 é só o saldo mínimo que o AttackAlertFrame confere antes de mandar o 9506
ATTACK_PRICE = 100
ENERGY_SAME_MAP = 100  # MapPhysicsCastle: energia para mudar de posição no mesmo mapa
ENERGY_OTHER_MAP = 200  # WorldMapControler: energia para mudar de mapa (captura: 500 -> 300)
BASE_MAP, INSTANCE_MAP = 100, 100_000  # mapas do castelo começam em 100000xxx (characters.GridCastlePlacement)


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


def army_soldiers(snap: PlayerSnapshot, templates: GameTemplates) -> tuple[list[dict[str, object]], int]:
    """As tropas do exército na luta da cidade externa (replay #718): duas pilhas (pos 3 e 9, livingId 1 e 2),
    vida da pilha = Live × soldados / 100. Devolve as pilhas e o template da tropa (0 sem tropa)."""
    soldiers: list[dict[str, object]] = []
    pawn = next((p for p in snap.pawns if p.army_count > 0), None)
    tpl = templates.get("PawnTempInfos", pawn.template_id) if pawn else None
    if pawn is not None and tpl is not None:
        # replay #718: [DefaultSkill, HighSkill] repetido 5 vezes (10,11 do Lancer)
        skills = [int(s) for s in (tpl["DefaultSkill"], tpl.get("HighSkill", "")) if s] * 5
        half = (pawn.army_count + 1) // 2
        for living, pos, count in ((1, 3, half), (2, 9, pawn.army_count - half)):
            if count <= 0:
                continue
            hp = max(1, int(tpl["Live"]) * count // 100)
            soldiers.append(
                {"livingId": living, "tempId": pawn.template_id, "type": 1, "side": 1, "pos": pos,
                 "initHp": hp, "hp": hp, "qteTime": 0, "castTime": 4000,
                 "skillId": skills}
            )  # fmt: skip
    return soldiers, pawn.template_id if soldiers and pawn else 0


def guard_battle(snap: PlayerSnapshot, templates: GameTemplates, guard: int) -> dict[str, object]:
    """Spec da luta contra um guarda no mapa 100 (replay #718, a mina): battleType 1, as tropas do exército
    (``army_soldiers``), o herói na 4 e o guarda na 5 com a vida de um soldado (Live / 100). Serve também
    ao castelo-robô (dedução: não há captura de luta com castelo; o guarda é o da mina do mesmo grau)."""
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
