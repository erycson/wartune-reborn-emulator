"""Herói: skills (dois conjuntos), talento, runas e pedidos que dependem de outros sistemas.
Ver ``docs/heroi-exercito.md``."""

from __future__ import annotations

from ...domain.models import BagType, Hero, Item, PlayerSnapshot
from ...protocol.messages import wartune_pb2 as pb
from ...services import ledger
from ...templates.repository import GameTemplates, Row
from .. import events as ev
from .. import rules
from ..arena import RUNE_POINT_KEY, rune_point_times
from ..builders import login as b
from ..builders.player import item_moved, quest_update
from ..castle import castle_yield
from ..router import router
from ..session import GameSession
from .player import _army, _player

S_SKILL, S_SKILL_RESET, S_TALENT_UP, S_TALENT, S_RUNE, S_ITEMS = 60, 61, 4430, 4431, 4495, 115
S_QUESTS = 112  # QuestUpdatedRspMsg
TALENT = "10"  # SkillTempInfo.MasterType do talento
TALENT_GRADE = "21"  # UpGradeTempInfo.Types: TemplateId = ouro, Data = EXP para o próximo grau
FREE_RESET_GRADE = 25  # SkillView: abaixo deste nível o reset de skill é grátis
TALENT_RESET_POINT = 895  # TalentView inglês: "armyII.viewII.talent.content01" com 895
SECOND_SKILL_GRADE = 38  # SkillView: _doubleSkillBtn.visible = grades >= 38
RUNE_BOOK, RUNE_EXP_ITEM = "302", 3020010  # SonType do livro de runa; item de EXP (Property2 = 50)
# RuneUpgradeView inglês: 50 + 10 x diamondIndex (usos do dia); DiamondTipTxt "Basic training earns 20 EXP"
RUNE_DIAMOND_BASE, RUNE_DIAMOND_STEP, RUNE_DIAMOND_EXP = 50, 10, 20
RUNE_MAX_GRADE = 10


def skill(templates: GameTemplates, template_id: int | str) -> Row | None:
    return templates.get("SkillTempInfos", int(template_id or 0))


def send_items(s: GameSession, changed: list[Item], deleted: list[Item]) -> None:
    moved = pb.ItemMovedListMsg()
    for item in deleted:
        moved.MergeFrom(item_moved(BagType.BAG, 0, item.pos, None, s.player_id))
    for item in changed:
        moved.MergeFrom(item_moved(BagType.BAG, 0, item.pos, item, s.player_id))
    if moved.moved:
        s.send(S_ITEMS, moved)


def leader(s: GameSession) -> tuple[PlayerSnapshot, Hero]:
    snap = s.snapshot
    assert snap is not None and snap.leader is not None
    return snap, snap.leader


@router.on(5185)
async def skill_upgrade(s: GameSession, msg: pb.HeroAddPointReqMsg) -> None:
    """Aprende/sobe uma skill (ou talento, MasterType 10) para ``skillTempId``: 1 ponto por grau.
    tutorial_en #1141-#1143 (30111): 150 e 60 {templateId, index, type 0}."""
    snap, hero = leader(s)
    templates = s.ctx.templates
    tpl = skill(templates, msg.skillTempId)
    talent = tpl is not None and tpl["MasterType"] == TALENT
    attr = "talent_script" if talent else ("skill_script2" if hero.skill_index == 1 else "skill_script")
    script = [x for x in getattr(hero, attr).split(",") if x]
    current = next(
        (x for x in script if (skill(templates, x) or {}).get("SonType") == (tpl or {}).get("SonType")), None
    )
    if tpl is None or (not talent and int(tpl["MasterType"]) != rules.job_type(snap.character.job)):
        s.log.info("5185 recusado", pedido=str(msg))
        return
    follows = (
        (skill(templates, current) or {}).get("NextTemplateId") == tpl["TemplateId"]
        if current
        else tpl["Grades"] == "1"
    )
    points = rules.talent_points(hero, templates) if talent else rules.skill_points(hero, templates, ",".join(script))
    if not follows or points < 1 or hero.grades < int(tpl["NeedPlayerGrade"]) or (talent and not hero.talent_grade):
        s.log.info("5185 recusado", pedido=str(msg), pontos=points)
        return
    if current is None:
        script.append(tpl["TemplateId"])
    else:
        script[script.index(current)] = tpl["TemplateId"]
    setattr(hero, attr, ",".join(script))
    rules.refresh_skill_point(hero, templates)
    await s.ctx.characters.save(hero)
    _army(s)
    s.send(S_SKILL, pb.UpdatedSkillMsg(templateId=msg.skillTempId, index=int(tpl["Index"]), type=int(talent)))


@router.on(5184)
async def skill_reset(s: GameSession, msg: pb.PayTypeMsg) -> None:
    """Reseta skills (type 0: grátis abaixo do nível 25, senão ResetSkill_NeedPay) ou talento (type
    1: 895 diamantes). payType 0 aceita diamante vinculado. Resposta: 61, 150 e 3."""
    snap, hero = leader(s)
    templates, c = s.ctx.templates, snap.character
    talent = msg.type == 1
    cost = (
        TALENT_RESET_POINT
        if talent
        else 0
        if hero.grades < FREE_RESET_GRADE
        else int(rules.config(templates, "ResetSkill_NeedPay", "100"))
    )
    spent = (
        ledger.pay(c, cost, bind=msg.payType == 0, reason="skill_reset", ref=str(msg.type), now=s.ctx.clock.now())
        if cost
        else None
    )
    if cost and spent is None:
        s.log.info("5184 recusado: sem diamante", pedido=str(msg))
        return
    if talent:
        hero.talent_script = ""
    elif hero.skill_index == 1:
        hero.skill_script2, hero.fast_key2 = templates.hero(hero.template_id).skill_script, ""
    else:
        hero.skill_script, hero.fast_key = templates.hero(hero.template_id).skill_script, ""
    rules.refresh_skill_point(hero, templates)
    await s.ctx.characters.save(c, hero, *([spent] if spent else []))
    s.send(S_SKILL_RESET, pb.UpdatedSkillMsg(resetResult=True, type=msg.type))
    _army(s)
    if cost:
        _player(s)


@router.on(5187)
async def talent_grade_up(s: GameSession, _: object) -> None:
    """Sobe o grau do talento (a partir do nível Talent_OpenGrade): custa ouro (TemplateId) e EXP
    (Data) do UpGrade Types 21 do próximo grau; cada grau dá 1 ponto. Resposta: 4430, 4431, 3, 109."""
    snap, hero = leader(s)
    templates, c = s.ctx.templates, snap.character
    row = rules.upgrade_row(templates, TALENT_GRADE, hero.talent_grade + 1)
    open_grade = int(rules.config(templates, "Talent_OpenGrade", "40"))
    gold, gp = (int(row["TemplateId"]), int(row["Data"])) if row else (0, 0)
    if row is None or hero.grades < open_grade or c.gold < gold or c.gp < gp:
        s.log.info("5187 recusado", talento=hero.talent_grade, ouro=c.gold, exp=c.gp)
        s.send(S_TALENT_UP, pb.TalentUpGradeMsg(upresult=False))
        return
    # ponytail: a EXP gasta sai da EXP do nível atual (c.gp); conferir com captura se o oficial
    # também baixa o total (e o nível) do jogador
    c.gold, c.gp, c.total_gp = c.gold - gold, c.gp - gp, c.total_gp - gp
    hero.talent_grade += 1
    await s.ctx.characters.save(c, hero)
    s.send(S_TALENT_UP, pb.TalentUpGradeMsg(upresult=True))
    talent = pb.HeroTalentMsg(userId=s.player_id, talentGrade=hero.talent_grade)
    talent.talentPoint = rules.talent_points(hero, templates)
    s.send(S_TALENT, talent)
    _player(s)
    castle_yield(s)


@router.on(8479)
async def active_second_skill(s: GameSession, msg: pb.PayTypeMsg) -> None:
    """Abre o segundo conjunto de skills no nível 38: Second_SkillPoint (995 nos templates) diamantes; payType 0
    aceita vinculado. O conjunto nasce com as skills iniciais. Resposta: 150 e 3."""
    snap, hero = leader(s)
    templates = s.ctx.templates
    cost = int(rules.config(templates, "Second_SkillPoint", "995"))
    if hero.active_second or hero.grades < SECOND_SKILL_GRADE:
        s.log.info("8479 recusado: já aberto ou abaixo do 38", pedido=str(msg))
        return
    spent = ledger.pay(
        snap.character, cost, bind=msg.payType == 0, reason="second_skill", ref="", now=s.ctx.clock.now()
    )
    if spent is None:
        s.log.info("8479 recusado", pedido=str(msg))
        return
    hero.active_second, hero.skill_script2 = True, templates.hero(hero.template_id).skill_script
    await s.ctx.characters.save(snap.character, hero, spent)
    _army(s)
    _player(s)


@router.on(8480)
async def change_skill(s: GameSession, msg: pb.HeroSkillChangeMsg) -> None:
    """Alterna o conjunto de skills em uso (0/1). Resposta: 150 (skillIndex, skillScript, fastKey)."""
    _, hero = leader(s)
    if msg.index not in (0, 1) or (msg.index == 1 and not hero.active_second):
        s.log.info("8480 recusado", pedido=str(msg))
        return
    hero.skill_index = msg.index
    rules.refresh_skill_point(hero, s.ctx.templates)
    await s.ctx.characters.save(hero)
    _army(s)


@router.on(5170)
async def reset_attribute_points(s: GameSession, _: object) -> None:
    """Redistribuir atributos: aqui os pontos de atributo são todos aplicados automaticamente por
    nível (rules.GROWTH), não há o que devolver; responde o herói atual. Nenhuma tela chama."""
    _army(s)


@router.on(5018)
async def player_grade_box(s: GameSession, msg: object) -> None:
    """``sendBoxNovice`` (BoxBoxMsg) nunca é chamado pelo cliente: só registra."""
    s.log.info("5018 ignorado (código morto no cliente)", pedido=str(msg))


@router.on(8548)
async def guild_war_player_fight(s: GameSession, msg: pb.GuildMsg) -> None:
    """Ataque a jogador na guerra de guildas (gvgPlayerFight): depende de GvG e da batalha PvP."""
    s.log.info("8548 sem guerra de guildas", pedido=str(msg))


# --- runas ---------------------------------------------------------------------------------------


def runes(hero: Hero) -> dict[int, list[int]]:
    """runeId -> [gp, swallowCount], na ordem gravada."""
    return {int(r.split(":")[0]): [int(x) for x in r.split(":")[1:]] for r in hero.runes.split(",") if r}


def set_runes(hero: Hero, learned: dict[int, list[int]]) -> None:
    hero.runes = ",".join(f"{rid}:{gp}:{sw}" for rid, (gp, sw) in learned.items())


def rune_reply(s: GameSession, hero: Hero, op: int, ok: bool) -> None:
    """``count`` = usos do diamante hoje (ArmyManager: vira o ``diamondIndex`` quando > 0)."""
    assert s.snapshot is not None
    msg = pb.HeroRuneOpMsg(opType=op, opResult=ok, count=rune_point_times(s.snapshot, s.ctx.clock.now()))
    msg.runeInfo.CopyFrom(b.rune_msg(hero, s.player_id))
    s.send(S_RUNE, msg)


@router.on(8605)
async def rune_op(s: GameSession, msg: pb.HeroRuneOpMsg) -> None:
    """opType 1 aprende (gasta o livro SonType 302 com Property1 = RuneType em learnRunePos), 2 sobe
    (count x item 3020010 de 50 EXP; count 0 = diamante, 50 + 10 por uso no dia e 20 EXP), 3 equipa
    (runeKey "id,id,").
    Resposta 4495 {opType, opResult, runeInfo}; 115 quando gasta item."""
    snap, hero = leader(s)
    templates = s.ctx.templates
    learned = runes(hero)
    tpl = templates.get("RuneTempInfos", msg.runeId)
    open_grade = int(rules.config(templates, "OpenRuneGrade", "35"))
    if hero.grades < open_grade or msg.opType not in (1, 2, 3):
        s.log.info("8605 recusado", pedido=str(msg))
        rune_reply(s, hero, msg.opType, False)
        return
    if msg.opType == 1:
        await _rune_learn(s, snap, hero, tpl, learned, msg)
    elif msg.opType == 2:
        await _rune_upgrade(s, snap, hero, tpl, learned, msg)
    else:
        keys = [k for k in msg.runeKey.split(",") if k]
        ids = [int(k) for k in keys if k.lstrip("-").isdigit() and int(k) != -1]
        slots = 2 if hero.grades >= int(rules.config(templates, "CarryTwoRune", "40")) else 1
        if len(keys) > 2 or len(ids) > slots or len(set(ids)) != len(ids) or any(i not in learned for i in ids):
            rune_reply(s, hero, 3, False)
            return
        hero.rune_key = msg.runeKey
        await s.ctx.characters.save(hero)
        rune_reply(s, hero, 3, True)


async def _rune_learn(
    s: GameSession,
    snap: PlayerSnapshot,
    hero: Hero,
    tpl: Row | None,
    learned: dict[int, list[int]],
    msg: pb.HeroRuneOpMsg,
) -> None:
    templates = s.ctx.templates
    book = next((i for i in snap.items if (i.bag_type, i.pos) == (BagType.BAG, msg.learnRunePos)), None)
    book_tpl = templates.get("ItemTempInfos", book.template_id) if book else None
    same_type = any(
        (templates.get("RuneTempInfos", r) or {}).get("RuneType") == (tpl or {}).get("RuneType") for r in learned
    )
    ok = tpl is not None and tpl["RuneGrade"] == "1" and book is not None and book_tpl is not None and not same_type
    ok = ok and book_tpl.get("SonType") == RUNE_BOOK and book_tpl.get("Property1") == tpl.get("RuneType")  # type: ignore[union-attr]
    job = (tpl or {}).get("Job", "0")
    if not ok or (job != "0" and str(rules.job_type(snap.character.job)) not in job.split(",")):
        s.log.info("8605 aprender recusado", pedido=str(msg))
        rune_reply(s, hero, 1, False)
        return
    assert book is not None and tpl is not None
    changed, deleted = rules.take_items(snap, [book], 1)
    learned[int(tpl["TemplateId"])] = [0, 0]
    set_runes(hero, learned)
    quests = rules.quest_event(snap, templates, rules.RUNE_STUDY, int(tpl["RuneType"]), 1)
    await s.ctx.characters.save(hero, *changed, *quests, delete=tuple(deleted))
    send_items(s, changed, deleted)
    rune_reply(s, hero, 1, True)
    if quests:
        s.send(S_QUESTS, quest_update(quests, rules.quest_bitmap(snap)))
    _army(s)


async def _rune_upgrade(
    s: GameSession,
    snap: PlayerSnapshot,
    hero: Hero,
    tpl: Row | None,
    learned: dict[int, list[int]],
    msg: pb.HeroRuneOpMsg,
) -> None:
    templates, c = s.ctx.templates, snap.character
    exp_item = templates.get("ItemTempInfos", RUNE_EXP_ITEM) or {}
    per_item = int(exp_item.get("Property2", 50))
    stock = [i for i in snap.items if i.bag_type == BagType.BAG and i.template_id == RUNE_EXP_ITEM]
    nxt = templates.get("RuneTempInfos", int(tpl["NextRuneId"] or 0)) if tpl else None
    if tpl is None or nxt is None or msg.runeId not in learned or int(tpl["RuneGrade"]) >= RUNE_MAX_GRADE:
        rune_reply(s, hero, 2, False)
        return
    gp, swallow = learned[msg.runeId]
    extra: list[object] = []
    if msg.count > 0:
        if sum(i.count for i in stock) < msg.count:
            rune_reply(s, hero, 2, False)
            return
        gain, (changed, deleted) = per_item * msg.count, rules.take_items(snap, stock, msg.count)
    elif (
        spent := ledger.pay(
            c,
            RUNE_DIAMOND_BASE + RUNE_DIAMOND_STEP * rune_point_times(snap, s.ctx.clock.now()),
            bind=False,
            reason="rune_exp",
            ref=str(msg.runeId),
            now=s.ctx.clock.now(),
        )
    ) is not None:
        # ponytail: sem o bônus 2x/5x/10x/20x da DiamondTipTxt (o cliente não diz a chance); mudar com captura
        used = ev.daily(snap, RUNE_POINT_KEY, s.ctx.clock.now())
        used.value, used.updated_at = used.value + 1, s.ctx.clock.now()
        gain, changed, deleted, extra = RUNE_DIAMOND_EXP, [], [], [used, spent]
    else:
        rune_reply(s, hero, 2, False)
        return
    gp, swallow = gp + gain, swallow + gain
    rune_id = msg.runeId
    while nxt is not None and gp >= int(nxt["NeedGp"]) and hero.grades >= int(nxt["NeedGrade"]):
        gp -= int(nxt["NeedGp"])
        rune_id = int(nxt["TemplateId"])
        nxt = templates.get("RuneTempInfos", int(nxt["NextRuneId"] or 0))
    if nxt is not None:
        gp = min(gp, int(nxt["NeedGp"]))  # parado no limite do nível do herói (UpgradeTipTxt2)
    del learned[msg.runeId]
    learned[rune_id] = [gp, swallow]
    hero.rune_key = ",".join(str(rune_id) if k == str(msg.runeId) else k for k in hero.rune_key.split(","))
    set_runes(hero, learned)
    new_tpl = templates.get("RuneTempInfos", rune_id)
    assert new_tpl is not None
    # 78: o grau que o símbolo chegou (o maior); 77: pedras da bolsa gastas, uma por pedra (dedução: QuestTemps
    # 186 "Consume Small Runestone" e 916 "by consuming Runestones" é dar a pedra ao símbolo; o cliente só faz
    # checkCount)
    quests = rules.quest_event(snap, templates, rules.RUNE_GRADE, int(new_tpl["RuneType"]), int(new_tpl["RuneGrade"]))
    if msg.count > 0:
        quests += rules.quest_event(snap, templates, rules.RUNE_COMBINE, RUNE_EXP_ITEM, msg.count)
    await s.ctx.characters.save(c, hero, *changed, *quests, *extra, delete=tuple(deleted))
    send_items(s, changed, deleted)
    rune_reply(s, hero, 2, True)
    if quests:
        s.send(S_QUESTS, quest_update(quests, rules.quest_bitmap(snap)))
    if not msg.count:
        _player(s)
    _army(s)
