"""Moda: esconder (5008), livro de moda (8625/8631/8781), provador (8595) e composição na bancada (8594). A compra
de moda (8592) fica na loja. Ver ``docs/itens.md``.
"""

from __future__ import annotations

import random
from typing import Any

from ...domain.models import BagType, FashionBook, Item, PlayerSnapshot
from ...protocol.messages import wartune_pb2 as pb
from ...templates.repository import GameTemplates
from .. import bag, rules, space
from ..builders.player import fashion_book
from ..castle import castle_yield
from ..router import router
from ..session import GameSession
from .player import S_ITEMS, _army, _player
from .shop import send

S_APPEARANCE, S_FASHION_COMPOSE, S_FASHION_BOOK, S_ALERT = 149, 4487, 4542, 111
HIDE, SHOW = 1, 2  # HeroHideFashionReqMsg.hide; 0 = só pedir a aparência (sendChangeHeroInfo)
FASHION_SONS = (rules.WING, rules.HAT, rules.FASHION_CLOTH, rules.FASHION_ARM)
WILDCARD, CHARM = 208020, 208021  # "Fashion Core" (curinga) e "Good Luck Charm" (ItemTempInfos)
IDENTIFY_RATES = (0, 20, 30, 40, 50, 60)  # (cliente) FashionModel.getSuccessRateForIdentityBook, por TransformId
IDENTIFY_GRADE = 27  # (cliente) FashionSwitchItem: "BattleGuardView.needGrade" 27
COMPOSE_GOLD = 10000  # (cliente) FashionComposeView.needGold: (nível1 + nível2) x 10000
# SkillTempInfos de atributo da moda identificada (SkillPropertyTempInfos AddType true): Strength (Power),
# Intellect, Endurance (Physique) e Armor (Agility). Cada família tem 5 faixas de 5 estrelas (Grades 1 a 5)
APPRAISAL_BASES = (5200, 5250, 5300, 5350)
# TODO(inventado): valores sem captura nem cliente; ficam em game_settings["fashion"] e podem ser trocados
DEFAULT_FASHION: dict[str, Any] = {
    "identify_stars": [40, 30, 15, 10, 5],  # pesos das estrelas 1 a 5 sorteadas na identificação
    "compose_rates": [60, 40, 20, 5],  # % de acerto da composição pela diferença de nível: 0, 1, 2 e 3+
    "compose_charm_rate": 100,  # % com a Good Luck Charm (o cliente só diz "Excellent")
}
# sorteio do servidor (testes trocam por valor fixo)
RNG = random.Random()


def is_fashion(templates: GameTemplates, template_id: int) -> bool:
    row = templates.get("ItemTempInfos", template_id)
    return row is not None and row.get("MasterType") == "1" and row.get("SonType") in FASHION_SONS


def register(snap: PlayerSnapshot, templates: GameTemplates, template_id: int) -> FashionBook | None:
    """Ativa a moda no livro (``FashionSwitchItem``: ``isSwitch`` false mostra o ícone de "novo" até o 8631).
    Devolve a entrada nova, ou None se já estava ou não é moda."""
    if not is_fashion(templates, template_id) or any(f.template_id == template_id for f in snap.fashions):
        return None
    book = FashionBook(snap.character.id or 0, template_id, is_switch=False)
    snap.fashions.append(book)
    return book


def activate(snap: PlayerSnapshot, templates: GameTemplates) -> list[FashionBook]:
    """Ativa as modas vinculadas que o jogador tem: "New bound clothing will automatically be activated when it is
    obtained" (``fashion.view.switch.helpFrameContent``). A livre (comprada em Balens) ativa ao vincular."""
    # ponytail: ativa quando o livro é pedido (8625, que o provador e a bancada pedem ao abrir) e não no ganho; mover
    # para o bag.add se algum lugar mostrar o livro sem pedir
    return [b for i in list(snap.items) if i.is_binds and (b := register(snap, templates, i.template_id))]


def appearance(s: GameSession, snap: PlayerSnapshot) -> pb.HeroEquUpdatedMsg:
    t, leader = s.ctx.templates, snap.leader
    return pb.HeroEquUpdatedMsg(
        playerId=snap.character.id or 0,
        armStr=rules.arm_avatar(snap, t),
        clothStr=rules.cloth_avatar(snap, t),
        wing=rules.avatar(snap, t, rules.WING),
        hat=rules.avatar(snap, t, rules.HAT),
        fashionArm=rules.avatar(snap, t, rules.FASHION_ARM),
        fashionCloth=rules.avatar(snap, t, rules.FASHION_CLOTH),
        hide=leader is not None and leader.hide_fashion,
        appellId=snap.character.appell_id,
    )


@router.on(5008)
async def hide_fashion(s: GameSession, msg: pb.HeroHideFashionReqMsg) -> None:
    """Esconde/mostra a moda e avisa todos (149, como a troca de aparência). (visto) oficial_20261023-171155-1 #2958,
    #5596, #8610: o cliente manda ``hide`` 0 com a moda já à mostra (depois de mexer no equipamento) e o oficial não
    responde; sem mudança, nada sai."""
    snap = s.snapshot
    assert snap is not None and snap.leader is not None
    if msg.hide not in (HIDE, SHOW) or snap.leader.hide_fashion == (msg.hide == HIDE):
        return
    snap.leader.hide_fashion = msg.hide == HIDE
    await s.ctx.characters.save(snap.leader)
    s.ctx.online.broadcast(S_APPEARANCE, appearance(s, snap))


@router.on(8625)
async def fashion_info(s: GameSession, _: object) -> None:
    snap = s.snapshot
    assert snap is not None
    books = activate(snap, s.ctx.templates)
    if books:
        await s.ctx.characters.save(*books)
    send(s, S_FASHION_BOOK, fashion_book(snap, s.ctx.templates))


@router.on(8595)
async def fashion_switch(s: GameSession, msg: pb.FashionMsg) -> None:
    """Provador (``FashionSwitchView.__saveHandler``, um 8595 por parte): a moda vestida no líder com o SonType do
    ``templateId`` passa a ser esse modelo. Só modelo ativado (no livro, ``saveBtn.tipData02``), com moda vestida
    nesse espaço (``tipData01``) e diferente da vestida (``tipData03``); sem custo (``helpFrameContent`` item 5).
    *(dedução)*: a peça troca de modelo (o ``ItemInfoMsg`` não tem campo de aparência); resposta = a do 5005."""
    snap = s.snapshot
    assert snap is not None and snap.leader is not None
    templates = s.ctx.templates

    def son(template_id: int) -> str | None:
        return (templates.get("ItemTempInfos", template_id) or {}).get("SonType")

    worn = next(
        (
            i
            for i in snap.items
            if i.bag_type == BagType.HERO
            and i.object_id == snap.leader.id
            and is_fashion(templates, i.template_id)
            and son(i.template_id) == son(msg.templateId)
        ),
        None,
    )
    known = any(f.template_id == msg.templateId for f in snap.fashions)
    # bloqueio real: na sala, o dono do casamento (MarryUIMediator) chama ``FashionManager.saveBook`` (8595) com
    # SlotId/ClothId/WingId/HatId da MarryQualityTemplateCate, que é lida do MarrySpecTempInfo; as linhas inglesas não
    # têm esses campos (> 0 falha) e o cliente nunca manda: só a moda do livro passa
    if not is_fashion(templates, msg.templateId) or not known or worn is None or worn.template_id == msg.templateId:
        s.log.info("8595 recusado", modelo=msg.templateId, vestida=worn.template_id if worn else None)
        return
    worn.template_id = msg.templateId
    await s.ctx.characters.save(worn)

    _player(s)
    _army(s)
    s.send(S_ITEMS, bag.moved([worn], s.player_id))
    space.refresh_look(s)


@router.on(8631)
async def fashion_special(s: GameSession, msg: pb.FashionMsg) -> None:
    """Apaga o ícone de "novo" da moda no livro (``FashionManager.disenableNewIcon``): grava ``isSwitch`` e reenvia o
    livro (o cliente só atualiza o ``bookList`` pelo 4542)."""
    snap = s.snapshot
    assert snap is not None
    book = next((f for f in snap.fashions if f.template_id == msg.templateId and not f.is_switch), None)
    if book is None:
        return
    book.is_switch = True
    await s.ctx.characters.save(book)
    send(s, S_FASHION_BOOK, fashion_book(snap, s.ctx.templates))


def _cfg(s: GameSession) -> dict[str, Any]:
    return DEFAULT_FASHION | dict(s.ctx.world.settings.get("fashion") or {})


def _grade(templates: GameTemplates, skill: int) -> int | None:
    row = templates.get("SkillTempInfos", skill)
    return int(row["Grades"]) if row else None


def _son(templates: GameTemplates, template_id: int) -> str | None:
    return (templates.get("ItemTempInfos", template_id) or {}).get("SonType")


def _level(templates: GameTemplates, item: Item) -> int:
    """(cliente) FashionComposeView.getFashionLevelByInfo: Grades do randomSkill1, ou do primeiro DefaultSkill."""
    if item.template_id == WILDCARD:
        return 1
    grade = _grade(templates, item.random_skill)
    if grade is None:
        row = templates.get("ItemTempInfos", item.template_id) or {}
        grade = _grade(templates, int((row.get("DefaultSkill") or "0").split(",")[0]))
    return grade or 0


def _appraisal_skill(templates: GameTemplates, cfg: dict[str, Any]) -> int:
    """Uma skill de atributo: estrelas pelos pesos, família de atributo e faixa ao acaso."""
    stars = RNG.choices(range(1, 6), weights=cfg["identify_stars"])[0]
    base = RNG.choice(APPRAISAL_BASES)
    return RNG.choice([t for t in range(base, base + 25) if _grade(templates, t) == stars])


@router.on(8781)
async def fashion_appraisal(s: GameSession, msg: pb.FashionMsg) -> None:
    """Identificação (``FashionSwitchItem.indentityCallBack``): gasta o ouro da moda (``ItemTempInfos.Property1``,
    "Spend {0} Gold"), que só some quando a moda está no livro e ainda não tem skill. A chance é a da tabela do
    cliente pelo ``TransformId``. (visto) 1026-225632-1 #2524: 109 (600000 gold da moda 1100303), 111 "Identification
    Failed." e 4542. Sucesso: 109 e 4542 (sem texto no cliente: TODO(inventado) nenhum aviso)."""
    snap = s.snapshot
    assert snap is not None and snap.leader is not None
    templates, c = s.ctx.templates, snap.character
    row = templates.get("ItemTempInfos", msg.templateId) or {}
    book = next((f for f in snap.fashions if f.template_id == msg.templateId), None)
    tr = int(row.get("TransformId") or -1)
    cost = int(row.get("Property1") or 0)
    if not is_fashion(templates, msg.templateId) or book is None or c.grades < IDENTIFY_GRADE:
        s.log.info("8781 recusado", modelo=msg.templateId)
        send(s, S_FASHION_BOOK, fashion_book(snap, templates))
        return
    if book.appraisal_skill:
        await _refresh(s, snap, book, int(row.get("Property2") or 0))
        return
    if not 0 <= tr < len(IDENTIFY_RATES) or c.gold < cost:
        s.log.info("8781 recusado: ouro ou taxa", modelo=msg.templateId, ouro=c.gold, custo=cost)
        send(s, S_FASHION_BOOK, fashion_book(snap, templates))
        return
    c.gold -= cost
    won = RNG.randrange(100) < IDENTIFY_RATES[tr]
    if won:
        book.appraisal_skill = _appraisal_skill(templates, _cfg(s))
        await s.ctx.characters.save(c, book)
    else:
        await s.ctx.characters.save(c)
    castle_yield(s)
    if not won:
        send(s, S_ALERT, pb.ChatChannelMsg(channel=7, encodeMsg="Identification Failed."))
    send(s, S_FASHION_BOOK, fashion_book(snap, templates))


async def _refresh(s: GameSession, snap: PlayerSnapshot, book: FashionBook, cores: int) -> None:
    """Refino da moda já identificada (cliente ``FashionSwitchItem``: "refreshContent", ``getCountForRefresh`` =
    ``Property2`` Fashion Cores; com 5 estrelas, ``hasRefreshFull``, o cliente nem pede). Sorteia de novo a skill.
    TODO(inventado): sempre acerta, a nova troca a antiga mesmo se for pior, e a resposta é só 115 e 4542."""
    templates = s.ctx.templates
    if _grade(templates, book.appraisal_skill) == 5 or cores <= 0 or bag.count_of(snap, WILDCARD) < cores:
        s.log.info("8781 refino recusado", modelo=book.template_id, nucleos=cores)
        send(s, S_FASHION_BOOK, fashion_book(snap, templates))
        return
    changed, gone = bag.take(snap, WILDCARD, cores)
    book.appraisal_skill = _appraisal_skill(templates, _cfg(s))
    await s.ctx.characters.save(*changed, book, delete=tuple(gone))
    send(s, S_ITEMS, bag.moved(changed, s.player_id, empty=gone))
    send(s, S_FASHION_BOOK, fashion_book(snap, templates))


def _compose_plan(
    s: GameSession, snap: PlayerSnapshot, a: Item, b: Item, use_charm: bool
) -> tuple[int, int, int] | None:
    """(ouro, Good Luck Charms, % de acerto) para compor ``a`` e ``b`` na bancada, ou None (recusa). Regras do
    cliente (``FashionComposeView.doCompose``): moda registrada ou curinga, nível > 0, mesmo SonType (curinga
    serve para qualquer), dois curingas não, e 5 curingas para SonType 109 (asas)."""
    templates, c = s.ctx.templates, snap.character
    if a.template_id == b.template_id == WILDCARD:
        return None
    for item in (a, b):
        if item.template_id != WILDCARD and not (
            is_fashion(templates, item.template_id) and any(f.template_id == item.template_id for f in snap.fashions)
        ):
            return None
    fashions = [i for i in (a, b) if i.template_id != WILDCARD]
    son = _son(templates, fashions[0].template_id)
    if any(_son(templates, i.template_id) != son for i in fashions):
        return None
    wild = [i for i in (a, b) if i.template_id == WILDCARD]
    if wild and son == rules.WING and wild[0].count < 5:
        return None
    levels = (_level(templates, a), _level(templates, b))
    gold = (levels[0] + levels[1]) * COMPOSE_GOLD
    if 0 in levels or c.gold < gold:
        return None
    # (cliente) calculateNeedLuckyCharmCount: só a peça da 1ª célula conta, e asas custam 5 vezes
    charms = 2 ** (levels[0] - 2) * (5 if _son(templates, a.template_id) == rules.WING else 1) if levels[0] > 1 else 0
    if use_charm and bag.count_of(snap, CHARM) < charms:
        return None
    diff = abs(levels[0] - levels[1])
    cfg = _cfg(s)
    if use_charm:
        rate = cfg["compose_charm_rate"]
    elif diff == 0 and levels[0] == 1:
        rate = 100  # (cliente) setRateText: nível 1 com diferença 0 é 100%
    else:
        rate = cfg["compose_rates"][min(diff, 3)]
    return gold, charms if use_charm else 0, rate


@router.on(8594)
async def fashion_compose(s: GameSession, msg: pb.StoreReqMsg) -> None:
    """Composição na bancada (``FashionComposeView.doCompose``; 8594 sem peças: as posições 0 e 1 da bancada,
    ``BagType.STORE``, como a forja). Custo: ouro pelos níveis e, com ``operate`` (Good Luck Charm), as charms.
    Sucesso: uma moda aleatória do mesmo SonType, preferindo as que o herói veste (``bag.fits_hero``).
    TODO(inventado): o que acontece na falha (aqui: as peças e o ouro somem, composeResult false) e o consumo de 5
    curingas (o cliente só exige 5 na célula)."""
    snap = s.snapshot
    assert snap is not None and snap.leader is not None
    c, templates, now = snap.character, s.ctx.templates, s.ctx.clock.now()
    a, b = bag.at(snap, BagType.STORE, 0, 0), bag.at(snap, BagType.STORE, 0, 1)
    plan = _compose_plan(s, snap, a, b, msg.operate) if a is not None and b is not None else None
    if plan is None or a is None or b is None:
        # o cliente só não mexe se composeResult for false; a mensagem dele para cada recusa não é conhecida
        s.log.info("8594 recusado", pedido=str(msg))
        send(s, S_FASHION_COMPOSE, pb.StoreRspMsg(composeResult=False, composeTemplateId=-1))
        return
    gold, charms, rate = plan
    c.gold -= gold
    changed: list[Item] = []
    gone: list[Item] = []
    fashion_son = _son(templates, next(i.template_id for i in (a, b) if i.template_id != WILDCARD))
    for item in (a, b):
        count = (5 if fashion_son == rules.WING else 1) if item.template_id == WILDCARD else 1
        (gone if bag.take_one(snap, item, count) else changed).append(item)
    charm_changed, charm_gone = bag.take(snap, CHARM, charms) if charms else ([], [])
    won = RNG.randrange(100) < rate
    got: list[Item] = []
    product = -1
    if won:
        pool = [
            r for r in templates.rows("ItemTempInfos") if r.get("MasterType") == "1" and r.get("SonType") == fashion_son
        ]
        fit = [r for r in pool if bag.fits_hero(snap, r, rules.job_type(c.job), c.sex)]
        product = int(RNG.choice(fit or pool)["TemplateId"])
        got = bag.add(snap, templates, product, 1, now)
    book = register(snap, templates, product) if won and got and got[0].is_binds else None
    await s.ctx.characters.save(
        c, *changed, *got, *charm_changed, *([book] if book else []), delete=tuple(gone + charm_gone)
    )
    send(s, S_ITEMS, bag.moved(changed, s.player_id, empty=gone + charm_gone))
    castle_yield(s)
    if won:
        send(s, S_ITEMS, bag.moved(got, s.player_id))
    send(
        s,
        S_FASHION_COMPOSE,
        pb.StoreRspMsg(
            composeResult=won,
            pos=got[0].pos if won else 0,
            objectId=got[0].object_id if won else 0,
            bagType=BagType.BAG if won else BagType.STORE,
            composeTemplateId=product,
        ),
    )
