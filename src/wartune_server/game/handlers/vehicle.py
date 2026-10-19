"""Veículos (Daimon Trial): perfil e garagem do jogador; batalha de veículos fica de fora.

A cena VEHICLE (campanha 3001, ``com.map.vehicle``) não está no cliente decompilado, então a fila e o
mapa não têm formato conhecido; mandamos 4512 ``matchState=false`` como o oficial fora do horário e o
botão não abre a fila. Detalhes em ``docs/diversos.md``.
"""

from __future__ import annotations

from ...domain.models import Character
from ...protocol.messages import wartune_pb2 as pb
from ..builders import login as b
from ..router import router
from ..session import GameSession

S_PLAYER, S_STATE, S_PROFILE, S_LIST, S_TECH = 3, 4512, 4515, 4516, 4501
S_DIE_STATE, S_ATTACK = 4175, 4520
GARAGE = "1"  # VehicleObjectTempInfo.Type dos veículos da garagem (DaimonModel)
EXIT_NODE = 0  # WorldBossPlayerStateMsg.state fora de 6/7/8 = desceu do veículo/torre (CampaignArmy.exitNode)


def owned(c: Character) -> list[int]:
    return [int(v) for v in c.vehicles.split(",") if v]


def _profile(c: Character) -> pb.PlayerVehicleProfileMsg:
    # isFirst: o oficial manda true numa conta que já jogou (só turco: login.json #110); significado não conhecido
    return pb.PlayerVehicleProfileMsg(
        exp=c.vehicle_exp, score=c.vehicle_score, defaultVehicle=c.vehicle_default, isFirst=True
    )


def _garage(c: Character) -> pb.PlayerVehicleListMsg:
    # ponytail: id = templateId (o oficial manda um id de banco; o cliente só usa templateId)
    return pb.PlayerVehicleListMsg(vehicles=[pb.PlayerVehicleMsg(id=t, templateId=t) for t in owned(c)])


def login(s: GameSession) -> None:
    """Estado de veículos no login (só turco: login.json #83, #110-#112; o tutorial_en, nível 1-15, não manda
    nenhum dos quatro)."""
    assert s.snapshot is not None
    c = s.snapshot.character
    s.send(S_STATE, pb.MatchStateMsg(matchState=False))
    s.send(S_PROFILE, _profile(c))
    s.send(S_LIST, _garage(c))
    s.send(S_TECH, pb.SimplePropertyMsg(param1=0))  # ponytail: tecnologia de veículo não existe ainda


@router.on(8608)
async def quick_play(s: GameSession, _: object) -> None:
    # fila rápida da campanha 3001: sem a cena VEHICLE no cliente não há para onde mandar; o cliente
    # fica "procurando" até o 8609
    s.log.info("8608 fila de veículos indisponível")


@router.on(8609)
async def quick_play_cancel(s: GameSession, _: object) -> None:
    pass  # o cliente não espera resposta


@router.on(8611)
async def choose_vehicle(s: GameSession, msg: pb.CampaignReqMsg) -> None:
    c = s.snapshot.character if s.snapshot else None
    if c is None or msg.paraInt1 not in owned(c):
        s.log.info("8611 recusado", veiculo=msg.paraInt1)
        return
    c.vehicle_default = msg.paraInt1
    await s.ctx.characters.save(c)
    s.send(S_PROFILE, _profile(c))


@router.on(8619)
async def activate_vehicle(s: GameSession, msg: pb.SimplePropertyMsg) -> None:
    """Compra/ativa um veículo da garagem com diamante (``NeedDiamond``).

    ``NeedGrades`` é comparado com a EXP de veículo (valores 365/915 não cabem em nível).
    ponytail: ``param2`` (0/1 conforme uma flag do frame que não foi decompilado) é ignorado; paga
    sempre com diamante (point).
    """
    snap = s.snapshot
    assert snap is not None
    c = snap.character
    row = s.ctx.templates.get("VehicleObjectTempInfos", msg.param1)
    price, need = (int(row.get("NeedDiamond", 0)), int(row.get("NeedGrades", 0))) if row else (0, 0)
    if row is None or row.get("Type") != GARAGE or msg.param1 in owned(c) or c.vehicle_exp < need or c.point < price:
        s.log.info("8619 recusado", veiculo=msg.param1, diamante=c.point)
        return
    c.point -= price
    c.vehicles = ",".join(str(t) for t in [*owned(c), msg.param1])
    await s.ctx.characters.save(c)
    s.send(S_LIST, _garage(c))
    s.send(S_PROFILE, _profile(c))
    if price:
        from .login import player_info  # login importa este módulo

        s.send(S_PLAYER, b.complete(player_info(s, snap)))


@router.on(25111)
async def exit_vehicle_node(s: GameSession, msg: pb.WarFieldAttackMsg) -> None:
    """Sair do veículo/torre num mapa de guerra: 4175 com estado fora de 6/7/8 solta o jogador do nó."""
    state = pb.WorldBossPlayerStateMsg(armyId=s.player_id, state=EXIT_NODE, serverName=msg.defenceServerName)
    s.send(S_DIE_STATE, b.complete(pb.PlayerStateListMsg(playerState=[state])))


@router.on(25112)
async def vehicle_attack(s: GameSession, msg: pb.VehicleAttackReqMsg) -> None:
    """Skill de veículo em mapa de guerra (GvG): devolve a animação sem dano.

    ponytail: os mapas de guerra com veículos (CampaignInfo Types 9 / GvG) não existem; dano e alvos
    quando existirem (``VehicleSkillTempInfos``).
    """
    reply = pb.VehicleAttackRspMsg(
        skillId=msg.skillId,
        effectX=msg.effectX,
        effectY=msg.effectY,
        attackerId=s.player_id,
        serverName=msg.attackServerName,
        attackTyep=1,  # 1 = useSkill (CampaignSocketManger.__playerAttackHandler)
    )
    s.send(S_ATTACK, reply)
