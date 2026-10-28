"""Moda: esconder (5008), livro de moda (8625/8631/8781), provador (8595) e composição na bancada (8594). A compra
de moda (8592) fica na loja. Ver ``docs/itens.md``.
"""

from __future__ import annotations

from ...domain.models import BagType, FashionBook, PlayerSnapshot
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
    # ponytail: o MarryUIMediator também manda 8595 com as roupas do casamento (MarryQualityTempInfo), que não estão no
    # livro: recusado até existir o casamento
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


@router.on(8781)
async def fashion_appraisal(s: GameSession, msg: pb.FashionMsg) -> None:
    # a avaliação sorteia o appraisalSkill da moda (5211, 5260; só turco: login.json #44) por uma tabela que não
    # está nos templates: recusa e reenvia o livro como está
    snap = s.snapshot
    assert snap is not None
    s.log.info("8781 recusado: tabela da avaliação desconhecida", modelo=msg.templateId)
    # (visto) 1026-225632-1 #2524: 109 e depois 111 "Identification Failed." logo após o pedido. TODO(inventado):
    # a sequência é de uma amostra só; o 109 sem gasto conhecido e a posição do 4542 não estão confirmados
    castle_yield(s)
    send(s, S_ALERT, pb.ChatChannelMsg(channel=7, encodeMsg="Identification Failed."))
    send(s, S_FASHION_BOOK, fashion_book(snap, s.ctx.templates))


@router.on(8594)
async def fashion_compose(s: GameSession, msg: pb.StoreReqMsg) -> None:
    # compor moda na bancada (duas do mesmo SonType ou com o curinga 208020) dá uma moda por uma regra
    # que não está no cliente decompilado: composeResult false (o FashionBag ignora e não mexe em nada)
    s.log.info("8594 recusado: regra da composição de moda desconhecida", pedido=str(msg))
    send(s, S_FASHION_COMPOSE, pb.StoreRspMsg(composeResult=False, composeTemplateId=-1))
