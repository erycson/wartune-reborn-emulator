"""Terras de mascote da fazenda: treino (12 começa, 13 cancela, 14 recolhe), comida (15) e guarda (16) do 15044.

(cliente) ``FarmOperateType`` 10-16; só 12-16 têm ``sendFarmOper`` (``FarmPetSelectMeun`` 12/16 com ``bagPos`` = pet,
``FarmPetLandView`` 13/14/15, ``PetShowView`` 13). O 10 (GIVE_POWER) e o 11 (TREE_PICK, a árvore vai pelo 5178)
nunca saem pelo 15044. ``FarmLandLayer``: 2 terras de mascote; ``FarmPetLandView.selectPet``: herói nível 50.
``PetLandInfo.canFeed``: a terra divide o treino em 10 partes; come quando a parte atual passa da última
alimentada (``state``) e até a 5; ``canGains``: agora >= ``endTime``. A resposta é o 4387 com ``petInfo`` (ou
``guardPetInfo``), nunca ``farmLandInfo``. O pet treinando leva ``PetInfoMsg.isPractice``.

TODO(inventado) (``game_settings.farm_pet_practice``, migração 0118): horas do treino, EXP por hora e % a mais por
comida (o cliente não mostra a conta; o ``templateId`` 12 do pedido é lido como as horas).
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta
from typing import Any

from ...domain.models import EventState, PlayerSnapshot
from ...protocol.messages import wartune_pb2 as pb
from ...templates.repository import GameTemplates
from .. import events as ev
from ..builders import login as b
from ..session import GameSession

S_FARM_LAND = 4387
START, CANCEL, COMPLETE, FEED, DEFENSE = 12, 13, 14, 15, 16
LANDS, NEED_GRADE, FEED_PARTS, FEED_MAX = 2, 50, 10, 5
KEY = "farm_pets"  # EventState: {"lands": {pos: {pet, begin, end, state, feeds}}, "guard": petId}
DEFAULT = {"hours": 12, "gp_per_hour": 1000, "feed_pct": 10}


def cfg(s: GameSession) -> dict[str, Any]:
    return DEFAULT | dict(s.ctx.world.settings.get("farm_pet_practice") or {})


def data(snap: PlayerSnapshot) -> dict[str, Any]:
    st = ev.peek(snap, KEY)
    raw: dict[str, Any] = json.loads(st.text) if st and st.text else {}
    return {"lands": {}, "guard": 0} | raw


def _store(snap: PlayerSnapshot, d: dict[str, Any], now: datetime) -> EventState:
    st = ev.state(snap, KEY, now)
    st.text, st.updated_at = json.dumps(d), now
    return st


def practicing(snap: PlayerSnapshot) -> set[int]:
    return {int(v["pet"]) for v in data(snap)["lands"].values()}


def guard_id(snap: PlayerSnapshot) -> int:
    """O guarda escolhido no 16, se o pet ainda existe (0 = o mascote em batalha, ``pets.guard_msg``)."""
    gid = int(data(snap)["guard"])
    return gid if any(p.id == gid for p in snap.pets) else 0


def land_msgs(snap: PlayerSnapshot, templates: GameTemplates) -> list[pb.FarmPetInfoMsg]:
    """As 2 terras (``petId`` 0 = vazia e aberta; o cliente só abre a terra que recebe), para o 4386 e o 4387."""
    from .pets import pet_star  # noqa: PLC0415  (pets -> player -> ... -> farm)

    uid, lands, out = snap.character.id or 0, data(snap)["lands"], []
    for pos in range(LANDS):
        msg = pb.FarmPetInfoMsg(userId=uid, pos=pos, petId=0)
        land = lands.get(str(pos))
        pet = next((p for p in snap.pets if land and p.id == land["pet"]), None)
        if land and pet is not None:
            msg.petId, msg.petTemplateId, msg.petName = pet.id or 0, pet.template_id, pet.name
            msg.quality = pet_star(pet, templates.get("PetTempInfos", pet.template_id) or {})
            msg.beginTime, msg.endTime, msg.state = land["begin"], land["end"], int(land["state"])
        out.append(msg)
    return out


def _reply(s: GameSession, owner: PlayerSnapshot, pos: int) -> None:
    lands = [m for m in land_msgs(owner, s.ctx.templates) if m.pos == pos]
    s.send(S_FARM_LAND, b.complete(pb.FarmInfoRspMsg(userId=owner.character.id or 0, petInfo=lands)))


def _region(land: dict[str, Any], now: datetime) -> int:
    begin, end = ev.parse_time(land["begin"]), ev.parse_time(land["end"])
    return int((now - begin) / ((end - begin) / FEED_PARTS))


def _can_feed(land: dict[str, Any], now: datetime) -> bool:
    """``PetLandInfo.canFeed``."""
    state = int(land["state"])
    return state < FEED_MAX and now < ev.parse_time(land["end"]) and _region(land, now) > state


def can_feed_any(snap: PlayerSnapshot, now: datetime) -> bool:
    return any(_can_feed(land, now) for land in data(snap)["lands"].values())


async def operate(s: GameSession, owner: PlayerSnapshot, msg: pb.FarmOperReqMsg, own: bool) -> None:
    """``owner`` é a fazenda (a própria ou, só no 15, a do amigo). Recusa: só o 4387 da terra como está."""
    from . import pets  # noqa: PLC0415

    snap, now, templates = s.snapshot, s.ctx.clock.now(), s.ctx.templates
    assert snap is not None
    d = data(owner)
    key = str(msg.pos)
    land = d["lands"].get(key)
    pet = next((p for p in snap.pets if p.id == (land["pet"] if land else msg.bagPos)), None) if own else None
    changed: list[object] = []
    ok = False
    if msg.opType == START and own and 0 <= msg.pos < LANDS and land is None and pet is not None:
        ok = snap.character.grades >= NEED_GRADE and not pet.is_fight and pet.id not in practicing(snap)
        if ok:
            hours = int(cfg(s)["hours"])
            end = now + timedelta(hours=hours)
            d["lands"][key] = {"pet": pet.id, "begin": b.fmt_time(now), "end": b.fmt_time(end), "state": 0,
                               "feeds": 0, "hours": hours}  # fmt: skip
    elif msg.opType == CANCEL and own and land is not None:
        ok = d["lands"].pop(key) is not None  # TODO(inventado): cancelar não dá EXP
    elif msg.opType == COMPLETE and own and land is not None and pet is not None:
        ok = now >= ev.parse_time(land["end"])
        if ok:
            c = cfg(s)
            gp = int(c["gp_per_hour"]) * int(land.get("hours", c["hours"]))
            gp = gp * (100 + int(c["feed_pct"]) * int(land["feeds"])) // 100
            pets.add_pet_gp(pet, templates, gp, snap.character.grades)
            del d["lands"][key]
            changed.append(pet)
    elif msg.opType == FEED and land is not None:
        ok = _can_feed(land, now)
        if ok:
            land["state"], land["feeds"] = min(_region(land, now), FEED_MAX), int(land["feeds"]) + 1
    elif msg.opType == DEFENSE and own and pet is not None:
        d["guard"], ok = pet.id, True
    if not ok:
        s.log.info("15044 recusado (terra de mascote)", op=msg.opType, pos=msg.pos, pet=msg.bagPos)
        if 0 <= msg.pos < LANDS:  # o guarda vem com pos -1: sem terra para devolver
            _reply(s, owner, msg.pos)
        return
    await s.ctx.characters.save(_store(owner, d, now), *changed)
    if msg.opType == DEFENSE:
        guard = pets.guard_msg(owner, templates)
        if guard is not None:
            s.send(S_FARM_LAND, b.complete(pb.FarmInfoRspMsg(userId=s.player_id, guardPetInfo=guard)))
        return
    _reply(s, owner, msg.pos)
    if not own and (other := s.ctx.online.get(owner.character.id or 0)) is not None:
        # o dono online vê como na rega/praga do amigo: 145 e o 4387 da terra. TODO(inventado): texto e type 2 (sem
        # captura da comida; o cliente não tem prêmio a quem dá comida, só a condição de evento PET_FEED 56)
        from .farm import S_FARM_LOG, _farm_log  # noqa: PLC0415

        other.send(S_FARM_LOG, _farm_log(s, "just fed your Sylph!", 2))
        _reply(other, owner, msg.pos)
    if own and msg.opType != FEED:
        s.send(pets.S_PETS, pets.pets_msg(snap, templates, [pet] if pet is not None else []))
