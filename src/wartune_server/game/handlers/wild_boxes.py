"""Baú dos monstros dos Wilds: cai no tile do monstro para quem o matou (4940) e abre com um clique (9526).

Cliente (m3 ``OuterCityManager.onMapBossBox``, ``OuterCityMap.onUpdateBox``, ``OuterCityBossBoxView``): o 4940
troca a lista inteira e desenha um ``BossBoxMc<type>`` por ``boxId`` novo, sem filtrar por mapa e sem tirar os
que saíram da lista; o clique manda o 9526 com o baú e o apaga da tela. Então o 4940 leva só os baús do mapa
pedido. O conteúdo é sorteado ao abrir (``monsters.loot``, tabela ``world_monster_drops``). O baú fica no banco
até ser aberto. (dedução) ``type`` = ``bossType``, e o baú não expira (nenhuma fonte diz quando some).
"""

from __future__ import annotations

import random

from ...domain.models import Mail, MailType, WildBox
from ...domain.repositories import UnitOfWork
from ...protocol.messages import wartune_pb2 as pb
from .. import mail as mailbox
from .. import monsters, rewards
from ..router import router
from ..session import GameSession
from .player import S_CHAT, alert, granted

S_MAP_BOX = 4940
MAIL_TITLE, MAIL_TEXT = "Wilds Chest", "Your bag was full, so the chest's contents were sent by mail."
SLAYER = "Wilds Slayer Rewards"  # (visto) #6987, colado no texto, sem ":"
BAG_FULL_MAIL = "Inventory full, check your mail!"  # (cliente) language.txt inglês, VipBoxFrame.command03
_rng = random.Random()


def send_boxes(s: GameSession, map_id: int) -> None:
    snap = s.snapshot
    assert snap is not None
    msg = pb.MapBoxMsg()
    for box in snap.wild_boxes:
        if box.map_id == map_id:
            msg.boxlist.add(boxId=str(box.id), userId=s.player_id, grade=box.grade, mapId=box.map_id,
                            x=box.pos_x, y=box.pos_y, type=box.boss_type)  # fmt: skip
    s.send(S_MAP_BOX, msg)


async def drop_box(s: GameSession, m: monsters.Monster) -> None:
    """Baú do monstro abatido que deu prêmio (``monsters.count_kill``), gravado e mostrado."""
    snap = s.snapshot
    assert snap is not None
    box = WildBox(snap.character.id or 0, m.map_id, m.x, m.y, m.boss_type, monsters.level(s.ctx.templates, m),
                  s.ctx.clock.now())  # fmt: skip
    snap.wild_boxes.append(box)
    await s.ctx.characters.save(box)


async def _by_mail(s: GameSession, box: WildBox, drops: list[tuple[int, int]]) -> None:
    """Mochila cheia: o conteúdo vai como anexo no correio do jogo (5 por carta), na mesma transação que apaga o
    baú. Aviso: o do baú VIP (``VipBoxFrame.command03``); título e texto da carta são dedução."""
    now = s.ctx.clock.now()
    mails = [Mail(box.character_id, now, MAIL_TITLE, MAIL_TEXT, mail_type=MailType.SYSTEM,
                  send_type=mailbox.SYSTEM_SENDER) for _ in range(0, len(drops), mailbox.MAX_ANNEXES)]  # fmt: skip

    async def change(uow: UnitOfWork) -> None:
        await uow.delete(box)
        for i, mail in enumerate(mails):
            await mailbox.stage(uow, mail, drops[i * mailbox.MAX_ANNEXES : (i + 1) * mailbox.MAX_ANNEXES])

    await s.ctx.characters.write(change)
    s.log.info("9526 baú pelo correio", box=box.id, drops=drops)
    for mail in mails:
        mailbox.notify(s.ctx.online, mail)
    send_boxes(s, box.map_id)
    alert(s, BAG_FULL_MAIL)


@router.on(9526)
async def pick(s: GameSession, msg: pb.ArmyBoxMsg) -> None:
    """Abre o baú: sorteia, dá e tira da lista. Mochila cheia: vai pelo correio."""
    snap = s.snapshot
    assert snap is not None
    box = next((b for b in snap.wild_boxes if str(b.id) == msg.boxId), None)
    if box is None:
        s.log.info("9526 baú inexistente", box=msg.boxId)
        return
    drops = monsters.loot(s.ctx.world, box.boss_type, box.grade, _rng)
    snap.wild_boxes.remove(box)
    if not rewards.can_grant(snap, s.ctx.templates, drops, s.ctx.clock.now()):
        await _by_mail(s, box, drops)
        return
    new, _ = rewards.grant(snap, s.ctx.templates, drops)
    await s.ctx.characters.save(*rewards.owners(snap), *new, delete=(box,))
    s.log.info("9526 baú aberto", box=msg.boxId, drops=drops)
    if drops:
        # (visto) oficial_20261023-171155-1 #6974-#6988: 3, 109, 115, 4476, 111 e 83 com "Wilds Slayer RewardsMystery
        # Stone x1, 10,000 Daru, 10,000 Gold" (itens primeiro, as moedas do fim da tabela para o começo); sem 4940
        shown = [d for d in drops if d[0] > 0] + [d for d in reversed(drops) if d[0] < 0]
        text = SLAYER + rewards.text(s.ctx.templates, shown).removeprefix("Received: ")
        granted(s, drops, new, "", chat=False)
        alert(s, text)
        s.send(S_CHAT, pb.ChatChannelMsg(channel=3, encodeMsg=text))
