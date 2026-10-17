from pathlib import Path

from tests.game.harness import Game, logged_in
from wartune_server.domain.models import Character, Consortia, Item
from wartune_server.game import bag
from wartune_server.game import guild as gd
from wartune_server.game.handlers import guild as handlers
from wartune_server.game.session import GameSession
from wartune_server.protocol import Packet
from wartune_server.protocol.messages import wartune_pb2 as pb


def _session(g: Game) -> GameSession:
    s = g.server.online.get(g.user_id)
    assert s is not None and s.snapshot is not None
    return s


def _char(g: Game) -> Character:
    snap = _session(g).snapshot
    assert snap is not None
    return snap.character


def _rich(g: Game) -> Character:
    c = _char(g)
    c.grades, c.gold, c.point = 20, 1_000_000, 100
    return c


def _one[M](got: list[Packet], code: int, cls: type[M]) -> M:
    [p] = [p for p in got if p.code == code]
    return cls.FromString(p.body)  # type: ignore[attr-defined, no-any-return]


def _guild(g: Game) -> Consortia:
    mine = _session(g).ctx.guilds.of(g.user_id)
    assert mine is not None
    return mine[0]


async def _create(g: Game, name: str = "Lobos") -> list[Packet]:
    _rich(g)
    await g.idle()
    g.client.send(5130, pb.ConsortiaMsg(consortiaName=name))
    return await g.idle()


async def _member(a: Game, username: str) -> Game:
    """``username`` se candidata e ``a`` aceita."""
    other = await a.join(username)
    _rich(other)
    other.client.send(5135, pb.ConsortiaMsg(consortiaId=_guild(a).id))
    apply_id = _one(await other.idle(), 35, pb.ConsortiaMsg).applyId
    a.client.send(5134, pb.ConsortiaMsg(applyId=apply_id, result=True))
    assert _one(await other.idle(), 117, pb.ConsortiaMsg).consortiaId == _guild(a).id
    await a.idle()
    return other


async def test_create_needs_level_and_gold_and_tells_the_client(tmp_path: Path) -> None:
    async with logged_in(tmp_path, novice=19000) as a:
        a.client.send(5130, pb.ConsortiaMsg(consortiaName="Lobos"))  # nível 1
        assert not [p for p in await a.idle() if p.code == 117]

        got = await _create(a)
        guild = _guild(a)
        assert _one(got, 117, pb.ConsortiaMsg).consortiaId == guild.id
        player = _one(got, 3, pb.PlayerMsg)
        assert (player.consortiaId, player.consortiaName) == (guild.id, "Lobos")
        info = _one(got, 164, pb.ConsortiaInfoMsg)
        assert (info.chairmanName, info.currentCount, info.levels) == ("Maga", 1, 1)
        assert _char(a).gold == 1_000_000 - handlers.CREATE_GOLD

        b = await a.join("bruxa")
        _rich(b)
        b.client.send(5130, pb.ConsortiaMsg(consortiaName="lobos"))  # nome em uso (sem caixa)
        assert not [p for p in await b.idle() if p.code == 117]

        b.client.send(8213, pb.SearchConditionMsg(consortiaName="lob", pageIndex=1))
        found = _one(await b.idle(), 4139, pb.ConsortiaSearchRspMsg)
        assert found.totalRows == 1 and found.consortiaInfo[0].consortiaName == "Lobos"

        state = await _session(a).ctx.characters.guild_state(_char(a).server_id)
        assert [x.name for x in state[0]] == ["Lobos"] and len(state[1]) == 1


async def test_apply_accept_and_guild_chat_reaches_only_members(tmp_path: Path) -> None:
    async with logged_in(tmp_path, novice=19000) as a:
        await _create(a)
        b = await _member(a, "bruxa")
        c = await a.join("clara")
        _rich(c)
        await c.idle()

        b.client.send(15005, pb.ChatChannelMsg(channel=5, encodeMsg="oi guilda"))
        msg = _one(await a.idle(), 83, pb.ChatChannelMsg)
        assert (msg.channel, msg.encodeMsg, msg.consortiaName) == (5, "oi guilda", "Lobos")
        assert not [p for p in await c.idle() if p.code == 83]

        a.client.send(8207)
        members = _one(await a.idle(), 4133, pb.SimplePlayerListRspMsg)
        assert members.totalRows == 2 and {p.nickName for p in members.playerInfo} == {"Maga", "Bruxa"}


async def test_invite_answer_quit_cooldown_and_kick(tmp_path: Path) -> None:
    async with logged_in(tmp_path, novice=19000) as a:
        await _create(a)
        c = await a.join("clara")
        _rich(c)
        await c.idle()
        a.client.send(5142, pb.ConsortiaMsg(otherId=c.user_id))
        invite_id = _one(await c.idle(), 41, pb.ConsortiaMsg).applyId
        c.client.send(5143, pb.ConsortiaMsg(applyId=invite_id, result=True))
        got = await c.idle()
        assert _one(got, 37, pb.ConsortiaMsg).result and _one(got, 117, pb.ConsortiaMsg).consortiaId

        c.client.send(5132, pb.ConsortiaMsg(otherId=a.user_id))  # membro não expulsa o chefe
        await c.idle()
        assert _session(a).ctx.guilds.of(a.user_id) is not None

        c.client.send(5146, pb.ConsortiaQuitReqMsg())
        assert _one(await c.idle(), 117, pb.ConsortiaMsg).consortiaId == 0
        assert _char(c).is_auto
        c.client.send(5135, pb.ConsortiaMsg(consortiaId=_guild(a).id))  # 24 h de espera
        assert not [p for p in await c.idle() if p.code == 35]

        b = await _member(a, "bruxa")
        a.client.send(5137, pb.ConsortiaMsg(otherId=b.user_id, positionId=3))
        assert _one(await b.idle(), 50, pb.ConsortiaMsg).positionId == 3
        a.client.send(5132, pb.ConsortiaMsg(otherId=b.user_id))
        assert _one(await b.idle(), 117, pb.ConsortiaMsg).consortiaId == 0
        assert _session(a).ctx.guilds.of(b.user_id) is None


async def test_contribution_matches_the_capture(tmp_path: Path) -> None:
    """Captura birlik_katkisi: -1000 ouro dá +1, -55000 dá +55 (hoje 1 -> 56)."""
    async with logged_in(tmp_path, novice=19000) as a:
        await _create(a)
        c = _char(a)
        gold = c.gold
        a.client.send(5144, pb.ConsortiaUserOfferReqMsg(offerGold=1000))
        await a.idle()
        a.client.send(5144, pb.ConsortiaUserOfferReqMsg(offerGold=55999))
        got = await a.idle()
        assert [p.code for p in got if p.code in (109, 3, 111, 42, 164)] == [109, 3, 111, 42, 164]
        assert _one(got, 42, pb.ConsortiaMsg).result
        assert _one(got, 164, pb.ConsortiaInfoMsg).offer == 56
        assert (c.gold, c.consortia_offer, c.consortia_total_offer) == (gold - 56000, 56, 56)

        a.client.send(8208, pb.ConsortiaOfferReqMsg(pageIndex=1))
        ranking = _one(await a.idle(), 4134, pb.ConsortiaContributeRspMsg)
        assert (ranking.selfOrder, ranking.selfInfo.todayOffer, ranking.selfInfo.totalOffer) == (1, 56, 56)

        a.client.send(5144, pb.ConsortiaUserOfferReqMsg(offerGold=10**9))  # mais ouro que tem
        assert not [p for p in await a.idle() if p.code == 42]


async def test_upgrade_cooldown_quick_and_learning(tmp_path: Path) -> None:
    async with logged_in(tmp_path, novice=19000) as a:
        await _create(a)
        guild = _guild(a)
        guild.offer = 10_000
        a.client.send(5133, pb.ConsortiaMsg(upgradeType=1))
        info = _one(await a.idle(), 164, pb.ConsortiaInfoMsg)
        assert (info.levels, info.offer, info.codeType, info.codeNeedDate) == (2, 9_600, 1, 3600)

        a.client.send(5133, pb.ConsortiaMsg(upgradeType=4))  # escola: espera da guilda
        assert not [p for p in await a.idle() if p.code == 164]

        a.client.send(8545, pb.PayTypeMsg(payType=1))  # 3600 s = 6 diamantes
        await a.idle()
        assert _char(a).point == 94 and guild.code_begin_at is None

        c = _char(a)
        c.consortia_offer = 1000
        a.client.send(5147, pb.ConsortiaMsg(studySkill=6))  # guilda sem pesquisa
        assert c.skill_attack == 0 and not [p for p in await a.idle() if p.code == 150]
        guild.attack_level = 1
        a.client.send(5147, pb.ConsortiaMsg(studySkill=6))
        got = await a.idle()
        assert _one(got, 3, pb.PlayerMsg).consortiaAttack == 1 and [p for p in got if p.code == 150]
        assert c.consortia_offer == 800


async def test_guild_shop_pays_with_contribution(tmp_path: Path) -> None:
    """Captura: goodId 19 = 2040106 "Şans Taşı Lv.6", 40 de contribuição, mercado nível 6."""
    async with logged_in(tmp_path, novice=19000) as a:
        await _create(a)
        s, c = _session(a), _char(a)
        c.consortia_offer = 100
        assert not await handlers.shop_buy(s, pb.BuyInfo(goodId=999_999, count=1))

        assert await handlers.shop_buy(s, pb.BuyInfo(goodId=19, count=1))
        assert _one(await a.idle(), 90, pb.ShopMsg).buyInfo.result == handlers.R_GUILD  # mercado nível 0

        _guild(a).shop_level = 6
        assert await handlers.shop_buy(s, pb.BuyInfo(goodId=19, count=1))
        got = await a.idle()
        assert [p.code for p in got if p.code in (3, 115, 111, 90, 83)] == [3, 115, 111, 90, 83]
        assert _one(got, 90, pb.ShopMsg).buyInfo.result == handlers.R_OK
        assert c.consortia_offer == 60
        assert any(i.template_id == 2040106 for i in s.snapshot.items)  # type: ignore[union-attr]


async def test_guild_market_is_bought_through_5154(tmp_path: Path) -> None:
    """O cliente compra no mercado pelo 5154 genérico (``ShopManager.sendShoping``): ShopType 2 vai
    para a guilda, e cada recusa manda o código que o cliente sabe mostrar."""
    async with logged_in(tmp_path, novice=19000) as a:
        await _create(a)
        c = _char(a)
        c.consortia_offer = 100
        a.client.send(5154, pb.ShopMsg(buyInfo=pb.BuyInfo(goodId=19, count=1), payType=0))
        assert _one(await a.idle(), 90, pb.ShopMsg).buyInfo.result == handlers.R_GUILD

        _guild(a).shop_level = 6
        a.client.send(5154, pb.ShopMsg(buyInfo=pb.BuyInfo(goodId=19, count=1, receiveId=999), payType=0))
        assert _one(await a.idle(), 90, pb.ShopMsg).buyInfo.result == handlers.R_NO_PLAYER

        a.client.send(5154, pb.ShopMsg(buyInfo=pb.BuyInfo(goodId=19, count=1), payType=0))
        got = await a.idle()
        assert _one(got, 90, pb.ShopMsg).buyInfo.result == handlers.R_OK
        assert c.consortia_offer == 60
        snap = _session(a).snapshot
        assert snap is not None and any(i.template_id == 2040106 for i in snap.items)


async def test_guild_market_counts_bought_bag_slots(tmp_path: Path) -> None:
    """A mochila é a da loja comum: espaços comprados contam e a compra empilha onde dá."""
    async with logged_in(tmp_path, novice=19000) as a:
        await _create(a)
        s, c = _session(a), _char(a)
        _guild(a).shop_level = 6
        c.consortia_offer = 100
        snap = s.snapshot
        assert snap is not None
        for pos in range(42):  # mochila base cheia de pilhas completas
            item = Item(c.id or 0, 2040106, count=bag.max_count(s.ctx.templates, 2040106))
            item.pos = pos
            snap.items.append(item)

        a.client.send(5154, pb.ShopMsg(buyInfo=pb.BuyInfo(goodId=19, count=1), payType=0))
        assert _one(await a.idle(), 90, pb.ShopMsg).buyInfo.result == handlers.R_FAIL
        assert c.consortia_offer == 100

        c.bag_count = 7  # comprou espaços
        a.client.send(5154, pb.ShopMsg(buyInfo=pb.BuyInfo(goodId=19, count=1), payType=0))
        assert _one(await a.idle(), 90, pb.ShopMsg).buyInfo.result == handlers.R_OK
        assert [i.pos for i in snap.items if i.pos >= 42] == [42]


async def test_altar_bless_and_take(tmp_path: Path) -> None:
    async with logged_in(tmp_path, novice=19000) as a:
        await _create(a)
        c = _char(a)
        c.consortia_offer = 100
        a.client.send(5145, pb.SimplePropertyMsg(param1=1))  # altar nível 0
        assert _one(await a.idle(), 45, pb.ConsortiaMsg).blessSite == -1

        _guild(a).altar_level = 1
        a.client.send(8217)
        sites = _one(await a.idle(), 4144, pb.ConsortiaInfoMsg).site
        a.client.send(5145, pb.SimplePropertyMsg(param1=1))
        bless = _one(await a.idle(), 45, pb.ConsortiaMsg)
        assert sites[bless.blessSite] == 1 and bless.blessLeftTime == 1 and c.consortia_offer == 80

        a.client.send(8216)
        got = await a.idle()
        assert _one(got, 4143, pb.ConsortiaMsg).result
        assert [p for p in got if p.code == 115]
        a.client.send(8215)
        assert _one(await a.idle(), 4141, pb.ConsortiaMsg).blessLeftTime == 1


async def test_altar_open_needs_level_5_and_tells_members(tmp_path: Path) -> None:
    async with logged_in(tmp_path, novice=19000) as a:
        await _create(a)
        guild = _guild(a)
        guild.offer = 60_000
        a.client.send(8541, pb.ConsortiaAltarOpenReqMsg(altarType=0))
        assert not [p for p in await a.idle() if p.code == 4436]

        guild.levels = 5
        a.client.send(8541, pb.ConsortiaAltarOpenReqMsg(altarType=0))
        got = await a.idle()
        assert _one(got, 4436, pb.ConsortiaAltarOpenRspMsg).result == gd.ALTAR_OPEN
        assert _one(got, 164, pb.ConsortiaInfoMsg).altarState == gd.ALTAR_OPEN
        assert guild.offer == 10_000


async def test_guild_shop_daily_limit(tmp_path: Path) -> None:
    """goodId 665 (Lv.40 Efsane Taşı): VIP0Count 5 por dia, como a loja comum."""
    async with logged_in(tmp_path, novice=19000) as a:
        await _create(a)
        s, c = _session(a), _char(a)
        _guild(a).shop_level = 10
        c.consortia_offer, c.grades = 1_000_000, 80
        assert await handlers.shop_buy(s, pb.BuyInfo(goodId=665, count=5))
        assert _one(await a.idle(), 90, pb.ShopMsg).buyInfo.result == handlers.R_OK
        left = c.consortia_offer
        assert await handlers.shop_buy(s, pb.BuyInfo(goodId=665, count=1))
        assert _one(await a.idle(), 90, pb.ShopMsg).buyInfo.result == handlers.R_LIMIT
        assert c.consortia_offer == left  # recusado sem cobrar
