"""Forgotten Catacombs (campanha 8001): estado da torre e os andares gerados dos templates.

Fontes (docs/salas-campanha.md): (só turco: yeralti_labirenti_ve_ilk_mob, labirent_sandik_toplama_odulu) os 4205, a
varredura do andar 1, a entrada no 8002, a luta e o portal para o 8003; (cliente) ``MazeFrame``,
``MazeMopupPrepareFrame``, ``MazeMopupIngFrame``, ``PosType`` (40 início, 42 monstro, 62 portal).

Andar ``k`` = mapa ``8000 + k`` (``MapInfos`` 8001-8100) com o monstro de TemplateId ``7000 + k``. Os andares 1 a 28
foram vistos nas capturas e estão em ``content/maze_floors.json`` (nós, monstro, poder de luta, baús); o resto é
regra deduzida. Os nós de cada andar (127): o início ``mapa*100+1``, o monstro ``+2`` (``param3`` ele mesmo, ``param4``
o portal), o baú ``+3`` (só a cada 5 andares, visível) e o portal ``+4`` (state 16 até o monstro cair, ``param1`` o
próximo mapa). Nos andares de chefe (5, 10, ...) o monstro tem ``heroTempId`` = ``7000 + k``.

Estado em ``EventState`` ``maze`` (``text`` JSON). Regras em ``game_settings.maze`` (migração 0087).
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime
from functools import lru_cache
from importlib import resources
from typing import Any

from ..domain import gameday
from ..domain.models import PlayerSnapshot
from ..protocol.messages import wartune_pb2 as pb
from ..templates.repository import GameTemplates
from . import events as ev

KEY = "maze"
SETTING = "maze"
CAMPAIGN = 8001  # Forgotten Catacombs (Campaigns Types 4)
SECOND = 8101  # Tormented Necropolis: "Requires passage through Level 100 of the Forgotten Catacombs."
FIRST_MAP = 8000  # andar k = mapa 8000 + k
MONSTER_BASE = 7000  # monstro do andar k = TemplateId 7000 + k
START, MONSTER, PORTAL, CHEST = 1, 2, 4, 3  # campDataId = mapa * 100 + isto
# (visto, só turco) masterType/sonType/estado dos nós; (cliente) PosType: 40 COPY_START, 42 COPY_NPC, 62 COPY_MAP_SEND
NODE_START, NODE_MONSTER, NODE_SEND, NODE_HANDLER = 40, 42, 62, 61
HIDDEN_PORTAL = 16  # (visto) o portal até o monstro cair; o 128 depois da vitória leva 1
FOG_ROWS, FOG_COLS = 18, 14  # (visto) 130 do 8003: tudo visível
# (visto) layouts por faixa de andar, nós dos andares 1-25 e baús dos chefes vistos (5, 10, 15, 20)
_SEEN: dict[str, Any] = json.loads(
    resources.files("wartune_server.content").joinpath("maze_floors.json").read_text(encoding="utf-8")
)
DEFAULT: dict[str, Any] = {
    "floors": 100,  # MapInfos 8001-8100 e os monstros 7001-7100
    # (visto) 4205 totalGp = 200 * k * (k + 1) depois de vencer o andar k (400, 1200, ... 76000, 84000, 120000)
    "gp_per_floor": 400,
    "free_enter": 1,  # (visto, só turco) freeEnterCount 1, maxEnterCount 1 em todos os 4205
    "max_enter": 1,
    # (visto, 4103 de 24/10 #12181 a #13269) nenhuma vitória dos andares 1-15 deu item de monstro, só EXP (gpBonus).
    # Os andares 21 e 22 têm loot depois do 4103 (25/10 #10000-#10421), mas não dá para atribuir a um monstro:
    # TODO(inventado) nada além disso; o Minor HP Pack x2 do turco (yeralti #69) não apareceu nas capturas novas.
    "drops": [],
    # baú dos andares não vistos (25 em diante): TODO(inventado) o do andar 5 (visto em content/maze_floors.json)
    "chest": [[2050501, 2], [208009, 2]],
    "chest_every": 5,
    "key": 208008,  # Crypt Key (sonType 297): o lucro dobrado (isDouble 2) gasta uma (cliente: MazeFrame)
    "revive": 25,  # (cliente) MazeRiverView.content01: "Reviving will consume 25 Balens"
    "sweep_from": 10,  # (cliente) "You may only blitz after completing level 10."
}


def settings(world_settings: Any) -> dict[str, Any]:
    return DEFAULT | dict((world_settings or {}).get(SETTING) or {})


@dataclass
class Tower:
    index: int = 0  # towerIndex: o andar da corrida (0 = sem corrida; MazeFrame mostra Start)
    record: int = 0  # maxIndex: o maior andar vencido ("My Record", missão 38, loja do labirinto)
    gp: int = 0  # totalGp da corrida ("Total Experience")
    items: list[list[int]] = field(default_factory=list)  # [[tid, n]] dos baús da corrida (itemTempIds)
    enters: int = 0  # enterCount: Start do dia
    day: str = ""  # dia de jogo do ``enters``
    double: bool = False  # corrida com lucro dobrado (isDouble 2)
    # mortes do dia; a 1ª é grátis, as outras custam o revive (visto 10/28 4207 #1105 msg 0, #1547, #1742, #1827 msg 25;
    # o giftToken 2458 -> 2433 -> 2408 é do jogador, não entra aqui, ver 8300 em #1755/#1756)
    deaths: int = 0
    dead: bool = False  # morto sem reviver (4207 e sem 8300 depois): a saída manda 4419 e zera a corrida

    def item_ids(self) -> str:
        return "|".join(f"{t},{n}" for t, n in self.items)  # (visto) "2050201,2|208009,2"

    def add_items(self, got: list[tuple[int, int]]) -> None:
        for tid, n in got:
            for pair in self.items:
                if pair[0] == tid:
                    pair[1] += n
                    break
            else:
                self.items.append([tid, n])


def load(snap: PlayerSnapshot, now: datetime) -> Tower:
    st = ev.peek(snap, KEY)
    tower = Tower(**json.loads(st.text)) if st is not None and st.text else Tower()
    today = gameday.today(now)
    if tower.day != today:  # (dedução) as entradas voltam no dia novo, como as das masmorras
        tower.enters, tower.deaths, tower.day = 0, 0, today  # (jogador 28/10) a morte grátis volta só no dia novo
    return tower


def store(snap: PlayerSnapshot, tower: Tower, now: datetime) -> Any:
    st = ev.state(snap, KEY, now)
    st.text, st.updated_at = json.dumps(asdict(tower)), now
    return st


def record(snap: PlayerSnapshot) -> int:
    """maxIndex gravado (0 sem corrida nenhuma)."""
    st = ev.peek(snap, KEY)
    return int(json.loads(st.text).get("record", 0)) if st is not None and st.text else 0


def info(tower: Tower, cfg: dict[str, Any], index: int = 0) -> pb.TowerInfoMsg:
    """4205. ``index`` é a aba do MazeFrame (0 Catacombs, 1 Necropolis). ``order`` 0: o cliente mostra "None"."""
    if index != 0:  # shortcut: a Necropolis (8101) não tem andares aqui; abre só com o recorde 100 da primeira
        return pb.TowerInfoMsg(index=index, campaignId=SECOND, freeEnterCount=cfg["free_enter"],
                               maxEnterCount=cfg["max_enter"])  # fmt: skip
    return pb.TowerInfoMsg(
        enterCount=tower.enters,
        totalGp=tower.gp,
        towerIndex=tower.index,
        maxIndex=tower.record,
        # shortcut: order (a posição no ranking do recorde, 5439 na captura) vai 0 ("None"); ligar quando houver o
        # ranking do labirinto
        order=0,
        maxEnterCount=cfg["max_enter"],
        itemTempIds=tower.item_ids(),
        freeEnterCount=cfg["free_enter"],
        campaignId=CAMPAIGN,
        index=index,
    )


def floor_gp(cfg: dict[str, Any], floor: int) -> int:
    return int(cfg["gp_per_floor"]) * floor


def chest_goods(cfg: dict[str, Any], floor: int) -> list[list[int]]:
    """Baú do andar (``maze_chests``): o visto nos andares 5 a 20, o da configuração depois. (visto) a gema muda por
    corrida (10/25 #9409, #9470, #9529; 10/26 #693; 10/27 #8677-#9041); cada andar guarda a de uma corrida
    (TODO(inventado) qual). A quantidade de 208009 (Crypt Tokens) é a mesma nas três."""
    return list(_SEEN["chests"].get(str(floor), cfg["chest"]))


def map_of(floor: int) -> int:
    return FIRST_MAP + floor


def floor_of(map_id: int) -> int:
    return map_id - FIRST_MAP


def is_floor(map_id: int) -> bool:
    return CAMPAIGN <= map_id <= FIRST_MAP + int(DEFAULT["floors"])


def boss(templates: GameTemplates, floor: int) -> bool:
    return templates.get("GameHeroTemp", MONSTER_BASE + floor) is not None


def _node(camp: int, master: int, son: int, state: int, pos: tuple[int, int], fix: tuple[int, int]) -> dict[str, Any]:
    """Nó com os campos do 127 captado (só turco: yeralti #37, #84)."""
    return {
        "nodeId": camp, "campDataId": camp, "nodeName": "", "masterType": master, "sonType": son,
        "preNodeIds": "0", "nextNodeIds": "", "state": state, "refreshSpeed": 1, "posX": pos[0], "posY": pos[1],
        "curX": pos[0], "curY": pos[1], "level": 0, "styleType": 1, "attackTypes": 0, "nameColor": 0, "sizeType": 0,
        "toward": 0, "resource": 2, "resetX": 0, "resetY": 0, "fixX": fix[0], "fixY": fix[1], "heroTempId": -1,
        "handlerRange": 0, "fightCapaity": 0, "param1": 0, "param2": 0, "param3": "", "param4": "", "param5": "",
    }  # fmt: skip


def _soldier(living: int, row: Any, pos: int, battle: dict[str, Any]) -> dict[str, Any]:
    """(visto, 157 de 24/10 a 27/10) a escolta tem vida Live / 100, ``castTime`` e skills do andar (``battle``) e
    livingId 4 a 7 nas posições 2, 3, 8 e 9. Sem captura: o ``DefaultSkill`` três vezes e 4000 (TODO(inventado))."""
    hp = int(row["Live"]) // 100
    skills = battle.get("skills") or [int(row["DefaultSkill"])] * 3
    return {"livingId": living, "tempId": int(row["TemplateId"]), "type": 1, "side": 2, "pos": pos, "initHp": hp,
            "hp": hp, "qteTime": 0, "castTime": battle.get("cast", 4000), "skillId": skills}  # fmt: skip


def _hero(row: Any, battle: dict[str, Any]) -> dict[str, Any]:
    """Chefe (visto, 157): livingId 4 na posição 5, vida = Live, sem escolta; ``castTime`` e skills do andar. Sem
    captura: TODO(inventado) o ``DefaultSkill`` dezoito vezes e 6000."""
    hp = int(row["Live"])
    return {
        "heroId": 1300000000, "livingId": 4, "userId": 0, "userPics": 0, "tempId": int(row["TemplateId"]), "type": 3,
        "nickName": row["TemplateName"], "grade": int(row["Grades"]), "side": 2, "pos": 5, "maxHp": hp, "initHp": hp,
        "hp": hp, "hp2": 0, "sp": 0, "slotAvata": "", "clothAvate": "", "cloakPath": "", "hairPath": "",
        "captain": int(row["Captain"]), "res": row["ResPath"], "qteTime": 0,
        "castTime": battle.get("cast", 6000), "pawnTempId": 0,
        "skillId": battle.get("skills") or [int(row["DefaultSkill"])] * 18, "headId": 0, "isShow": False,
        "serverName": "", "wingAvata": "", "fashionArmAvata": "", "fashionClothAvata": "", "awake": 0, "livingId2": 0,
        "fateSkillTempIds": "", "isChange": False, "fightCapacity": 0, "hasShadow": False, "mateId": 0, "curturn": 0,
    }  # fmt: skip


def _battle(templates: GameTemplates, cfg: dict[str, Any], floor: int) -> dict[str, Any]:
    """(visto, 157) battleType 6, attackModel 2 (``attack`` do andar: 1 nos 26-28, 10/28 #1369, #1488, #1578, #1685,
    #1766); quatro do monstro nas posições 2, 3, 8 e 9, e o chefe sozinho (sem
    escolta). ``battleScene`` 10 não conferido no 157. O gpBonus guardado é a base (``rules.exp_bonus`` soma o mundo e a
    descansada)."""
    tid = MONSTER_BASE + floor
    battle = _SEEN["floors"].get(str(floor), {}).get("battle", {})
    spec: dict[str, Any] = {
        "battleType": 6, "mapTempId": map_of(floor), "attackModel": battle.get("attack", 2), "soldiers": [],
        "heroes": [],
        "player": {"livingId": 1, "pos": 1}, "map": map_of(floor), "gpBonus": floor_gp(cfg, floor),
        "strategyBonus": 0, "battleScene": 10,
    }  # fmt: skip
    if (hero := templates.get("GameHeroTemp", tid)) is not None:
        spec["heroes"] = [_hero(hero, battle)]
    elif (pawn := templates.get("PawnTempInfos", tid)) is not None:
        spec["soldiers"] = [_soldier(4 + i, pawn, p, battle) for i, p in enumerate((2, 3, 8, 9))]
    return spec


def _layout(floor: int) -> dict[str, Any]:
    """(visto) as posições mudam em 11 e em 21; o andar 1-25 cai numa das três faixas."""
    key = max(int(k) for k in _SEEN["layouts"] if int(k) <= floor)
    return dict(_SEEN["layouts"][str(key)])


def _floor(templates: GameTemplates, cfg: dict[str, Any], floor: int, top: int) -> dict[str, Any]:
    m = map_of(floor)
    camp = m * 100
    lay = _layout(floor)
    seen = _SEEN["floors"].get(str(floor))
    last = _SEEN["floors"][str(max(int(k) for k in _SEEN["floors"]))]
    # (visto) 1-25: o início é 40 com state 2 nos andares ímpares e 62 com state 1 nos pares (8001 #12046 é 40/2, 8002
    # #12116 é 62/1). Causa não achada; por isso o from_town saiu.
    odd = floor % 2 == 1
    start = _node(camp + START, NODE_START if odd else NODE_SEND, 2301, 2 if odd else 1, lay["start"][:2],
                  lay["start"][2:4])  # fmt: skip
    tid = MONSTER_BASE + floor
    hero = templates.get("GameHeroTemp", tid)
    pawn = templates.get("PawnTempInfos", tid)
    name = (seen or {}).get("name") or (hero or {}).get("TemplateName") or (pawn or {}).get("PawnName", "")
    # TODO(inventado) andares 29+: o sonType 2116 e o poder de luta do último andar visto (28) são chutes
    monster = _node(camp + MONSTER, NODE_MONSTER, (seen or {}).get("son", 2116), 1, lay["monster"][:2],
                    lay["monster"][2:4])  # fmt: skip
    monster |= {
        "nodeName": name, "nameColor": 5, "toward": 180, "resource": 1, "handlerRange": 2,
        "heroTempId": tid if hero is not None else -1, "fightCapaity": (seen or last)["fight"],
        "param3": str(camp + MONSTER), "param4": str(camp + PORTAL) if floor < top else "",
    }  # fmt: skip
    portal = _node(camp + PORTAL, NODE_SEND, 2336, HIDDEN_PORTAL, lay["portal"][:2], lay["portal"][2:4])
    portal |= {
        "resetX": lay["portal"][4],
        "resetY": lay["portal"][5],
        "param1": map_of(floor + 1) if floor < top else 0,
    }
    nodes = [start, monster, portal]
    if floor % int(cfg["chest_every"]) == 0:
        # (visto) o baú é visível (state 1, nameColor 4) e não vai no param4; o sonType alterna 2202 (5, 15, 25) e 2203
        # (10, 20): TODO(inventado) para os andares 26 em diante
        cx = lay["chest"]
        chest = _node(camp + CHEST, NODE_HANDLER, 2202 if floor % 10 == 5 else 2203, 1, cx[:2], cx[2:4])
        chest |= {"nodeName": "Treasure Chest", "nameColor": 4, "resetX": cx[4], "resetY": cx[5]}
        nodes.append(chest)
    zero = "00" * FOG_COLS
    return {"start": lay["start"][:2], "nodes": nodes,
            "fog": {"row": FOG_ROWS, "col": FOG_COLS, "forArray": [zero] * FOG_ROWS}}  # fmt: skip


@lru_cache(maxsize=4)
def _content(templates: GameTemplates, cfg_json: str) -> dict[str, Any]:
    cfg = json.loads(cfg_json)
    top = int(cfg["floors"])
    out: dict[str, Any] = {"campaign": CAMPAIGN, "stages": [], "maps": {}, "battles": {}, "drops": {},
                           "portals": {}, "maze_chests": {}}  # fmt: skip
    for floor in range(1, top + 1):
        m = map_of(floor)
        out["maps"][str(m)] = _floor(templates, cfg, floor, top)
        out["battles"][str(m * 100 + MONSTER)] = _battle(templates, cfg, floor)
        out["drops"][str(m * 100 + MONSTER)] = cfg["drops"]
        if floor < top:
            out["portals"][str(m * 100 + PORTAL)] = map_of(floor + 1)
        if floor % int(cfg["chest_every"]) == 0:
            # (visto) 5, 10, 15, 20: o baú de cada chefe (ganho do 4205); o resto é o ``chest`` da configuração
            out["maze_chests"][str(m * 100 + CHEST)] = chest_goods(cfg, floor)
    return out


def content(templates: GameTemplates, cfg: dict[str, Any]) -> dict[str, Any]:
    """Os andares todos, no formato do ``campaign_contents`` (``CampaignMap.enter_dungeon``)."""
    return _content(templates, json.dumps(cfg, sort_keys=True))
