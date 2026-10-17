"""Mensagens de missões (112) e itens (115) montadas a partir das entidades."""

from __future__ import annotations

from collections.abc import Iterable

from ...domain.models import Item, PlayerSnapshot, Quest
from ...protocol.messages import wartune_pb2 as pb
from ...templates.repository import GameTemplates
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
        strengthenGrade=item.strengthen_grade,
        join_1=item.join_1,
        join_2=item.join_2,
        join_3=item.join_3,
        join_4=item.join_4,
        randomSkill_1=item.random_skill,
        randomSkill_2=item.random_skill_2,
        randomSkill_3=item.random_skill_3,
        randomSkill_4=item.random_skill_4,
        randomSkill_5=item.random_skill_5,
        isNew=item.is_new,
        userId=player_id,
        property1="",
        isLocked=item.is_locked,
        mouldGrade=item.mould_grade,
        blessValue=0,
    )


def item_moved(change_type: int, object_id: int, pos: int, item: Item | None, player_id: int) -> pb.ItemMovedListMsg:
    """Uma entrada do 115; sem ``item`` = a posição ficou vazia."""
    msg = pb.ItemMovedListMsg()
    moved = msg.moved.add(changeType=change_type, changeObjId=object_id, changePos=pos)
    if item is not None:
        moved.item.CopyFrom(item_info(item, player_id))
    return msg


def smithy(templates: GameTemplates) -> pb.ItemSmithyMsg:
    """4184 do login: as receitas de composição liberadas (o oficial manda todos os Ids)."""
    return pb.ItemSmithyMsg(composeId=[int(r["Id"]) for r in templates.rows("ComposeTempInfos")])


def fashion_book(snap: PlayerSnapshot, templates: GameTemplates) -> pb.FashionMsg:
    """4542: o livro de moda (modas registradas, aparência ligada, avaliação) e, em ``fashionIds``,
    todas as modas do jogo (MasterType 1, SonType 109-112), como o oficial."""
    msg = pb.FashionMsg()
    sons = ("109", "110", "111", "112")
    msg.fashionIds.extend(
        int(r["TemplateId"])
        for r in templates.rows("ItemTempInfos")
        if r.get("MasterType") == "1" and r.get("SonType") in sons
    )
    for f in snap.fashions:
        msg.info.add(tempId=f.template_id, isSwitch=f.is_switch, appraisalSkill=f.appraisal_skill)
    return msg
