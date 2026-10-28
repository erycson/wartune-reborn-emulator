"""Campanha de treino (mapas 10001 e 10002): estado do mapa de uma sessão.

Os nós, tropas e diálogos vêm de ``content/tutorial.json`` (extraído da captura do oficial inglês). Cada nó
tem dois ids: o de execução (``nodeId``, usado nos pacotes 127/128/4105/4122/4124) e o do template
(``campDataId``, usado pelo cliente em 5125/8196/5032).

O cliente só grava o ``noviceProcess`` em pontos de retomada; ao reentrar, o servidor recoloca os nós
como estavam naquele ponto (``RESUME``) e o guia do cliente continua dali.
"""

from __future__ import annotations

import copy
import struct
from collections import Counter
from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from google.protobuf.json_format import ParseDict

from ..content import tutorial
from ..protocol.messages import wartune_pb2 as pb

FIRST_MAP, SECOND_MAP = 10001, 10002
PET_ISLANDS = range(20001, 25001)  # WorldBossHelper.checkPetLand: 20000 < mapa <= 25000
FAM_MAP = 7501  # terra secreta da guilda (Guild Chamber), handlers/fam.py
SECOND_MAP_FROM = 15500  # noviceProcess a partir do qual o jogador já passou pelo portal
ESCORT_FROM = 15300  # a Tina segue o jogador desde aqui (mapa 10001) até o fim
FOG_ROWS, FOG_COLS = 18, 19

NORMAL, FIGHTING, DONE = 1, 4, 8  # CampaignNodeMsg.state (2 = NPC parado, 16 = escondido)
HIDDEN = 16
FOLLOWING = 2  # o NPC que passou a seguir o jogador (Tina, Elise)
MONSTER, TRIGGER, PANDORA = 42, 53, 61  # masterType (61 também é o baú de ouro, sem buff em param3)
BOSS, COLLECT = 41, 91  # masterType: chefe (a vitória fecha o mapa) e pilha da pedreira (6001)
GATE = 62  # masterType do portal que o grupo caído mostra (1002: 113106 -> 1132; 9001: 201107)
SHOW = 2  # ação do param4 sem ``,ação`` (1002: "113106"): o nó aparece só com o 128, sem FLICKER (#2471)
AGGRESSIVE = 1  # attackTypes: persegue o jogador (8196 -> 4105)
FLICKER_DELAY, DISAPPEAR_DELAY = 85, 35  # delay das PlayerMovieMsg de liberar/esconder um nó (inglês #1414/#1412)

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
class StageRun:
    """Uma etapa de masmorra em andamento (do 125 tipo 1 ao 137): o que o relatório conta. Passa de um mapa ao
    outro da etapa (1131 -> 1132): (visto) o ``time`` do 137 #2705 (189) conta desde o 125 do 1131 (#2311)."""

    campaign_id: int
    stage: int  # índice em ``content["stages"]``
    maps: tuple[int, ...]
    started: datetime
    wound: int = 0  # dano que o lado do jogador causou
    hurt: int = 0  # dano que o lado do jogador sofreu
    lost: int = 0  # lutas perdidas (``failedCount``)
    batter: int = 0  # maior 8282 (combo) da etapa
    rewarded: bool = True  # campanha em grupo sem a entrada do dia: sem EXP, drop nem carta (cliente)


@dataclass
class CampaignMap:
    map_id: int
    nodes: dict[int, dict[str, Any]]  # campDataId -> CampaignNodeMsg (como dict, estado muda)
    pos: tuple[int, int]
    escort: int = 0  # nodeId do NPC que segue o jogador (Tina), 0 = nenhum
    callbacks: Counter[int] = field(default_factory=Counter)  # 5032 recebidos por nó
    fighting: int = 0  # campDataId em combate
    talked: set[int] = field(default_factory=set)  # nós cujo diálogo de chegada já saiu
    chased: set[int] = field(default_factory=set)  # nós que já perseguiram (a fala do chase só na 1ª vez)
    dungeon: bool = False  # masmorra (``campaign_contents``): sem Tina, com 130 da captura
    fog_data: dict[str, Any] | None = None  # 130 da captura (só masmorra)
    card: int | None = None  # index do 5122 já virado (uma carta por mapa, depois do 135)
    finished: bool = False  # mapa vencido: o fim (137 ... 134) já saiu
    buffs: list[int] = field(default_factory=list)  # buffs da Pandora, zerados no fim
    world_boss: bool = False  # mapa do chefe do mundo (5001/5003): um nó, a luta em ``handlers/worldboss.py``
    content: Mapping[str, Any] | None = None  # conteúdo da campanha (masmorra ou pedreira), do banco
    run: StageRun | None = None  # etapa da masmorra (relatório 137)
    quarry: bool = False  # pedreira 6001: coleta (5032) e a luta do 8699, sem fim nem carta
    over: tuple[int, int] | None = None  # (gp, strategy) do 4382 que espera a volta ao mapa (5035 state 4)
    ending: list[Any] | None = None  # etapa vencida: missões (Quest) que fecham no fim, que sai com o 4382
    fallen: dict[str, list[tuple[int, int]]] = field(default_factory=dict)  # baús da luta por signId (5129)
    hook: bool = False  # sala do gancho (7001-7009): estátuas, em ``handlers/hangup.py``
    fam: bool = False  # terra secreta da guilda (7501): Invasores, em ``handlers/fam.py``
    ready: bool = False  # o 1º 5035 state 4 já foi tratado (terra secreta: a sala; chefe do mundo: 4371 e 4413)

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
    def enter_dungeon(cls, content: Mapping[str, Any], map_id: int, run: StageRun | None = None) -> CampaignMap:
        data = content["maps"][str(map_id)]
        nodes = {n["campDataId"]: copy.deepcopy(n) for n in data["nodes"]}
        x, y = data["start"]
        if map_id == FAM_MAP:  # sem névoa como a pedreira, mas sem coleta nem a luta do 8699
            return cls(map_id, nodes, (int(x), int(y)), content=content, fam=True)
        if "fog" not in data:  # pedreira: (visto) #1805-#1809 sem 130
            return cls(map_id, nodes, (int(x), int(y)), content=content, quarry=True)
        return cls(map_id, nodes, (int(x), int(y)), dungeon=True, fog_data=data["fog"], content=content, run=run)

    def battle(self, camp: int | str) -> dict[str, Any] | None:
        """Luta do nó (ou ``"8699"``, a da pedreira) no conteúdo da campanha."""
        spec: dict[str, Any] | None = (self.content or {}).get("battles", {}).get(str(camp))
        return spec

    def battle_like(self, camp: int) -> dict[str, Any] | None:
        """Luta do nó ou, sem uma própria, a de outro nó do conteúdo com o mesmo ``sonType``: (dedução) a Tauren Tomb
        114105 só caiu na moeda nas capturas; o param5 dela também tem a luta, que sai com a da 113105."""
        if (spec := self.battle(camp)) is not None or (node := self.node(camp)) is None:
            return spec
        for m in (self.content or {}).get("maps", {}).values():
            for n in m["nodes"]:
                if n["sonType"] == node["sonType"] and (spec := self.battle(n["campDataId"])) is not None:
                    return spec
        return None

    def part(self, name: str, camp: int | str) -> Any:
        """Entrada ``camp`` de uma seção do conteúdo (``chests``, ``confirms``, ``wins``, ``plots``...)."""
        return (self.content or {}).get(name, {}).get(str(camp))

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
        """Nó que só aparece quando o grupo cai (``param4`` com ação 1 ou sem ação); some ao cair o grupo."""
        for n in self.nodes.values():
            if any(target == camp and action in (1, SHOW) for target, action in unlock_actions(n)):
                return any(self.nodes[g]["state"] != DONE for g in group_of(n) if g in self.nodes)
        return False


# param5 dos nós de caixa (127): "tipo,item,n,peso|...", sorteados pelo peso. (visto) Tauren Tomb 113105/114105
# "-200,0,5000,50|-500,0,0,50" (5.000 Daru ou luta: as duas aconteceram, tutorial_en #2397 e #2874); Hunter's Treasure
# Cache e Enchanted Crystal Mine "-300,2040103,1,50|-200,0,10000,50" (Lvl. 3 Luck Stone ou 10.000 Daru: os dois na
# 103105, oficial_20261023-153200-1 e oficial_20261023-171155-1). O cliente não lê o param5.
OUT_ITEM, OUT_DARU, OUT_FIGHT = -300, -200, -500
DARU, GOLD = -300, -100  # TemplateIds das moedas em ``rewards.CURRENCIES`` (strategy, gold)


def outcomes(node: Mapping[str, Any]) -> list[tuple[int, list[tuple[int, int]], int]]:
    """Desfechos do ``param5`` do nó: (tipo, drops, peso); vazio se o param5 não for dessa forma."""
    out = []
    for part in str(node.get("param5", "")).split("|"):
        fields = part.split(",")
        if len(fields) != 4 or not all(f.lstrip("-").isdigit() for f in fields):
            return []
        kind, tid, n, weight = (int(f) for f in fields)
        drops = [(tid, n)] if kind == OUT_ITEM else [(DARU, n)] if kind == OUT_DARU else []
        out.append((kind, drops, weight))
    return out


def group_of(node: Mapping[str, Any]) -> list[int]:
    """Grupo de monstros de um nó (``param3`` do 127, ids separados por ``|``); vazio para os demais."""
    if node["masterType"] != MONSTER:
        return []
    return [int(x) for x in str(node.get("param3", "")).split("|") if x]


def unlock_actions(node: Mapping[str, Any]) -> list[tuple[int, int]]:
    """Ações ao cair o grupo (``param4`` do 127 de um monstro): ``campDataId,ação``. Ação 0 esconde, 1 mostra
    com FLICKER (1021); sem ``,ação`` (1002, "113106") só mostra (``SHOW``). Nos outros nós o param4 é outra coisa
    (a caixa do 1132 lista os nós que fecham com ela)."""
    if node["masterType"] != MONSTER:
        return []
    out = []
    for x in str(node.get("param4", "")).split("|"):
        if x:
            target, _, action = x.partition(",")
            out.append((int(target), int(action) if action else SHOW))
    return out


def battle_spec(camp: int) -> dict[str, Any] | None:
    """Spec da luta de um nó do tutorial (ids 1000xxx); as masmorras usam ``CampaignMap.battle``."""
    spec: dict[str, Any] | None = tutorial()["battles"].get(str(camp))
    return spec


# -- relatório do fim da etapa (137) ---------------------------------------------------------------
# (visto) os quatro 137 da captura inglesa (#1098, #1521, #2705, #3157) e o do gravador (oficial_encantar #689, Worg
# Lair de novo) têm notas 1, 5, 5 e 4: dano causado / StandardDamage de 0,17 a 0,62 é D, dano sofrido /
# StandardHurt até 0,17 é S, sem derrota é S.
# (dedução) os degraus abaixo e a nota total = média arredondada; nada além disso fecha com as amostras.
WOUND_STEPS = (0.7, 0.8, 0.9, 1.0)  # causado/StandardDamage: abaixo do 1º = D (1) ... a partir do último = S (5)
HURT_STEPS = (0.2, 0.4, 0.6, 0.8)  # sofrido/StandardHurt: até o 1º = S (5) ... acima do último = D (1)
GP_BONUS = 1.05  # (visto) totalGp 630 com BaseGp 600 e 839 com 800: (int)(BaseGp * 1.05f) em float de 32 bits


def _f32(x: float) -> float:
    return float(struct.unpack("f", struct.pack("f", x))[0])


def total_gp(base_gp: int) -> int:
    """EXP do fim da etapa. 800 * 1,05 = 840, mas o oficial mandou 839: a conta é em float (``1.05f``)."""
    return int(_f32(_f32(base_gp) * _f32(GP_BONUS)))


def grades(run: StageRun, row: Mapping[str, Any]) -> tuple[int, int, int, int]:
    """Notas (1 = D ... 5 = S): dano causado, dano sofrido, derrotas e a total."""
    dealt = run.wound / max(1, int(row.get("StandardDamage") or 0))
    taken = run.hurt / max(1, int(row.get("StandardHurt") or 0))
    wound = 1 + sum(dealt >= s for s in WOUND_STEPS)
    hurt = 5 - sum(taken > s for s in HURT_STEPS)
    failed = max(1, 5 - run.lost)
    return wound, hurt, failed, int((wound + hurt + failed) / 3 + 0.5)


def report(run: StageRun, row: Mapping[str, Any], now: datetime) -> pb.CampaignReportMsg:
    """137 calculado. ``time``: segundos desde o 125 da etapa (visto: 143,7 -> 143 ... 177,3 -> 177).
    ponytail: ``StandSecond`` não entra em nota nenhuma do 137 (não há campo de tempo avaliado); time/friend/vip
    join ficam 0 (jogo solo, sem VIP na captura)."""
    wound, hurt, failed, total = grades(run, row)
    return pb.CampaignReportMsg(
        time=int((now - run.started).total_seconds()), woundValue=run.wound, hurtValue=run.hurt,
        failedCount=run.lost, woundAppraisal=wound, hurtAppraisal=hurt, failedAppraisal=failed,
        totalAppraisal=total, batter=run.batter, teamJoin=0, friendJoin=0, vipJoin=0, propJoin=0, otherJoin=0,
        totalGp=total_gp(int(row.get("BaseGp") or 0)), petGp=0,
    )  # fmt: skip
