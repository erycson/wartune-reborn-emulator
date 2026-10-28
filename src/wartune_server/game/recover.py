"""Recuperar EXP (9503/4912, cliente ExpBackManager + ExpBackSignelFrame): o que ficou sem fazer ontem.

Na virada do dia (``daily.roll``, antes de zerar os contadores) grava em ``recover`` (EventState, texto JSON
``{sonType: num}``) quanto de cada atividade sobrou do dia anterior: ``num = OneDayMax - feito ontem``
(``RecoverInfos``; ``Max`` 1 = só um dia, quem some vários dias vê o dia cheio). ``ev.daily`` zera a lista no
outro dia. Atividades e o contador de cada uma:

- 1 campanha em grupo (``multi_copy_*``), 4 painel de recompensas (``offer:count``), 8 coliseu
  (``arena.challenge_count``), 2 Forgotten Catacombs (leed 23 "Enter Forgotten Catacombs"), 9 chefe do mundo
  (leed 18 "Fight a World BOSS"), 6 Altar of Ennoblement (``hangup``: estamina meditada no dia), 10 cobrança do
  conselho (``castle.impose_used``), 7 estamina que transbordou na virada (``weary + 100`` acima de ``weary_limit``).
- 3 Tormented Necropolis e 5 The Spire não têm entrada no servidor: contam como não feitas (a 3 só depois do
  recorde 100 das Catacombs, que a abre).

Prêmio por ``MasterType`` (language ``active.expback.MasterTypeN``): 1 EXP, 2 ouro, 3 estamina, 4 insígnia,
5 "Gold Daru" (ouro e Daru).

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
from . import maze, rewards
from .castle import impose_used, levy_gold

KEY = "recover"
# RecoverInfos.SonType
GROUP, CATACOMBS, NECROPOLIS, OFFER, SPIRE, ALTAR, SPILL, ARENA, BOSS, LEVY = 1, 2, 3, 4, 5, 6, 7, 8, 9, 10
STAMINA = 0  # não é item: soma em ``weary`` (MasterType 3)
LEEDS = {CATACOMBS: "leed:23", BOSS: "leed:18", ALTAR: "hangup"}  # EventState diário de cada atividade
ITEM = 2131020  # ExpBackSignelFrame: o item de resgate (way 1 e 3)
INSIGNIA = 208001
GOLD, DARU = -100, -300
# base por unidade com ItemPercent 100. (visto) d27 nível 29: grupo 160320/0,8, painel 334080/10/0,6 = 55680;
# d28 nível 31: painel 446400/10/0,6 = 74400; coliseu 150/15 = Insignia x10.
# TODO(inventado): 2, 3 e 5 (masmorras de uma vez por dia) com a base da campanha em grupo; sem captura
EXP_29 = {GROUP: 200400, OFFER: 55680, CATACOMBS: 200400, NECROPOLIS: 200400, SPIRE: 200400}
# TODO(inventado): curva de nível que passa pelos dois pontos vistos do painel (29 -> 55680, 31 -> 74400);
# nenhum template tem esses números. Trocar pela fórmula do oficial quando houver mais capturas.
EXP_POWER = 4.345
# (visto) d27 #63: altar num 3 -> itemReward 60 com ItemPercent 100 = 20 de estamina por unidade.
# (dedução) transbordo: a unidade já é estamina, 1 por 1.
STAMINA_PER = {ALTAR: 20, SPILL: 1}
BOSS_29 = 50000  # TODO(inventado): ouro e Daru do chefe do mundo no nível 29, na mesma curva; sem captura


def base(son: int, snap: PlayerSnapshot, templates: GameTemplates) -> rewards.Drop | None:
    grades = snap.character.grades
    if son == ARENA:
        return INSIGNIA, 10
    if son in EXP_29:
        return rewards.EXP, round(EXP_29[son] * (grades / 29) ** EXP_POWER)
    if son in STAMINA_PER:
        return STAMINA, STAMINA_PER[son]
    if son == BOSS:
        return GOLD, round(BOSS_29 * (grades / 29) ** EXP_POWER)
    if son == LEVY:  # uma cobrança do conselho hoje (handlers/castle.gold_impose)
        return (GOLD, gold) if (gold := levy_gold(snap, templates)) else None
    return None


def drops(son: int, template_id: int, reward: int) -> list[rewards.Drop]:
    """O que ``rewards.grant`` entrega (a estamina fica de fora: quem chama soma em ``weary``)."""
    if template_id == STAMINA:
        return []
    return [(GOLD, reward), (DARU, reward)] if son == BOSS else [(template_id, reward)]


def _used_yesterday(snap: PlayerSnapshot, son: int, now: datetime) -> int:
    yesterday = gameday.game_day(now) - timedelta(days=1)
    c = snap.character
    if son == GROUP and c.multi_copy_day == yesterday.isoformat():
        return max(0, c.multi_copy_max - c.multi_copy_count)
    if son == OFFER and (st := ev.peek(snap, "offer:count")) and gameday.game_day(st.updated_at) == yesterday:
        return st.value
    if son == ARENA and snap.arena is not None and snap.arena.day == yesterday.isoformat():
        return snap.arena.challenge_count
    if son in LEEDS and (st := ev.peek(snap, LEEDS[son])) and gameday.game_day(st.updated_at) == yesterday:
        return st.value
    if son == LEVY and snap.castle is not None:
        return impose_used(snap.castle, now - timedelta(days=1))
    if son == SPILL:  # a virada dá 100 (daily.WEARY_DAILY = OneDayMax) até o teto: o que cabe não transborda
        return max(0, c.weary_limit - c.weary)
    if son == NECROPOLIS and maze.record(snap) < 100:
        return 1 << 30  # fechada: nada a recuperar
    return 0


def build(snap: PlayerSnapshot, templates: GameTemplates, now: datetime) -> EventState:
    """Monta a lista de hoje (chame na virada, antes de zerar). Personagem novo (sem dia anterior): vazia."""
    st = ev.state(snap, KEY, now)
    left: dict[str, int] = {}
    if snap.character.reset_day:
        for row in templates.rows("RecoverInfos"):
            son = int(row["SonType"])
            if base(son, snap, templates) is not None:
                n = int(row["OneDayMax"]) - _used_yesterday(snap, son, now)
                if n > 0:
                    left[str(son)] = n
    st.value, st.text, st.updated_at = 0, json.dumps(left), now
    return st


def pending(snap: PlayerSnapshot, now: datetime) -> dict[int, int]:
    st = ev.daily(snap, KEY, now)
    return {int(k): v for k, v in json.loads(st.text or "{}").items()}


def info(snap: PlayerSnapshot, templates: GameTemplates, son: int, num: int) -> pb.RecoverInfo | None:
    row = next(templates.find("RecoverInfos", SonType=str(son)), None)
    drop = base(son, snap, templates)
    if row is None or drop is None or int(row["Grade"]) > snap.character.grades:
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
    rows = (info(snap, templates, son, n) for son, n in sorted(pending(snap, now).items()))
    return pb.RecoverInfosMsg(recoverInfos=[r for r in rows if r is not None])
