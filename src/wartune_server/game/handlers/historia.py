"""História (Time Story, 8629/8630 -> 4546) e caixa de ano novo da cidade do céu (8994 -> 143/4811).

História: (cliente) ``TimeStoryFrame.setEggByPageChange`` manda o 8629 a cada página, com ``isAccess`` a cada 5ª
troca; o 4546 (``__eggDropHandler``) mostra o ovo, e clicar nele (ou 7 s, ou fechar o quadro) manda o 8630. O ovo
"tem muito ouro" (lang ``timestory.TimeStoryFrame.eggImage.tipData``). Regras em ``game_settings.time_story`` (0123).

Caixa de ano novo: nós ``MasterType`` 300..315/410 do mapa 10000 (``SpaceNodeType.isYearNode``). 8994 ``param1``:
3 = procurar (``SpaceUIMediator``, ao entrar no space) -> 4811 com as caixas; 1 = clicar no nó
(``StoreSocketOutManager.sendYearBoxCollect``, nível 35) -> 143 "COLLECTION"; 2 = fim da coleta
(``CollectionAction`` -> ``sendYearBoxCollectConfirm``) -> prêmio e 4811 de novo. Regras em
``game_settings.new_year_box`` (0123); fora da janela não responde, como no oficial (1023-215937-1 #751).
"""

from __future__ import annotations

from typing import Any

from ...domain import gameday
from ...protocol.messages import wartune_pb2 as pb
from ...templates.repository import Row
from .. import space
from ..router import router
from ..session import GameSession
from . import minijogo as mj
from .space import COLLECT_TIME, S_MOVIE, _near

S_EGG, S_YEAR_NODES = 4546, 4811
STORY = "time_story"  # EventState: {"day", "eggs" (dados hoje), "egg" (ovo à espera do 8630)}
YEAR = "new_year_box"  # EventState: {"day", "taken": [nós coletados hoje]}
SEARCH, COLLECT, CONFIRM = 3, 1, 2  # SimplePropertyMsg.param1 do 8994 (StoreSocketOutManager:151-180)


def _today(s: GameSession, data: dict[str, Any]) -> dict[str, Any]:
    today = gameday.today(s.ctx.clock.now())
    return data if data.get("day") == today else {"day": today}


@router.on(8629)
async def story_page(s: GameSession, msg: pb.GameStoryMsg) -> None:
    snap, c = s.snapshot, mj.cfg(s, STORY)
    if snap is None or not c or not msg.isAccess:
        return
    data = _today(s, mj.load(snap, STORY))
    if data.get("egg") or int(data.get("eggs", 0)) >= int(c["dailyEggs"]):
        return
    data["egg"], data["eggs"] = True, int(data.get("eggs", 0)) + 1
    await s.ctx.characters.save(mj.store(snap, STORY, data, s.ctx.clock.now()))
    s.send(S_EGG, pb.GameStoryMsg(isDrop=True, index=msg.index))


@router.on(8630)
async def story_egg(s: GameSession, _: object) -> None:
    """Abre o ovo à espera; o 8630 do fechar o quadro sem ovo não dá nada."""
    snap = s.snapshot
    if snap is None or not (data := mj.load(snap, STORY)).get("egg"):
        return
    data["egg"] = False
    await mj.give(s, snap, mj.pairs(mj.cfg(s, STORY)["prize"]), mj.store(snap, STORY, data, s.ctx.clock.now()))


def _year_node(s: GameSession, node_id: int) -> Row | None:
    node = next(s.ctx.templates.find("MapNodeInfos", Id=str(node_id), MapId=str(space.SPACE)), None)
    kind = int(node["MasterType"]) if node else 0
    return node if 300 <= kind <= 315 or kind == 410 else None


def _send_nodes(s: GameSession, c: dict[str, Any] | Any, taken: list[int]) -> None:
    msg = pb.QueryCollectCampaignNodeRspMsg()
    for node in s.ctx.templates.find("MapNodeInfos", MapId=str(space.SPACE)):
        if _year_node(s, int(node["Id"])) and int(node["Id"]) not in taken:
            msg.collectCampaignNode.add(
                mastType=int(node["MasterType"]), campaignDataId=int(node["Id"]), sonType=int(node["SonType"]),
                name=str(c["name"]),
            )  # fmt: skip
    s.send(S_YEAR_NODES, msg)


@router.on(8994)
async def new_year_box(s: GameSession, msg: pb.SimplePropertyMsg) -> None:
    snap, c, now = s.snapshot, mj.cfg(s, YEAR), s.ctx.clock.now()
    if snap is None or not mj.is_open(c, now):
        s.log.info("8994 sem evento de ano novo", param1=msg.param1)
        return
    data = _today(s, mj.load(snap, YEAR))
    taken: list[int] = data.setdefault("taken", [])
    if msg.param1 == SEARCH:
        _send_nodes(s, c, taken)
        return
    node = _year_node(s, msg.param2)
    if node is None or msg.param2 in taken or not _near(s, node) or snap.character.grades < int(c["minLevel"]):
        s.log.info("8994 recusado", param1=msg.param1, no=msg.param2)
        return
    if msg.param1 == COLLECT:
        s.space_collect = (msg.param2, now)
        s.send(S_MOVIE, pb.PlayerMovieMsg(movieTargetType=0, targetId=msg.param2, movieType="COLLECTION"))
        return
    pending, s.space_collect = s.space_collect, None
    if msg.param1 != CONFIRM or pending is None or pending[0] != msg.param2 or now - pending[1] < COLLECT_TIME:
        s.log.info("8994 sem coleta iniciada", param1=msg.param1, no=msg.param2)
        return
    taken.append(msg.param2)
    await mj.give(s, snap, mj.pairs(c["prize"]), mj.store(snap, YEAR, data, now))
    _send_nodes(s, c, taken)
