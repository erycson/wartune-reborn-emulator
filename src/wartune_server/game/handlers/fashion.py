"""Moda: esconder (5008), livro de moda (8625/8595/8631/8781) e composição/troca na bancada
(8594/8595). A compra de moda (8592) fica na loja. Ver ``docs/itens.md``.
"""

from __future__ import annotations

from ...domain.models import FashionBook, PlayerSnapshot
from ...protocol.messages import wartune_pb2 as pb
from ...templates.repository import GameTemplates
from .. import rules
from ..builders.player import fashion_book
from ..router import router
from ..session import GameSession
from .shop import send

S_APPEARANCE, S_FASHION_COMPOSE, S_FASHION_BOOK = 149, 4487, 4542
HIDE, SHOW = 1, 2  # HeroHideFashionReqMsg.hide; 0 = só pedir a aparência (sendChangeHeroInfo)
FASHION_SONS = (rules.WING, rules.HAT, rules.FASHION_CLOTH, rules.FASHION_ARM)


def is_fashion(templates: GameTemplates, template_id: int) -> bool:
    row = templates.get("ItemTempInfos", template_id)
    return row is not None and row.get("MasterType") == "1" and row.get("SonType") in FASHION_SONS


def register(snap: PlayerSnapshot, templates: GameTemplates, template_id: int) -> FashionBook | None:
    """Põe a moda no livro na primeira vez que é vestida (o livro do oficial lista as que o jogador já
    teve, com ``isSwitch`` ligado). Devolve a entrada nova, ou None se já estava ou não é moda."""
    if not is_fashion(templates, template_id) or any(f.template_id == template_id for f in snap.fashions):
        return None
    book = FashionBook(snap.character.id or 0, template_id)
    snap.fashions.append(book)
    return book


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
    """Esconde/mostra a moda e avisa todos (149, como a troca de aparência)."""
    snap = s.snapshot
    assert snap is not None and snap.leader is not None
    if msg.hide in (HIDE, SHOW) and snap.leader.hide_fashion != (msg.hide == HIDE):
        snap.leader.hide_fashion = msg.hide == HIDE
        await s.ctx.characters.save(snap.leader)
    s.ctx.online.broadcast(S_APPEARANCE, appearance(s, snap))


@router.on(8625)
async def fashion_info(s: GameSession, _: object) -> None:
    snap = s.snapshot
    assert snap is not None
    send(s, S_FASHION_BOOK, fashion_book(snap, s.ctx.templates))


@router.on(8595)
async def fashion_switch(s: GameSession, msg: pb.FashionMsg) -> None:
    # dois pedidos no mesmo opcode: FashionMsg.templateId = saveBook, que o cliente só usa para as
    # roupas do casamento (MarryUIMediator) e depende do casamento; StoreReqMsg vazio (chega com
    # templateId 0) = troca de aparência na bancada, cuja regra não está no cliente decompilado
    s.log.info("8595 recusado: depende do casamento / regra da troca desconhecida", modelo=msg.templateId)


@router.on(8631)
async def fashion_special(s: GameSession, msg: pb.FashionMsg) -> None:
    # só apaga o ícone de "novo" da moda no livro (FashionManager.disenableNewIcon): estado só do
    # cliente, nada a gravar nem responder
    s.log.debug("8631 ícone de moda nova visto", modelo=msg.templateId)


@router.on(8781)
async def fashion_appraisal(s: GameSession, msg: pb.FashionMsg) -> None:
    # a avaliação sorteia o appraisalSkill da moda (5211, 5260 nas capturas) por uma tabela que não
    # está nos templates: recusa e reenvia o livro como está
    snap = s.snapshot
    assert snap is not None
    s.log.info("8781 recusado: tabela da avaliação desconhecida", modelo=msg.templateId)
    send(s, S_FASHION_BOOK, fashion_book(snap, s.ctx.templates))


@router.on(8594)
async def fashion_compose(s: GameSession, msg: pb.StoreReqMsg) -> None:
    # compor moda na bancada (duas do mesmo SonType ou com o curinga 208020) dá uma moda por uma regra
    # que não está no cliente decompilado: composeResult false (o FashionBag ignora e não mexe em nada)
    s.log.info("8594 recusado: regra da composição de moda desconhecida", pedido=str(msg))
    send(s, S_FASHION_COMPOSE, pb.StoreRspMsg(composeResult=False, composeTemplateId=-1))
