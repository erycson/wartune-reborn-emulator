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

from ..content import tutorial
from ..protocol.messages import wartune_pb2 as pb

FIRST_MAP, SECOND_MAP = 10001, 10002
SECOND_MAP_FROM = 15500  # noviceProcess a partir do qual o jogador já passou pelo portal
ESCORT_FROM = 15300  # a Tina segue o jogador desde aqui (mapa 10001) até o fim
FOG_ROWS, FOG_COLS = 18, 19

NORMAL, FIGHTING, DONE = 1, 4, 8  # CampaignNodeMsg.state (2 = NPC parado, 16 = escondido)
MONSTER, TRIGGER = 42, 53  # masterType
AGGRESSIVE = 1  # attackTypes: persegue o jogador (8196 -> 4105)

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
        # tudo visível (0); o tutorial não usa névoa
        return pb.CampaignFogMsg(
            row=FOG_ROWS, col=FOG_COLS, forArray=[bytes(FOG_COLS)] * FOG_ROWS, mapTempId=self.map_id
        )
