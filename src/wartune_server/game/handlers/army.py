"""Exército e tropas: recrutar, colocar no exército, dispensar, evoluir, especialidades, formação e
teleporte no mapa externo. Ver ``docs/heroi-exercito.md``.

O exército tem um único slot de tropa (``sites`` 0). Cada tipo (SonType) é uma linha ``Pawn`` com
os soldados no castelo e no exército; o template da linha é o nível atual daquele tipo.
"""

from __future__ import annotations

import math
import random

from ...domain.models import Pawn, PlayerSnapshot
from ...protocol.messages import wartune_pb2 as pb
from ...services import ledger
from ...templates.repository import GameTemplates, Row
from .. import rules
from ..builders import login as b
from ..builders.army import castle_pawns, pawn_msg
from ..builders.player import quest_update
from ..castle import castle_yield
from ..router import router
from ..session import GameSession
from .player import _army, _player

S_CASTLE_PAWNS, S_ARMY_EDIT, S_PAWN, S_QUESTS, S_ALERT, S_CHAT = 100, 93, 116, 112, 111, 83
S_TELEPORT, S_TELEPORT_FAIL, S_ARMY_POS, S_TEAM_POS = 4237, 4263, 4241, 4186
RECRUIT, PAWN_LEVEL, FORMATION, COMPREHEND = 3, 10, 34, 52  # QuestCondictionInfos.CondictionType
PAWN_UPGRADE = "1"  # UpGradeTempInfo.Types: TemplateId = próximo nível, Data = custo em Daru
SPECIAL_BLESS = "16"  # UpGradeTempInfo.Types: Data = bênção máxima no grau da especialidade
COMPREHEND_COST = 1_000_000  # Daru (PawnSpecialAbilityFrame)
CHANGE_POINT, CHANGE_SOUL, CHANGE_LEVEL = 200, 2_000_000, 10  # PawnAbilityConvertFrame
TELEPORT_ENERGY, TELEPORT_POINT = 100, 100  # TransmitHandler


def pawn_template(templates: GameTemplates, template_id: int) -> Row | None:
    return templates.get("PawnTempInfos", template_id)


def pawn_of(snap: PlayerSnapshot, son_type: int) -> Pawn | None:
    return next((p for p in snap.pawns if p.template_id // 100 == son_type), None)


def current_pawn(s: GameSession, template_id: int) -> tuple[Pawn, Row] | None:
    """Linha do tipo pedido, criada em memória no nível 1 se o jogador ainda não tem; recusa um
    template que não é o nível atual daquele tipo (o cliente sempre manda o atual)."""
    snap = s.snapshot
    assert snap is not None
    son_type = template_id // 100
    pawn = pawn_of(snap, son_type) or Pawn(snap.character.id or 0, son_type * 100 + 1)
    tpl = pawn_template(s.ctx.templates, pawn.template_id)
    return (pawn, tpl) if tpl is not None and pawn.template_id == template_id else None


def keep(snap: PlayerSnapshot, pawn: Pawn) -> None:
    if pawn not in snap.pawns:
        snap.pawns.append(pawn)


def barracks_grade(snap: PlayerSnapshot, templates: GameTemplates) -> tuple[int, Row | None]:
    row = rules.building_row(snap, templates, rules.BARRACKS)
    return (int(row["BuildingGrade"]), row) if row else (0, None)


def send_quests(s: GameSession, quests: list) -> None:  # type: ignore[type-arg]
    assert s.snapshot is not None
    if quests:
        s.send(S_QUESTS, quest_update(quests, rules.quest_bitmap(s.snapshot)))


@router.on(5155)
async def recruit(s: GameSession, msg: pb.ArmyPawnInfoMsg) -> None:
    """Recruta no castelo: ouro = GoldConsume por soldado (menos o desconto Property4 do quartel),
    população = NeedPopulation por soldado. tutorial_en #653-#659: 109, 112, 109, 100, 111."""
    snap, templates = s.snapshot, s.ctx.templates
    assert snap is not None
    found, n = current_pawn(s, msg.tempateId), msg.ownPawns
    used, cap = rules.population(snap, templates, s.ctx.clock.now())
    grade, barracks = barracks_grade(snap, templates)
    if found is None or barracks is None or n <= 0:
        s.log.info("5155 recusado", pedido=str(msg))
        return
    pawn, tpl = found
    unlocked = int(barracks["TemplateId"]) >= int(tpl["NeedBuilding"] or 0)
    discount = int(barracks.get("Property4", 0))
    cost = math.ceil(n * int(tpl["GoldConsume"]) * (100 - discount) / 100)
    if not unlocked or used + n * int(tpl["NeedPopulation"]) > cap or snap.character.gold < cost:
        s.log.info("5155 recusado", pedido=str(msg), ouro=snap.character.gold, populacao=(used, cap))
        return
    snap.character.gold -= cost
    castle_yield(s)  # (visto) oficial_20261023-171155-1 #5471: o 1º 109 já pago, com a população de antes
    pawn.castle_count += n
    keep(snap, pawn)
    quests = rules.quest_event(snap, templates, RECRUIT, int(tpl["MasterType"]), n)
    await s.ctx.characters.save(snap.character, pawn, *quests)

    send_quests(s, quests)
    castle_yield(s)
    s.send(S_CASTLE_PAWNS, castle_pawns(snap, templates, [pawn]))
    # texto do oficial inglês (111, tutorial_en #659 e oficial_20261023-171155-1 #5474: "Successfully Recruited 1,166
    # Lancer")
    s.send(S_ALERT, pb.ChatChannelMsg(channel=7, encodeMsg=f"Successfully Recruited {n:,} {tpl['PawnName']}"))


@router.on(5156)
async def army_edit(s: GameSession, msg: pb.ArmyPawnInfoMsg) -> None:
    """Põe ``ownPawns`` soldados do tipo no exército (o resto volta ao castelo). Limite: liderança
    do herói (totalConatArmy). tutorial_en #665-#669: 150, 93, 100; o 100 leva só a tropa pedida, mesmo quando a que
    estava no exército volta ao castelo (#2301-#2304)."""
    snap, templates = s.snapshot, s.ctx.templates
    assert snap is not None and snap.leader is not None
    pawn = pawn_of(snap, msg.tempateId // 100)
    total = pawn.castle_count + pawn.army_count if pawn else 0
    leadership = rules.leader_stats(snap, templates, s.ctx.clock.now()).total["ConatArmy"]
    if pawn is None or pawn.template_id != msg.tempateId or msg.sites != 0 or not 0 <= msg.ownPawns <= total:
        s.log.info("5156 recusado", pedido=str(msg))
        return
    if msg.ownPawns > leadership:
        s.log.info("5156 recusado: liderança", pedido=str(msg), lideranca=leadership)
        return
    changed = [p for p in snap.pawns if p is not pawn and p.army_count > 0]  # o slot é um só
    for other in changed:
        other.castle_count, other.army_count = other.castle_count + other.army_count, 0
    pawn.castle_count, pawn.army_count = total - msg.ownPawns, msg.ownPawns
    await s.ctx.characters.save(pawn, *changed)

    _army(s)
    tpl = pawn_template(templates, pawn.template_id)
    assert tpl is not None
    s.send(S_ARMY_EDIT, pb.ArmyEditRspMsg(armyPawn=[pawn_msg(pawn, tpl, snap.character.id or 0, pawn.army_count)]))
    s.send(S_CASTLE_PAWNS, castle_pawns(snap, templates, [pawn]))


@router.on(5157)
async def dismiss(s: GameSession, msg: pb.ArmyPawnInfoMsg) -> None:
    """Dispensa soldados do castelo (sem reembolso). Resposta: 100 e 109 (população)."""
    snap = s.snapshot
    assert snap is not None
    pawn = pawn_of(snap, msg.tempateId // 100)
    if pawn is None or pawn.template_id != msg.tempateId or not 0 < msg.ownPawns <= pawn.castle_count:
        s.log.info("5157 recusado", pedido=str(msg))
        return
    pawn.castle_count -= msg.ownPawns
    await s.ctx.characters.save(pawn)
    s.send(S_CASTLE_PAWNS, castle_pawns(snap, s.ctx.templates, [pawn]))
    castle_yield(s)


def send_pawn(s: GameSession, pawn: Pawn) -> None:
    """116: o cliente atualiza todas as tropas daquele SonType (castelo e exército)."""
    tpl = pawn_template(s.ctx.templates, pawn.template_id)
    assert tpl is not None
    s.send(S_PAWN, pawn_msg(pawn, tpl, 0, pawn.castle_count))


@router.on(5158)
async def upgrade(s: GameSession, msg: pb.ArmyPawnInfoMsg) -> None:
    """Evolui o tipo para NextLevelTemplateId: custa Daru (UpGrade Types 1) e exige quartel no nível
    seguinte. tutorial_en #2089-#2094: 3, 116, 150 e o 83 "Lancer successfully upgraded to Lvl. 2" (sem 109 nem 112:
    a missão 101 "Upgrade Lancers" só aparece no 5014, #2179-#2180). Fechando a tarefa do guia de 7 dias (tropa no
    nível 10), o 4638 vem entre o 116 e o 150 (oficial_20261023-171155-1 #1676-#1682; lá um 3 a mais só com o
    ``fightingCapacity`` novo, que aqui já vai no primeiro)."""
    snap, templates = s.snapshot, s.ctx.templates
    assert snap is not None and snap.leader is not None
    found = current_pawn(s, msg.tempateId)
    nxt = pawn_template(templates, int(found[1]["NextLevelTemplateId"] or 0)) if found else None
    cost_row = (
        next(templates.find("UpGradeTempInfos", Types=PAWN_UPGRADE, TemplateId=nxt["TemplateId"]), None)
        if nxt
        else None
    )
    grade, _ = barracks_grade(snap, templates)
    if found is None or nxt is None or cost_row is None:
        s.log.info("5158 recusado", pedido=str(msg))
        return
    pawn, tpl = found
    cost, level = int(cost_row["Data"]), int(nxt["Level"])
    # PawnLevelUpFrame.__upgradeHandler só confere o Daru e o quartel; o "nível do herói - 3" do ArmyManager é só a
    # dica visual (visto: oficial_20261023-171155-1 #4891 sobe a tropa 10 com o herói 13, #5899 a 11 com o 14)
    if grade < level or snap.character.strategy < cost:
        s.log.info("5158 recusado", pedido=str(msg), quartel=grade, daru=snap.character.strategy)
        return
    snap.character.strategy -= cost
    pawn.template_id = int(nxt["TemplateId"])
    keep(snap, pawn)
    quests = rules.quest_event(snap, templates, PAWN_LEVEL, int(tpl["MasterType"]), level)
    await s.ctx.characters.save(snap.character, pawn, *quests)

    _player(s)
    send_pawn(s, pawn)
    from .events import refresh_serven  # events importa player, que importa este módulo

    refresh_serven(s)
    _army(s)
    s.send(S_CHAT, pb.ChatChannelMsg(channel=3, encodeMsg=f"{nxt['PawnName']} successfully upgraded to Lvl. {level}"))


@router.on(8580)
async def pawn_change(s: GameSession, msg: pb.PawnChangeMsg) -> None:
    """Troca as especialidades de dois tipos de nível >= 10: 200 diamantes (payType 1; 3 = vinculado
    primeiro) ou 2.000.000 de Daru (2). Resposta: 3 e 116 de cada tropa (dedução)."""
    snap = s.snapshot
    assert snap is not None
    a, t = current_pawn(s, msg.curPawnTempId), current_pawn(s, msg.tarPawnTempId)
    ok = a is not None and t is not None and a[0] is not t[0] and a[0].specials != ""
    ok = ok and all(int(x[1]["Level"]) >= CHANGE_LEVEL for x in (a, t) if x)
    c, spent = snap.character, None
    if ok and msg.payType != 2:
        spent = ledger.pay(c, CHANGE_POINT, bind=msg.payType == 3, reason="pawn_change", ref="", now=s.ctx.clock.now())
    if not (ok and (rules.pay_soul(c, CHANGE_SOUL) if msg.payType == 2 else spent)):
        s.log.info("8580 recusado", pedido=str(msg))
        return
    assert a is not None and t is not None
    a[0].specials, t[0].specials = t[0].specials, a[0].specials
    keep(snap, a[0])
    keep(snap, t[0])
    await s.ctx.characters.save(snap.character, a[0], t[0], *([spent] if spent else []))
    _player(s)
    send_pawn(s, a[0])
    send_pawn(s, t[0])
    _army(s)


MAX_SPECIAL_GRADE = 10  # PawnSpecialAbilityFrame.helpContent: "The highest level specialty is level 10"
FIGHT_ROWS = (1, 3)  # AllocateView: _frontRowIndex 1, _backRowIndex 3 ("fightPos must be 1 or 3")


def special_pick(templates: GameTemplates, master_type: str, grade: int, exact: bool = False) -> Row | None:
    """Sorteio ponderado (TakeRandom) entre as especialidades do tipo de tropa até ``grade`` (só dele com ``exact``)."""
    rows = templates.find("SpecialTempInfos", PawnMasterType=master_type)
    pool = [r for r in rows if (int(r["Grades"]) == grade if exact else int(r["Grades"]) <= grade)]
    if not pool:
        return None
    return random.choices(pool, weights=[int(r["TakeRandom"]) or 1 for r in pool])[0]


@router.on(8455)
async def comprehend(s: GameSession, msg: pb.ComprehendMsg) -> None:
    """Sorteia uma especialidade (1.000.000 de Daru) em ``comprehednTempIds``; cada tentativa enche a
    bênção, e com ela cheia o sorteio dá um grau acima, 100% (PawnSpecialAbilityFrame.helpContent inglês).
    Resposta: 3 e 116."""
    snap, templates = s.snapshot, s.ctx.templates
    assert snap is not None
    found = current_pawn(s, msg.templateId)
    if found is None or snap.character.strategy < COMPREHEND_COST:
        s.log.info("8455 recusado", pedido=str(msg))
        return
    pawn, tpl = found
    saved = templates.get("SpecialTempInfos", int(pawn.specials)) if pawn.specials else None
    grade = int(saved["Grades"]) if saved else 1
    bless = next(templates.find("UpGradeTempInfos", Types=SPECIAL_BLESS, Grades=grade), None)
    # ponytail: o sorteio comum vai até o grau atual (o texto só diz "chance" de subir); mudar com captura
    full = bless is not None and pawn.bless + 1 >= int(bless["Data"]) and grade < MAX_SPECIAL_GRADE
    pick = special_pick(templates, tpl["MasterType"], grade + 1 if full else grade, exact=full)
    if pick is None:
        s.log.info("8455 recusado: sem especialidade", pedido=str(msg))
        return
    snap.character.strategy -= COMPREHEND_COST
    pawn.comprehend = pick["TemplateId"]
    pawn.bless = 0 if full else pawn.bless + 1
    keep(snap, pawn)
    quests = rules.quest_event(snap, templates, COMPREHEND, 0, 1)
    await s.ctx.characters.save(snap.character, pawn, *quests)
    _player(s)
    send_pawn(s, pawn)
    send_quests(s, quests)


@router.on(8456)
async def save_special(s: GameSession, msg: pb.ComprehendMsg) -> None:
    """Troca a especialidade pela sorteada no 8455; subindo de grau a bênção zera ("Blessing levels are reset
    after each specialty level upgrade"). Resposta: 116 e 150 (atributos da tropa)."""
    snap, templates = s.snapshot, s.ctx.templates
    assert snap is not None
    found = current_pawn(s, msg.templateId)
    if found is None or not found[0].comprehend:
        s.log.info("8456 recusado", pedido=str(msg))
        return
    pawn = found[0]

    def grade(special: str) -> int:
        return int((templates.get("SpecialTempInfos", int(special)) or {}).get("Grades", 0)) if special else 0

    if grade(pawn.comprehend) > grade(pawn.specials):
        pawn.bless = 0
    pawn.specials, pawn.comprehend = pawn.comprehend, ""
    await s.ctx.characters.save(pawn)
    send_pawn(s, pawn)
    _army(s)


@router.on(8276)
async def army_pos_edit(s: GameSession, msg: pb.ArmyFightPosEditMsg) -> None:
    """Formação (AllocateView): herói e tropa na fileira da frente (1) ou de trás (3). Resposta: 150."""
    snap = s.snapshot
    assert snap is not None and snap.leader is not None
    pawn = rules.army_pawn(snap)
    valid = FIGHT_ROWS
    if msg.userId != s.player_id or msg.heroPos not in valid or msg.heroPos == msg.pawnPos:
        s.log.info("8276 recusado", pedido=str(msg))
        return
    if pawn is not None and msg.pawnPos not in valid:
        s.log.info("8276 recusado", pedido=str(msg))
        return
    snap.leader.fight_pos = msg.heroPos
    if pawn is not None:
        pawn.fight_pos = msg.pawnPos
    quests = rules.quest_event(snap, s.ctx.templates, FORMATION, 0, 1)
    await s.ctx.characters.save(snap.leader, *(x for x in (pawn,) if x), *quests)
    _army(s)
    send_quests(s, quests)


def team_pos(s: GameSession) -> pb.ArmyFightPosEditListMsg:
    assert s.snapshot is not None and s.snapshot.leader is not None
    msg = pb.ArmyFightPosEditListMsg()
    msg.armyFightPos.add(userId=s.player_id, heroPos=s.snapshot.leader.fight_pos)
    return msg


@router.on(8277)
async def campaign_pos_edit(s: GameSession, msg: pb.ArmyFightPosEditListMsg) -> None:
    """Formação da equipe na sala de campanha. ponytail: só a posição do próprio herói é gravada;
    as dos outros membros dependem do sistema de salas em grupo. Resposta: 4186."""
    snap = s.snapshot
    assert snap is not None and snap.leader is not None
    mine = next((p for p in msg.armyFightPos if p.userId == s.player_id), None)
    if mine is not None and 1 <= mine.heroPos <= 9:
        snap.leader.fight_pos = mine.heroPos
        await s.ctx.characters.save(snap.leader)
    s.send(S_TEAM_POS, team_pos(s))


@router.on(8278)
async def campaign_pos_request(s: GameSession, _: object) -> None:
    s.send(S_TEAM_POS, team_pos(s))


@router.on(8326)
async def teleport(s: GameSession, msg: pb.ArmyPositionMsg) -> None:
    """Teleporte no mapa externo: 100 de energia do castelo, ou 100 diamantes sem energia (payType 1
    diamante, 2 vinculado). Resposta 4237 (posição + energia restante); recusa 4263.
    ponytail: a posição do exército no mapa externo não é gravada (sistema do mapa externo)."""
    snap = s.snapshot
    assert snap is not None and snap.castle is not None
    castle, c = snap.castle, snap.character
    if not (0 <= msg.posX < 1000 and 0 <= msg.posY < 1000):
        s.send(S_TELEPORT_FAIL)
        return
    spent = None
    if castle.energy >= TELEPORT_ENERGY:
        castle.energy -= TELEPORT_ENERGY
    elif (
        spent := ledger.pay(c, TELEPORT_POINT, bind=msg.payType == 2, reason="teleport", ref="", now=s.ctx.clock.now())
    ) is None:
        s.send(S_TELEPORT_FAIL)
        return
    await s.ctx.characters.save(c, castle, *([spent] if spent else []))
    s.send(S_TELEPORT, pb.ArmyPositionMsg(posX=msg.posX, posY=msg.posY, mapId=castle.map_id, leftEnergy=castle.energy))
    _player(s)


@router.on(8328)
async def army_position(s: GameSession, _: object) -> None:
    """Posição do exército no mapa externo (4241): ao lado do castelo, como no 150."""
    snap = s.snapshot
    assert snap is not None and snap.castle is not None
    army = b.army_msg(snap, snap.castle, pb.SimpleHeroInfoMsg(), 0)
    s.send(S_ARMY_POS, pb.ArmyPositionMsg(mapId=army.mapId, posX=army.curPosX, posY=army.curPosY))
