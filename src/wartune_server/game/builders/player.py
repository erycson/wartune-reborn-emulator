"""Mensagens de missões (112) e itens (115) montadas a partir das entidades."""

from __future__ import annotations

from collections.abc import Iterable

from ...domain.models import Item, Quest
from ...protocol.messages import wartune_pb2 as pb
from .login import NEVER, QUEST_SITE_LEN, fmt_time

ITEM_ADDED = 1  # ItemMoveUpdateMsg.changeType: bolsa (1) ou herói (4), igual ao bagType de destino


def quest_info(q: Quest) -> pb.QuestInfo:
    return pb.QuestInfo(
        templateId=q.template_id,
        isComplete=q.completed,
        condition_1=q.progress,
        condition_2=0,
        condition_3=0,
        condition_4=0,
        completedDate=fmt_time(q.completed_at) if q.completed_at else NEVER,
        repeatFinish=1,
        isAccept=not q.completed,
        isSelect=True,
        addDate=fmt_time(q.added_at),
    )


def quest_update(quests: Iterable[Quest], states: bytes) -> pb.QuestUpdatedRspMsg:
    msg = pb.QuestUpdatedRspMsg(statesLength=QUEST_SITE_LEN, states=states)
    msg.quest.extend(quest_info(q) for q in quests)
    return msg


def item_info(item: Item, player_id: int) -> pb.ItemInfoMsg:
    # mesmos campos que o oficial manda (sem complete(): ele omite attack/defence/strength...)
    return pb.ItemInfoMsg(
        id=item.id or 0,
        templateId=item.template_id,
        pos=item.pos,
        exist=True,
        objectId=item.object_id,
        bagType=item.bag_type,
        bind=True,
        used=False,
        validDate=0,
        beginDate=NEVER,
        count=item.count,
        strengthenGrade=0,
        join_1=-1,
        join_2=-1,
        join_3=-1,
        join_4=-1,
        randomSkill_1=item.random_skill,
        randomSkill_2=0,
        randomSkill_3=0,
        randomSkill_4=0,
        randomSkill_5=0,
        isNew=item.is_new,
        userId=player_id,
        property1="",
        isLocked=False,
        mouldGrade=0,
        blessValue=0,
    )


def item_moved(change_type: int, object_id: int, pos: int, item: Item | None, player_id: int) -> pb.ItemMovedListMsg:
    """Uma entrada do 115; sem ``item`` = a posição ficou vazia."""
    msg = pb.ItemMovedListMsg()
    moved = msg.moved.add(changeType=change_type, changeObjId=object_id, changePos=pos)
    if item is not None:
        moved.item.CopyFrom(item_info(item, player_id))
    return msg
