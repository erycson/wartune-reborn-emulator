"""Cadeiras (9638 ``ChairsListMsg {op}`` -> 414 aberto e 415 a tela). Edição em ``game_settings.chairs``
(``begin``/``end`` em hora do jogo, ``chairsNeedPoints``, ``rewardNeedChairs``, ``comfortItems`` e ``luckyItems``
["TemplateId|quantidade", ...], ``luckyCount``); sem ela, fechadas (414 falso, como em todas as capturas).

Cliente (``PublicChairsManager``, ``PublicChairsFrame``): op 1 abre (415), op 2 resgata; o botão "recarregar" leva à
página de recarga, a barra mostra ``totalChairsCount`` / ``rewardNeedChairs`` do servidor, o texto mostra
``chairsNeedPoints`` (sem cadeira) ou ``leftPoint`` (o que falta para a próxima), ``currentChairs`` as minhas,
``rewardCounts`` os resgates pendentes (o botão só acende com > 0) e ``luckyNickName`` os sortudos; as dicas dos
ícones listam ``luckyItems`` e ``comfortItems`` (``TemplateId|quantidade``, ``getTimeStr``).

Sem captura nem texto no idioma; TODO(inventado) a regra: cada ``chairsNeedPoints`` Balens recarregados na edição
(``cash_ledger`` ``recharge``) dão uma cadeira; cada cadeira é um resgate de ``comfortItems``; quando o servidor
soma ``rewardNeedChairs`` cadeiras, os ``luckyCount`` com mais cadeiras (desempate pelo id) são os sortudos e o
próximo resgate de cada um leva também ``luckyItems``. Padrões: 100 Balens, 100 cadeiras, 3 sortudos.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from ...domain.models import PlayerSnapshot
from ...protocol.messages import wartune_pb2 as pb
from ..builders import login as b
from ..router import router
from ..session import GameSession
from . import minijogo as mj
from .player import alert

S_OPEN, S_INFO = 414, 415
KEY = "chairs"
REQUEST, TAKE = 1, 2
NEED_POINTS, NEED_CHAIRS, LUCKY = 100, 100, 3  # TODO(inventado): padrões


def _items(raw: list[str]) -> list[tuple[int, int]]:
    return [(int(t), int(n)) for t, n in (str(x).split("|") for x in raw)]


def open_msg(s: GameSession) -> pb.SimplePropertyMsg:
    return pb.SimplePropertyMsg(param7=mj.is_open(mj.cfg(s, KEY), s.ctx.clock.now()))


def _state(snap: PlayerSnapshot, c: Any) -> dict[str, Any]:
    data = mj.load(snap, KEY)
    return data if data.get("edition") == c["begin"] else {"edition": c["begin"], "claimed": 0, "lucky_paid": False}


async def _board(s: GameSession, c: Any, snap: PlayerSnapshot, data: dict[str, Any], now: datetime) -> list[Any]:
    """Grava as cadeiras do jogador e devolve as linhas da edição de todo o servidor: (cadeiras, id, apelido)."""
    need = int(c.get("chairsNeedPoints", NEED_POINTS))
    point = await s.ctx.characters.read(lambda uow: uow.characters.recharged(s.player_id, mj.at(c, "begin"), now))
    data |= {"chairs": point // need, "left": need - point % need, "nick": snap.character.nickname or ""}
    await s.ctx.characters.save(mj.store(snap, KEY, data, now))
    states = await s.ctx.characters.read(lambda uow: uow.events.by_prefix(snap.character.server_id, KEY))
    rows = []
    for st in states:
        other = mj.load_text(st.text)
        if st.key == KEY and other.get("edition") == c["begin"]:
            rows.append((int(other.get("chairs", 0)), st.character_id, str(other.get("nick", ""))))
    return rows


def _lucky(c: Any, rows: list[Any]) -> list[Any]:
    if sum(r[0] for r in rows) < int(c.get("rewardNeedChairs", NEED_CHAIRS)):
        return []
    return sorted((r for r in rows if r[0] > 0), key=lambda r: (-r[0], r[1]))[: int(c.get("luckyCount", LUCKY))]


@router.on(9638)
async def chairs(s: GameSession, msg: pb.ChairsListMsg) -> None:
    c, now, snap = mj.cfg(s, KEY), s.ctx.clock.now(), s.snapshot
    assert snap is not None
    s.send(S_OPEN, open_msg(s))
    if not mj.is_open(c, now):
        s.send(S_INFO, pb.ChairsListMsg())  # obrigatório se a tela abrir
        return
    data = _state(snap, c)
    rows = await _board(s, c, snap, data, now)
    lucky = _lucky(c, rows)
    is_lucky = any(r[1] == s.player_id for r in lucky) and not data["lucky_paid"]
    pending = data["chairs"] - data["claimed"]
    if msg.op == TAKE:
        if pending <= 0 and not is_lucky:
            alert(s, "No rewards to claim.")  # TODO(inventado): o cliente apaga o botão sem resgate
        else:
            drops = [(t, n * max(pending, 0)) for t, n in _items(c.get("comfortItems", []))]
            if is_lucky:
                drops += _items(c.get("luckyItems", []))
            data |= {"claimed": data["chairs"], "lucky_paid": data["lucky_paid"] or is_lucky}
            await mj.give(s, snap, [d for d in drops if d[1] > 0], mj.store(snap, KEY, data, now))
            pending, is_lucky = 0, False
    elif msg.op != REQUEST:
        s.log.info("9638 op desconhecido", op=msg.op)
    out = pb.ChairsListMsg(
        op=msg.op,
        totalChairsCount=sum(r[0] for r in rows),
        userId=s.player_id,
        currentChairs=data["chairs"],
        rewardCounts=pending + (1 if is_lucky and pending <= 0 else 0),
        rewardNeedChairs=int(c.get("rewardNeedChairs", NEED_CHAIRS)),
        chairsNeedPoints=int(c.get("chairsNeedPoints", NEED_POINTS)),
        openTime=str(c["begin"]),
        stopTime=str(c["end"]),
        leftPoint=data["left"],
    )
    out.luckyNickName.extend(r[2] for r in lucky)
    out.luckyItems.extend(str(x) for x in c.get("luckyItems", []))
    out.comfortItems.extend(str(x) for x in c.get("comfortItems", []))
    s.send(S_INFO, b.complete(out))
