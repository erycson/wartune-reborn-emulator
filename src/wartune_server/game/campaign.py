"""Campanha de treino (mapas 10001 e 10002): estado do mapa de uma sessão.

Os nós, tropas e diálogos vêm de ``content/tutorial.json`` (extraído da captura oficial). Cada nó
tem dois ids: o de execução (``nodeId``, usado nos pacotes 127/128/4105/4122/4124) e o do template
(``campDataId``, usado pelo cliente em 5125/8196/5032).

O cliente só grava o ``noviceProcess`` em pontos de retomada; ao reentrar, o servidor recoloca os nós
como estavam naquele ponto (``RESUME``) e o guia do cliente continua dali.
"""

from __future__ import annotations

import copy
from collections import Counter
from dataclasses import dataclass, field
from typing import Any

from google.protobuf.json_format import ParseDict

from ..content import dungeon, tutorial
from ..protocol.messages import wartune_pb2 as pb

FIRST_MAP, SECOND_MAP = 10001, 10002
DUNGEON_FIRST, DUNGEON_SECOND = 1011, 1021  # masmorra Kurt İni (campanha 1001), em ordem
PET_ISLANDS = range(20001, 25001)  # WorldBossHelper.checkPetLand: 20000 < mapa <= 25000
SECOND_MAP_FROM = 15500  # noviceProcess a partir do qual o jogador já passou pelo portal
ESCORT_FROM = 15300  # a Tina segue o jogador desde aqui (mapa 10001) até o fim
FOG_ROWS, FOG_COLS = 18, 19

NORMAL, FIGHTING, DONE = 1, 4, 8  # CampaignNodeMsg.state (2 = NPC parado, 16 = escondido)
HIDDEN = 16
MONSTER, TRIGGER, PANDORA = 42, 53, 61  # masterType (61 também é o baú de ouro, sem buff em param3)
AGGRESSIVE = 1  # attackTypes: persegue o jogador (8196 -> 4105)
FLICKER_DELAY, DISAPPEAR_DELAY = 85, 35  # delay das PlayerMovieMsg de liberar/esconder um nó (replay #1595/#1597)

# noviceProcess gravado -> estados dos nós que já tinham mudado (campDataId -> estado)
RESUME: dict[int, list[tuple[int, dict[int, int]]]] = {
    FIRST_MAP: [
        (11400, {1000103: DONE}),
        (12000, {1000104: DONE}),
        (13500, {1000110: DONE, 1000106: DONE, 1000109: NORMAL}),
        (14000, {1000108: NORMAL}),
    ],
    SECOND_MAP: [
        (16700, {1000202: DONE}),
        (17500, {1000203: DONE}),
        (18500, {1000208: DONE, 1000205: DONE, 1000206: NORMAL, 1000207: NORMAL}),
    ],
}


def map_for(novice: int) -> int:
    return SECOND_MAP if novice >= SECOND_MAP_FROM else FIRST_MAP


@dataclass
class CampaignMap:
    map_id: int
    nodes: dict[int, dict[str, Any]]  # campDataId -> CampaignNodeMsg (como dict, estado muda)
    pos: tuple[int, int]
    escort: int = 0  # nodeId do NPC que segue o jogador (Tina), 0 = nenhum
    callbacks: Counter[int] = field(default_factory=Counter)  # 5032 recebidos por nó
    fighting: int = 0  # campDataId em combate
    talked: set[int] = field(default_factory=set)  # nós cujo diálogo de chegada já saiu
    dungeon: bool = False  # masmorra 1001 (``dungeon_1001.json``): sem Tina, com 130 da captura
    fog_data: dict[str, Any] | None = None  # 130 da captura (só masmorra)
    card: int | None = None  # index do 5122: carta escolhida, usada no fim do mapa
    waiting: int = 0  # campDataId de uma luta que espera o 5180 (último nó, replay #1169)
    finished: bool = False  # mapa vencido: o fim (137 ... 134) já saiu
    buffs: list[int] = field(default_factory=list)  # buffs da Pandora, zerados no fim

    @classmethod
    def enter(cls, map_id: int, novice: int) -> CampaignMap:
        data = tutorial()["maps"][str(map_id)]
        nodes = {n["campDataId"]: copy.deepcopy(n) for n in data["nodes"]}
        for since, states in RESUME[map_id]:
            if novice >= since:
                for camp, state in states.items():
                    nodes[camp]["state"] = state
        escort = next((n["nodeId"] for n in nodes.values() if n["heroTempId"] > 0), 0)
        following = map_id == SECOND_MAP or novice >= ESCORT_FROM
        return cls(map_id, nodes, tuple(data["start"]), escort=escort if following else 0)

    @classmethod
    def enter_dungeon(cls, map_id: int) -> CampaignMap:
        data = dungeon()["maps"][str(map_id)]
        nodes = {n["campDataId"]: copy.deepcopy(n) for n in data["nodes"]}
        return cls(map_id, nodes, tuple(data["start"]), dungeon=True, fog_data=data["fog"])

    def node(self, camp: int) -> dict[str, Any] | None:
        return self.nodes.get(camp)

    def by_runtime(self, node_id: int) -> dict[str, Any] | None:
        return next((n for n in self.nodes.values() if n["nodeId"] == node_id), None)

    def node_list(self) -> pb.CampaignNodeListMsg:
        msg = pb.CampaignNodeListMsg()
        for n in reversed(list(self.nodes.values())):  # oficial manda do último ao primeiro
            ParseDict(n, msg.node.add())
        return msg

    def fog(self) -> pb.CampaignFogMsg:
        if self.fog_data is not None:  # masmorra: a névoa que o oficial mandou no 130 (24 x 19 no 1011)
            rows = [bytes.fromhex(h) for h in self.fog_data["forArray"]]
            return pb.CampaignFogMsg(
                row=self.fog_data["row"], col=self.fog_data["col"], forArray=rows, mapTempId=self.map_id
            )
        # tudo visível (0); o tutorial não usa névoa
        return pb.CampaignFogMsg(
            row=FOG_ROWS, col=FOG_COLS, forArray=[bytes(FOG_COLS)] * FOG_ROWS, mapTempId=self.map_id
        )

    def locked(self, camp: int) -> bool:
        """Nó que só aparece quando o grupo de lobos cai (``param4`` com ação 1); some ao cair o grupo."""
        for n in self.nodes.values():
            if any(target == camp and action == 1 for target, action in unlock_actions(n)):
                return any(self.nodes[g]["state"] != DONE for g in group_of(n) if g in self.nodes)
        return False


def group_of(node: dict[str, Any]) -> list[int]:
    """Grupo de lobos de um nó (``param3`` do 127, ids separados por ``|``); vazio para os demais."""
    if node["masterType"] != MONSTER:
        return []
    return [int(x) for x in str(node.get("param3", "")).split("|") if x]


def unlock_actions(node: dict[str, Any]) -> list[tuple[int, int]]:
    """Ações ao cair o grupo (``param4`` do 127): ``campDataId,ação``. Ação 0 esconde, 1 mostra."""
    return [(int(a), int(b)) for a, b in (x.split(",") for x in str(node.get("param4", "")).split("|") if x)]


def battle_spec(camp: int) -> dict[str, Any] | None:
    """Spec da luta de um nó: do tutorial (ids 1000xxx) ou da masmorra (ids 101xxx/102xxx)."""
    spec: dict[str, Any] | None = tutorial()["battles"].get(str(camp)) or dungeon()["battles"].get(str(camp))
    return spec
