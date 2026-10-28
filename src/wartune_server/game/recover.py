"""Recuperar EXP (9503/4912, cliente ExpBackManager + ExpBackSignelFrame): o que ficou sem fazer ontem.

Na virada do dia (``daily.roll``, antes de zerar os contadores) grava em ``recover`` (EventState, texto JSON
``{sonType: num}``) quanto de cada atividade sobrou do dia anterior: ``num = OneDayMax - feito ontem``
(``RecoverInfos``; ``Max`` 1 = só um dia, quem some vários dias vê o dia cheio). ``ev.daily`` zera a lista no
outro dia. Atividades com contador no servidor:

- 1 campanha em grupo (``multi_copy_*``), 4 painel de recompensas (``offer:count``), 8 coliseu
  (``arena.challenge_count``). As outras (labirintos 2/3, torre 5, templo 6, 7, chefe do mundo 9, imposto 10)
  ficam fora até terem contador diário.

Custos (visto, oficial_20261027 d27 #63: as quatro linhas batem): ``itemCost = num*ItemCount``,
``goldCost = num*Gold``, ``goldReward = itemReward*GoldPercent/ItemPercent``; ``itemReward = num*base*ItemPercent/100``.
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta

from ..domain import gameday
from ..domain.models import EventState, PlayerSnapshot
from ..protocol.messages import wartune_pb2 as pb
from ..templates.repository import GameTemplates
from . import events as ev
from . import rewards

KEY = "recover"
GROUP, OFFER, ARENA = 1, 4, 8  # RecoverInfos.SonType
ITEM = 2131020  # ExpBackSignelFrame: o item de resgate (way 1 e 3)
INSIGNIA = 208001
# base por unidade com ItemPercent 100. (visto) d27 nível 29: grupo 160320/0,8, painel 334080/10/0,6 = 55680;
# d28 nível 31: painel 446400/10/0,6 = 74400; coliseu 150/15 = Insignia x10
EXP_29 = {GROUP: 200400, OFFER: 55680}
# TODO(inventado): curva de nível que passa pelos dois pontos vistos do painel (29 -> 55680, 31 -> 74400);
# nenhum template tem esses números. Trocar pela fórmula do oficial quando houver mais capturas.
EXP_POWER = 4.345


def base(son: int, grades: int) -> rewards.Drop | None:
    if son == ARENA:
        return INSIGNIA, 10
    if son in EXP_29:
        return rewards.EXP, round(EXP_29[son] * (grades / 29) ** EXP_POWER)
    return None


def _used_yesterday(snap: PlayerSnapshot, son: int, now: datetime) -> int:
    yesterday = gameday.game_day(now) - timedelta(days=1)
    c = snap.character
    if son == GROUP and c.multi_copy_day == yesterday.isoformat():
        return max(0, c.multi_copy_max - c.multi_copy_count)
    if son == OFFER and (st := ev.peek(snap, "offer:count")) and gameday.game_day(st.updated_at) == yesterday:
        return st.value
    if son == ARENA and snap.arena is not None and snap.arena.day == yesterday.isoformat():
        return snap.arena.challenge_count
    return 0


def build(snap: PlayerSnapshot, templates: GameTemplates, now: datetime) -> EventState:
    """Monta a lista de hoje (chame na virada, antes de zerar). Personagem novo (sem dia anterior): vazia."""
    st = ev.state(snap, KEY, now)
    left: dict[str, int] = {}
    if snap.character.reset_day:
        for row in templates.rows("RecoverInfos"):
            son = int(row["SonType"])
            if base(son, 1) is not None:
                n = int(row["OneDayMax"]) - _used_yesterday(snap, son, now)
                if n > 0:
                    left[str(son)] = n
    st.value, st.text, st.updated_at = 0, json.dumps(left), now
    return st


def pending(snap: PlayerSnapshot, now: datetime) -> dict[int, int]:
    st = ev.daily(snap, KEY, now)
    return {int(k): v for k, v in json.loads(st.text or "{}").items()}


def info(templates: GameTemplates, son: int, num: int, grades: int) -> pb.RecoverInfo | None:
    row = next(templates.find("RecoverInfos", SonType=str(son)), None)
    drop = base(son, grades)
    if row is None or drop is None or int(row["Grade"]) > grades:
        return None
    item_pct = int(row["ItemPercent"])
    reward = num * drop[1] * item_pct // 100
    return pb.RecoverInfo(
        sonType=son,
        num=num,
        itemCost=num * int(row["ItemCount"]),
        itemReward=reward,
        goldCost=num * int(row["Gold"]),
        goldReward=reward * int(row["GoldPercent"]) // item_pct if item_pct else 0,
    )


def infos_msg(snap: PlayerSnapshot, templates: GameTemplates, now: datetime) -> pb.RecoverInfosMsg:
    rows = (info(templates, son, n, snap.character.grades) for son, n in sorted(pending(snap, now).items()))
    return pb.RecoverInfosMsg(recoverInfos=[r for r in rows if r is not None])
