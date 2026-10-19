"""Itens com validade (loja de honra, 8346, relógio), VIP (amigos, corneta, 5172 index 0) e a mochila real
(comprados/alugada) nas concessões. Ver docs/itens.md, docs/social.md, docs/chat.md."""

from datetime import UTC, datetime, timedelta
from pathlib import Path

from tests.game.harness import Game, logged_in
from tests.game.test_shop import buy, codes
from wartune_server.domain.models import BagType, Item, PlayerSnapshot
from wartune_server.game import bag, items, rewards
from wartune_server.game import events as ev
from wartune_server.game.handlers import chat, vip
from wartune_server.game.session import GameSession
from wartune_server.protocol.messages import wartune_pb2 as pb
from wartune_server.services.clock import FakeClock

MEDAL_GOOD, MEDAL, HONOR = 153, 3010101, 208001  # ShopTempInfo 153: Private Medallion, 1000 Honor, ValidDate 43200
START = datetime(2026, 5, 21, 12, 0, 0, tzinfo=UTC)


def _session(g: Game) -> GameSession:
    session = g.server.online.get(g.user_id)
    assert session is not None and session.snapshot is not None
    return session


def _snap(g: Game) -> PlayerSnapshot:
    snap = _session(g).snapshot
    assert snap is not None
    return snap


def _vip(snap: PlayerSnapshot, until: str = "2999-01-01 00:00:00") -> None:
    st = ev.state(snap, "vip", START)
    st.value, st.text = 0, until  # nível 1


async def test_medalha_da_loja_de_honra_vence_e_some(tmp_path: Path) -> None:
    clock = FakeClock(START)
    async with logged_in(tmp_path, novice=19000, clock=clock) as g:
        snap = _snap(g)
        snap.character.grades, snap.character.geste = 16, 2000  # NeedGrades e NeedGeste da medalha
        honor = Item(g.user_id, HONOR, pos=30, count=1000)
        snap.items.append(honor)
        await g.server.services.characters.save(snap.character, honor)

        g.client.send(5154, buy(MEDAL_GOOD, 1))
        got = await g.until(90)
        assert codes(got) == [115, 115, 111, 83, 90]
        info = pb.ItemMovedListMsg.FromString(got[1].body).moved[0].item
        # (cliente) validDate em minutos e beginDate no formato do sysCurtime
        assert (info.templateId, info.validDate, info.beginDate) == (MEDAL, 43200, "2026-05-21 12:00:00")
        saved = await g.server.services.characters.snapshot(g.user_id)
        medal = next(i for i in saved.items if i.template_id == MEDAL)
        assert (medal.valid_date, medal.begin_date) == (43200, START)

        g.client.send(8346, pb.ItemRemoveMsg(bagType=1, pos=medal.pos))  # ainda vale: ignora
        assert await g.idle() == []

        clock.advance(43200 * 60)
        g.client.send(8346, pb.ItemRemoveMsg(bagType=1, pos=medal.pos))
        got = await g.until(115)
        moved = pb.ItemMovedListMsg.FromString(got[-1].body).moved[0]
        assert (moved.changePos, moved.HasField("item")) == (medal.pos, False)
        saved = await g.server.services.characters.snapshot(g.user_id)
        assert not any(i.template_id == MEDAL for i in saved.items)


async def test_medalha_vestida_vencida_some_no_relogio(tmp_path: Path) -> None:
    clock = FakeClock(START)
    async with logged_in(tmp_path, novice=19000, clock=clock) as g:
        snap = _snap(g)
        assert snap.leader is not None
        worn = Item(g.user_id, MEDAL, bag_type=BagType.HONOR, object_id=snap.leader.id or 0, valid_date=10)
        worn.begin_date = START
        snap.items.append(worn)
        await g.server.services.characters.save(worn)
        g.client.send(20008, pb.SynchronizedTimeMsg())
        assert 115 not in codes(await g.idle())

        clock.advance(600)  # 10 minutos: o cliente não confere a bolsa 3, o servidor sim
        g.client.send(20008, pb.SynchronizedTimeMsg())
        got = await g.idle()
        assert 115 in codes(got) and worn not in snap.items
        saved = await g.server.services.characters.snapshot(g.user_id)
        assert not any(i.template_id == MEDAL for i in saved.items)


async def test_vip_amigos_corneta_e_aceleracao_gratis(tmp_path: Path) -> None:
    async with logged_in(tmp_path, novice=20000) as g:
        s, snap = _session(g), _snap(g)
        assert vip.friend_bonus(s, snap) == 0 and not vip.free_cool(s, snap)
        free = chat.free_bugles(s)
        assert s.ctx.world.settings["vip_bugle_bonus"] == [0] * 10  # migração 0037: sem fonte, sem efeito
        bonus = {**s.ctx.world.settings, "vip_bugle_bonus": [0, 5] + [0] * 8}
        object.__setattr__(s.ctx.world, "settings", bonus)  # World é congelado; este servidor é só do teste
        assert chat.free_bugles(s) == free  # sem VIP: só a cota do ConfigInfo

        _vip(snap)
        # (cliente) vipFriendPrivilege: para2 6 no nível 1 tem para1 != 0 -> 50 fixos
        assert vip.friend_bonus(s, snap) == 50 and vip.free_cool(s, snap)
        assert chat.free_bugles(s) == free + 5

        council = next(b.id for b in snap.buildings if b.template_id == 90101 and b.id)
        snap.character.grades, snap.character.gold, snap.character.point = 2, 1000, 0
        await g.server.services.characters.save(snap.character)
        g.client.send(8203, pb.BuildingOptionReqMsg(buildingId=council))
        await g.until(83)
        g.client.send(5172, pb.BuildingReqMsg(orderId=1, index=0))  # VIP: grátis, sem diamante
        got = await g.until(102)
        assert codes(got) == [3, 111, 102]
        assert pb.OrderQuickRspMsg.FromString(got[2].body).orderInfo[0].remainTime == 0
        assert snap.character.point == 0

        _vip(snap, "2000-01-01 00:00:00")  # vencido
        assert vip.friend_bonus(s, snap) == 0 and not vip.free_cool(s, snap)


async def test_concessoes_usam_a_mochila_real(tmp_path: Path) -> None:
    async with logged_in(tmp_path, novice=19000) as g:
        snap, templates, now = _snap(g), g.server.services.templates, START
        cid = snap.character.id or 0
        snap.items.extend(Item(cid, 2040101, pos=p) for p in range(bag.BAG_BASE) if not bag.at(snap, BagType.BAG, 0, p))
        one = [(2040101, 1)]
        assert not rewards.can_grant(snap, templates, one, now) and not items.fits(snap, one, now)
        snap.character.bag_count = 7  # uma linha comprada (5010)
        assert rewards.can_grant(snap, templates, one, now) and items.fits(snap, one, now)
        snap.character.bag_count = 0
        snap.character.rental_bag_until = now + timedelta(days=1)  # alugada: 217
        assert rewards.can_grant(snap, templates, one * 175, now)
