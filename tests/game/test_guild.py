from datetime import timedelta
from pathlib import Path

from sqlalchemy import select

from tests.game.harness import Game, logged_in
from wartune_server.domain.models import CashLedger, Character, Consortia, Item
from wartune_server.game import bag, rules
from wartune_server.game import events as ev
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
    return await g.until(164) + await g.idle()  # o 164 fecha a criação; só idle() perde a guilda sob carga


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


async def test_joining_matches_the_official_sequence(tmp_path: Path) -> None:
    """(visto) oficial_20261023-171155-1 #4561-#4567: 3, 150, 117, 111, 4266 a quem entrou; 83 do canal 5 a todos."""
    async with logged_in(tmp_path, novice=19000) as a:
        await _create(a)
        other = await a.join("bruxa")
        _rich(other)
        other.client.send(5135, pb.ConsortiaMsg(consortiaId=_guild(a).id))
        apply_id = _one(await other.idle(), 35, pb.ConsortiaMsg).applyId
        a.client.send(5134, pb.ConsortiaMsg(applyId=apply_id, result=True))
        got = await other.idle()
        assert [p.code for p in got if p.code in (3, 150, 117, 111, 4266, 83, 164)] == [3, 150, 117, 111, 4266, 83, 164]
        alert = _one(got, 111, pb.ChatChannelMsg).encodeMsg
        assert alert == "Congratulations! You have joined Guild  [Lobos]."
        chat = _one(got, 83, pb.ChatChannelMsg)
        assert (chat.channel, chat.type, chat.otherId) == (5, 5, -1)
        assert chat.encodeMsg.endswith(
            'name="Bruxa" consortiaId="1" serverName="" grades="0" /> has just become the guilds newest member!'
        )
        assert _one(await a.idle(), 83, pb.ChatChannelMsg).encodeMsg == chat.encodeMsg


async def test_recruit_notice_five_per_day(tmp_path: Path) -> None:
    """8335: 5 anúncios por dia (visto ``speakTimes`` 5 no oficial), só com o direito de recrutar; 83 tipo 2 no mundo."""
    async with logged_in(tmp_path, novice=19000) as a:
        got = await _create(a)
        info = _one(got, 164, pb.ConsortiaInfoMsg)
        assert info.speakTimes == 5 and info.fightPower == _char(a).fighting_capacity
        assert info.orderInfo.fightPowerOrder == 1
        b = await _member(a, "bruxa")
        b.client.send(8335, pb.ConditionSpeakMsg(speak="nao pode"))  # membro comum: sem o direito 9
        assert not [p for p in await b.idle() if p.code == 83]
        for left in (4, 3, 2, 1, 0):
            a.client.send(8335, pb.ConditionSpeakMsg(speak="Venham!"))
            got = await a.idle()
            chat = _one(got, 83, pb.ChatChannelMsg)
            assert (chat.channel, chat.type, chat.encodeMsg, chat.consortiaName) == (10, 2, "Venham!", "Lobos")
            assert _one(got, 164, pb.ConsortiaInfoMsg).speakTimes == left
            assert _one(await b.idle(), 83, pb.ChatChannelMsg).encodeMsg == "Venham!"
        a.client.send(8335, pb.ConditionSpeakMsg(speak="sexto"))
        assert not [p for p in await a.idle() if p.code == 83]
        tomorrow = _session(a).ctx.clock.now() + timedelta(days=1)
        assert gd.speak_left(_session(a).ctx.templates, _guild(a), tomorrow) == 5


async def test_guild_war_groups_list_the_guilds_by_power(tmp_path: Path) -> None:
    """8546 -> 4441 e 4458 (visto #5135-#5136), com as guildas pelo poder (a guerra em si não roda)."""
    async with logged_in(tmp_path, novice=19000) as a:
        await _create(a)
        a.client.send(8546)
        got = await a.idle()
        assert [p.code for p in got if p.code in (4441, 4458)] == [4441, 4458]
        teams, order = _one(got, 4441, pb.GuildGroupListMsg), _one(got, 4458, pb.GuildGroupListMsg)
        assert [(x.consortiaName, x.fightPower) for x in teams.group] == [("Lobos", _char(a).fighting_capacity)]
        assert not teams.isGuildSize and [x.order for x in order.group] == [1] and order.orderTime


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
        await c.idle()
        a.client.send(5142, pb.ConsortiaMsg(otherId=c.user_id))  # abaixo do 12 (ConsortiaRecruitFrame)
        assert not [p for p in await c.idle() if p.code == 41]
        _rich(c)
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
        got = await a.idle()  # (visto) 231733 #4448-#4449: 164 e o aviso no chat da guilda
        assert [p.code for p in got if p.code in (164, 83)] == [164, 83]
        assert _one(got, 83, pb.ChatChannelMsg).encodeMsg.endswith(
            f'name="Bruxa" consortiaId="{_guild(a).id}" serverName="" grades="0" />'
        )
        assert " kicked " in _one(got, 83, pb.ChatChannelMsg).encodeMsg
        assert _session(a).ctx.guilds.of(b.user_id) is None


async def test_contribution_matches_the_capture(tmp_path: Path) -> None:
    """Captura birlik_katkisi (só turco): -1000 ouro dá +1, -55000 dá +55 (hoje 1 -> 56)."""
    async with logged_in(tmp_path, novice=19000) as a:
        await _create(a)
        c = _char(a)
        gold = c.gold
        a.client.send(5144, pb.ConsortiaUserOfferReqMsg(offerGold=1000))
        got = await a.idle()
        leed = _one(got, 4152, pb.LeedUpdatedRspMsg)  # leed 8 "Contribute to your Guild" (só turco: birlik_katkisi #11)
        assert [(x.templateId, x.isComplete) for x in leed.leed] == [(8, True)]
        # (visto) oficial_20261023-171155-1 #4951-#4961: o 83 da devoção vai por último
        assert [p.code for p in got if p.code in (111, 4152, 150, 42, 164, 83)] == [111, 4152, 150, 42, 164, 83]
        a.client.send(5144, pb.ConsortiaUserOfferReqMsg(offerGold=55999))
        got = await a.idle()
        assert [p.code for p in got if p.code in (109, 3, 111, 150, 42, 164, 83)] == [109, 3, 111, 150, 42, 164]
        assert _one(got, 42, pb.ConsortiaMsg).result
        assert _one(got, 164, pb.ConsortiaInfoMsg).offer == 56
        assert (c.gold, c.consortia_offer, c.consortia_total_offer) == (gold - 56000, 56, 56)

        a.client.send(8208, pb.ConsortiaOfferReqMsg(pageIndex=1))
        ranking = _one(await a.idle(), 4134, pb.ConsortiaContributeRspMsg)
        assert (ranking.selfOrder, ranking.selfInfo.todayOffer, ranking.selfInfo.totalOffer) == (1, 56, 56)

        a.client.send(5144, pb.ConsortiaUserOfferReqMsg(offerGold=10**9))  # mais ouro que tem
        assert not [p for p in await a.idle() if p.code == 42]

        # 5 Balens = 1 (cliente inglês), vinculados primeiro; o resto que não vira contribuição fica
        c.point, c.gift_token = 100, 3
        a.client.send(5144, pb.ConsortiaUserOfferReqMsg(offerPoint=4))
        assert not [p for p in await a.idle() if p.code == 42]
        a.client.send(5144, pb.ConsortiaUserOfferReqMsg(offerPoint=12))
        assert _one(await a.idle(), 164, pb.ConsortiaInfoMsg).offer == 58
        assert (c.point, c.gift_token, c.consortia_offer) == (93, 0, 58)
        async with a.server.services.database.sessions() as db:
            ledger = (await db.execute(select(CashLedger))).scalars().all()
        assert [(e.delta_point, e.delta_gift_token, e.reason) for e in ledger] == [(-7, -3, "guild_contribute")]


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
        before = rules.leader_stats(_session(a).snapshot, _session(a).ctx.templates, None)
        got = await a.idle()
        # (visto) oficial_20261023-171155-1 #5045-#5051
        assert [p.code for p in got if p.code in (3, 110, 150, 111)] == [3, 110, 150, 3, 111]
        old, new = (pb.PlayerMsg.FromString(p.body) for p in got if p.code == 3)
        assert (old.consortiaAttack, old.consortiaOffer, new.consortiaAttack) == (0, 800, 1)
        bonus = pb.PropertyUpdatedMsg.FromString(next(p.body for p in got if p.code == 110))
        assert (bonus.propertyType, bonus.value) == (3, 40)
        after = rules.leader_stats(_session(a).snapshot, _session(a).ctx.templates, None)
        gain = {k: after.total[k] - before.total[k] for k in ("Power", "PhyAttack", "PhyDefence")}
        assert gain == {"Power": 40, "PhyAttack": 160, "PhyDefence": 40}  # "Strength +40 (Hero)"
        assert c.consortia_offer == 800


async def test_guild_shop_pays_with_contribution(tmp_path: Path) -> None:
    """Captura (só turco: birlik_katkisi): goodId 19 = 2040106 "Lvl. 6 Luck Stone", 40 de contribuição, mercado nível 6."""
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
        assert sorted(sites) == list(range(1, 11))  # oficial #5151: as 10 casas embaralhadas
        a.client.send(5145, pb.SimplePropertyMsg(param1=1))
        got = await a.idle()
        bless = _one(got, 45, pb.ConsortiaMsg)
        assert sites[bless.blessSite] == 1 and bless.blessLeftTime == 1 and c.consortia_offer == 80
        shout = _one(got, 83, pb.ChatChannelMsg)  # (visto) oficial_encantar #1749: o prêmio para o servidor
        assert shout.channel == 2 and shout.encodeMsg.startswith(f'Congratulations to <a t="1" id="{c.id}"')
        assert f'tempid="{bless.blessTempId}"' in shout.encodeMsg and shout.encodeMsg.endswith(
            " x1 from Guild Blessing!"
        )

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
    """goodId 665 (Lvl. 40 Legendary Stone): VIP0Count 5 por dia, como a loja comum."""
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


async def test_guild_creation_saves_guild_member_and_event_together(tmp_path: Path) -> None:
    """Criar grava guilda, membro e evento na mesma transação (o membro precisa do id da guilda)."""
    async with logged_in(tmp_path, novice=19000) as a:
        await _create(a)
        guild = _guild(a)
        _, members, _, events, _ = await _session(a).ctx.characters.guild_state(_char(a).server_id)
        assert [(m.consortia_id, m.character_id, m.duty_id) for m in members] == [(guild.id, a.user_id, gd.CHAIRMAN)]
        assert [e.consortia_id for e in events] == [guild.id]


async def test_altar_prize_is_saved_on_the_member(tmp_path: Path) -> None:
    """O prêmio da bênção fica na linha do membro: recarregar a guilda do banco (reinício) o devolve."""
    async with logged_in(tmp_path, novice=19000) as a:
        await _create(a)
        s, c = _session(a), _char(a)
        _guild(a).altar_level = 1
        c.consortia_offer = 100
        a.client.send(5145, pb.SimplePropertyMsg(param1=1))
        assert _one(await a.idle(), 45, pb.ConsortiaMsg).blessSite != -1

        reloaded = await gd.Guilds.load(s.ctx.characters, c.server_id)
        member = reloaded.members[a.user_id]
        assert member.bless_item > 0 and member.bless_item_count == 1
        a.client.send(8215)
        assert _one(await a.idle(), 4142, pb.ItemInfoMsg).templateId == member.bless_item


async def test_altar_prize_waits_for_a_free_bag_slot(tmp_path: Path) -> None:
    """Mochila cheia não perde o prêmio: ele espera um espaço, e o espaço comprado conta."""
    async with logged_in(tmp_path, novice=19000) as a:
        await _create(a)
        s, c = _session(a), _char(a)
        _guild(a).altar_level = 1
        c.consortia_offer = 100
        snap = s.snapshot
        assert snap is not None
        for pos in range(42):  # mochila base cheia de pilhas completas
            item = Item(c.id or 0, 2040106, count=bag.max_count(s.ctx.templates, 2040106))
            item.pos = pos
            snap.items.append(item)
        a.client.send(5145, pb.SimplePropertyMsg(param1=1))
        assert _one(await a.idle(), 45, pb.ConsortiaMsg).blessSite != -1
        member = s.ctx.guilds.members[a.user_id]

        a.client.send(8216)
        assert not _one(await a.idle(), 4143, pb.ConsortiaMsg).result
        assert member.bless_item > 0

        c.bag_count = 7  # comprou espaços: o prêmio entra no primeiro livre, depois dos 42
        a.client.send(8216)
        got = await a.idle()
        assert _one(got, 4143, pb.ConsortiaMsg).result
        assert [i.pos for i in snap.items if i.pos >= 42] == [42]
        assert member.bless_item == 0 and member.bless_item_count == 0


async def test_box_item_goes_by_mail_when_the_bag_is_full(tmp_path: Path) -> None:
    """Item do baú: cabe na mochila entra nela; sem espaço vai pelo correio, com o item como anexo."""
    async with logged_in(tmp_path, novice=19000) as a:
        await _create(a)
        b = await _member(a, "bruxa")
        s = _session(a)
        await s.ctx.characters.save(handlers.add_to_box(s, _guild(a).id or 0, 2060044, 3))  # quem chama grava
        full = _session(b).snapshot
        assert full is not None
        for pos in range(42):
            item = Item(full.character.id or 0, 2040106, count=bag.max_count(s.ctx.templates, 2040106))
            item.pos = pos
            full.items.append(item)

        a.client.send(
            8578,
            pb.ConsortiaTreasureBoxMsg(
                templateId=2060044,
                playerInfo=[
                    pb.ConsortiaMembersInfoMsg(userId=b.user_id, count=2),
                    pb.ConsortiaMembersInfoMsg(userId=a.user_id, count=1),
                ],
            ),
        )
        got = await a.idle()
        box = _one(got, 4466, pb.ConsortiaStorageInfoMsg).storageInfo  # 3 distribuídos: baú zerado
        assert [(i.templateId, i.count) for i in box] == [(2060044, 0)]  # a linha fixa do oficial
        mine = s.snapshot
        assert mine is not None
        assert [i.count for i in mine.items if i.template_id == 2060044] == [1]
        assert not [i for i in full.items if i.template_id == 2060044]
        assert 148 in [p.code for p in await b.idle()]  # aviso do correio para quem está online

        mails = await s.ctx.characters.read(lambda uow: uow.mails.by_receiver(b.user_id))
        annexes = await s.ctx.characters.read(lambda uow: uow.mails.annexes([m.id or 0 for m in mails]))
        assert [(x.template_id, x.count) for x in annexes if x.template_id == 2060044] == [(2060044, 2)]


async def test_creating_hides_own_applications_before_the_write(tmp_path: Path) -> None:
    """Durante a gravação da criação, a candidatura dele já saiu da memória: outra guilda não o aceita (5134)."""
    async with logged_in(tmp_path, novice=19000) as a:
        await _create(a)
        b = await a.join("bruxa")
        _rich(b)
        b.client.send(5135, pb.ConsortiaMsg(consortiaId=_guild(a).id))
        apply_id = _one(await b.idle(), 35, pb.ConsortiaMsg).applyId
        s = _session(b)
        chars = s.ctx.characters
        real, seen = chars.write, []

        async def spy(change):  # type: ignore[no-untyped-def]
            seen.append(s.ctx.guilds.invite(apply_id))
            return await real(change)

        chars.write = spy  # type: ignore[method-assign]
        try:
            b.client.send(5130, pb.ConsortiaMsg(consortiaName="Corvos"))
            assert _one(await b.idle(), 117, pb.ConsortiaMsg).consortiaId
        finally:
            chars.write = real  # type: ignore[method-assign]
        assert seen == [None]


async def test_guild_mail_from_the_chairman_costs_175_balens(tmp_path: Path) -> None:
    """ConsortiaEmailGroupSendView (inglês): só o chefe, para membros da guilda, "Spend 175 Balens"."""
    async with logged_in(tmp_path, novice=19000) as a:
        await _create(a)
        b = await _member(a, "bruxa")
        c = _char(a)
        c.point, c.gift_token = 200, 0
        mail = pb.MailSendReqMsg(sendType=2, receiverUserId=[b.user_id, 999], title="aviso", contents="guerra")
        a.client.send(8205, mail)  # 999 não é da guilda
        assert not [p for p in await b.idle() if p.code == 148] and c.point == 200
        del mail.receiverUserId[1]
        a.client.send(8205, mail)
        await b.until(148)
        assert c.point == 25
        async with a.server.services.database.sessions() as db:
            ledger = (await db.execute(select(CashLedger))).scalars().all()
        assert [(e.delta_point, e.reason) for e in ledger] == [(-175, "guild_mail")]

        _char(b).point = 1000
        b.client.send(8205, pb.MailSendReqMsg(sendType=2, receiverUserId=[a.user_id], title="oi", contents="chefe"))
        assert not [p for p in await a.idle() if p.code == 148] and _char(b).point == 1000  # membro comum


async def test_altar_bless_with_a_prize_waiting_abandons_it(tmp_path: Path) -> None:
    """ConsortiaAltarHelper.canBless: com prêmio por pegar o cliente pergunta e só manda o 5145 se o jogador
    abandonar; o prêmio novo toma o lugar."""
    async with logged_in(tmp_path, novice=19000) as a:
        await _create(a)
        s, c = _session(a), _char(a)
        _guild(a).altar_level = 1
        c.consortia_offer = 100
        s.ctx.guilds.members[a.user_id].bless_item = 1  # prêmio antigo, não pego
        a.client.send(5145, pb.SimplePropertyMsg(param1=1))
        assert _one(await a.idle(), 45, pb.ConsortiaMsg).blessSite != -1
        assert s.ctx.guilds.members[a.user_id].bless_item not in (0, 1)


async def test_quit_paying_the_cooldown_costs_consortia_clear_cd_point(tmp_path: Path) -> None:
    """ConsortiaFrame.checkTxt: sem o cartão 208013, ``Consortia_ClearCD_Point`` (395) Balens e sem espera."""
    async with logged_in(tmp_path, novice=19000) as a:
        await _create(a)
        b = await _member(a, "bruxa")
        c = _char(b)
        c.point, c.gift_token = 500, 0
        b.client.send(5146, pb.ConsortiaQuitReqMsg(clear_CDType=1))
        assert _one(await b.idle(), 117, pb.ConsortiaMsg).consortiaId == 0
        assert c.point == 105 and not c.is_auto
        async with a.server.services.database.sessions() as db:
            ledger = (await db.execute(select(CashLedger))).scalars().all()
        assert [(e.delta_point, e.reason) for e in ledger if e.reason == "guild_clear_cd"] == [(-395, "guild_clear_cd")]
        b.client.send(5135, pb.ConsortiaMsg(consortiaId=_guild(a).id))  # sem as 24 h
        assert [p for p in await b.idle() if p.code == 35]


async def test_events_follow_consortia_event_item_parts(tmp_path: Path) -> None:
    """ConsortiaEventItem.decode parte o remark por "|" e monta pelo tipo; frase sem as partes vira "undefined"."""
    async with logged_in(tmp_path, novice=19000) as a:
        await _create(a)
        b = await _member(a, "bruxa")
        a.client.send(5132, pb.ConsortiaMsg(otherId=b.user_id))
        await a.idle()
        a.client.send(8210)
        got = _one(await a.idle(), 4136, pb.ConsortiaEventListRspMsg).eventInfo
        assert [(e.type, e.remark) for e in got] == [
            (3, "Maga|founded the guild."),
            (3, "Bruxa|joined the guild."),
            (1, "Maga|expelled|Bruxa|from the guild."),
        ]


async def test_election_lists_candidates_and_my_vote_like_election_list_view(tmp_path: Path) -> None:
    """ElectionListView: ``isVotingman`` = candidato; o "já votou" sai da própria linha (``votingTime > 0``)."""
    async with logged_in(tmp_path, novice=19000) as a:
        await _create(a)
        b = await _member(a, "bruxa")
        guild = _guild(a)
        guild.voting_state, guild.voting_id = 3, 7
        _char(b).consortia_offer = 100
        b.client.send(8241)
        got = _one(await b.idle(), 4389, pb.ConsortiaVotingUsersMsg).info
        assert [(u.userId, u.isVotingman, u.votingTime) for u in got] == [(a.user_id, True, 0), (b.user_id, False, 0)]
        b.client.send(8481, pb.ConsortiaVotingReqMsg(votingUser=a.user_id))
        assert _one(await b.idle(), 4390, pb.ConsortiaVotingRspMsg).result
        b.client.send(8241)
        got = _one(await b.idle(), 4389, pb.ConsortiaVotingUsersMsg).info
        assert [(u.userId, u.votingTime, u.votingData) for u in got] == [(a.user_id, 0, 1), (b.user_id, 1, 0)]


async def test_member_list_shows_the_vip_of_online_members(tmp_path: Path) -> None:
    """ConsortiaMemberItem: nome VIP e Ã­cone pelo ``isVip``/``vipType``."""
    async with logged_in(tmp_path, novice=19000) as a:
        await _create(a)
        b = await _member(a, "bruxa")
        snap, now = _session(b).snapshot, _session(b).ctx.clock.now()
        assert snap is not None
        ev.state(snap, "vip", now).text = (now + timedelta(days=1)).strftime(ev.TIME_FMT)
        ev.state(snap, "vip:type", now).value = 2
        a.client.send(8207)
        got = [p for p in await a.idle() if p.code == 4133]
        rows = [r for p in got for r in pb.SimplePlayerListRspMsg.FromString(p.body).playerInfo]
        assert sorted((r.userId, r.isVip, r.vipType) for r in rows) == [(a.user_id, False, 0), (b.user_id, True, 2)]


async def test_guild_name_is_4_to_10_client_bytes_and_merged_names_rename_free(tmp_path: Path) -> None:
    """CreatConsortiaFrame/ConsortiaRenameFrame: 4 a 10 com [^\x00-\xff] valendo 2; "!" no nome renomeia grátis."""
    async with logged_in(tmp_path, novice=19000) as a:
        await _create(a, "Lobo")
        assert _guild(a).name == "Lobo"
        b = await a.join("bruxa")
        _rich(b)
        for bad in ("Lob", "Lobosdonorte", "Ñandú本本本"):
            b.client.send(5130, pb.ConsortiaMsg(consortiaName=bad))
            await b.idle()
            assert _session(b).ctx.guilds.of(b.user_id) is None, bad
        c = _char(a)
        c.point, c.gift_token = 1000, 0
        _guild(a).name = "Lobo!s1"
        a.client.send(5148, pb.ConsortiaRenameReqMsg(newName="Corvos", same=True, payType=1))
        assert _one(await a.idle(), 49, pb.ConsortiaRenameRspMsg).result
        assert (_guild(a).name, c.point) == ("Corvos", 1000)
        a.client.send(5148, pb.ConsortiaRenameReqMsg(newName="Gralhas", same=True, payType=1))  # sem "!": paga
        assert _one(await a.idle(), 49, pb.ConsortiaRenameRspMsg).result
        assert (_guild(a).name, c.point) == ("Gralhas", 0)


async def test_accepting_someone_already_in_another_guild_drops_the_old_application(tmp_path: Path) -> None:
    """ApplyPlayerList tira a linha e espera um 40; a candidatura velha não volta na lista."""
    async with logged_in(tmp_path, novice=19000) as a:
        await _create(a)
        c = await a.join("clara")
        await _create(c, "Corvos")
        b = await a.join("bruxa")
        _rich(b)
        b.client.send(5135, pb.ConsortiaMsg(consortiaId=_guild(c).id))
        old = _one(await b.idle(), 35, pb.ConsortiaMsg).applyId
        b.client.send(5135, pb.ConsortiaMsg(consortiaId=_guild(a).id))
        new = _one(await b.idle(), 35, pb.ConsortiaMsg).applyId
        a.client.send(5134, pb.ConsortiaMsg(applyId=new, result=True))
        await b.until(117)
        c.client.send(5134, pb.ConsortiaMsg(applyId=old, result=True))
        assert [p for p in await c.idle() if p.code == 40]
        assert _guild(b).id == _guild(a).id


async def test_box_gives_at_most_10_to_each_member(tmp_path: Path) -> None:
    """ConsortiaPrizeAllotItem.changeReceviedCount: no máximo 10 por membro."""
    async with logged_in(tmp_path, novice=19000) as a:
        await _create(a)
        s = _session(a)
        await s.ctx.characters.save(handlers.add_to_box(s, _guild(a).id or 0, 2060044, 20))
        box = pb.ConsortiaTreasureBoxMsg(templateId=2060044, playerInfo=[{"userId": a.user_id, "count": 11}])
        a.client.send(8578, box)
        assert not [p for p in await a.idle() if p.code == 4466]
        box.playerInfo[0].count = 10
        a.client.send(8578, box)
        assert [i.count for i in _one(await a.idle(), 4466, pb.ConsortiaStorageInfoMsg).storageInfo] == [10]


async def test_guild_warehouse_is_bag_6_with_store_level_times_5_cells(tmp_path: Path) -> None:
    """ConsortiaCaseBag: bolsa 6, ``storeLevel*5`` espaços (ConsortiaModel.currentCasecellNum); "Sort" é o 8220."""
    async with logged_in(tmp_path, novice=19000) as a:
        await _create(a)
        snap = _session(a).snapshot
        assert snap is not None
        item = Item(a.user_id, 2040106, pos=0)
        snap.items.append(item)
        await _session(a).ctx.characters.save(item)
        a.client.send(5005, pb.ItemReqMsg(beginBagType=1, beginPos=0, endBagType=6, endPos=0))  # nível 0: fechado
        assert await a.idle() == [] and item.bag_type == 1
        _guild(a).store_level = 1
        a.client.send(5005, pb.ItemReqMsg(beginBagType=1, beginPos=0, endBagType=6, endPos=5))  # só 0 a 4
        assert await a.idle() == [] and item.bag_type == 1
        a.client.send(5005, pb.ItemReqMsg(beginBagType=1, beginPos=0, endBagType=6, endPos=4))
        await a.idle()
        assert (item.bag_type, item.pos) == (6, 4)
        a.client.send(8220, pb.ArrangeReq(bagType=6, arrangeInfo=[pb.ArrangeInfo(oldplace=4, newplace=0)]))
        await a.idle()
        assert (item.bag_type, item.pos) == (6, 0)


async def test_grade_order_ranks_guilds_by_level_then_wealth(tmp_path: Path) -> None:
    """``orderInfo.gradeOrder`` (ConsortiaActivityPage): sai 0 sem isso; o critério é dedução."""
    async with logged_in(tmp_path, novice=19000) as a:
        await _create(a)
        c = await a.join("clara")
        await _create(c, "Corvos")
        _guild(c).total_offer = 10
        a.client.send(8212)
        assert _one(await a.idle(), 4138, pb.ConsortiaInfoMsg).orderInfo.gradeOrder == 2
        _guild(a).levels = 2
        a.client.send(8212)
        assert _one(await a.idle(), 4138, pb.ConsortiaInfoMsg).orderInfo.gradeOrder == 1


async def test_vip_trial_card_tells_the_guild_chat_4455(tmp_path: Path) -> None:
    """ConsortiaGroupChatControler: o 4455 troca o ícone VIP do membro no chat em grupo."""
    async with logged_in(tmp_path, novice=19000) as a:
        await _create(a)
        b = await _member(a, "bruxa")
        snap = _session(b).snapshot
        assert snap is not None
        card = Item(b.user_id, 2031201, pos=0)  # VIP Trial Card
        snap.items.append(card)
        await _session(b).ctx.characters.save(card)
        b.client.send(5006, pb.ItemUseMsg(pos=0, count=1, bagType=1))
        vip = _one(await a.idle(), 4455, pb.VipToConsortiaMsg)
        assert (vip.userid, vip.isVip, vip.vipType, vip.consortiaId) == (b.user_id, True, 2, _guild(a).id)


async def test_applications_list_newest_first_with_the_day_at_midnight(tmp_path: Path) -> None:
    """(visto) oficial_20261023-171155-1 #4249-#4260: 5135 -> 35 com o ``applyId``; o 4135 lista a candidatura mais
    nova primeiro, com ``createDate`` e ``inviteDate`` no dia da candidatura à meia-noite."""
    async with logged_in(tmp_path, novice=19000) as a:
        await _create(a, "Lobos")
        b = await a.join("bruxa")
        await _create(b, "Corvos")
        c = await a.join("clara")
        _rich(c)
        await c.idle()
        ids = []
        for g in (a, b):
            c.client.send(5135, pb.ConsortiaMsg(consortiaId=_guild(g).id))
            ids.append(_one(await c.idle(), 35, pb.ConsortiaMsg).applyId)
        c.client.send(8209)
        rows = _one(await c.idle(), 4135, pb.ConsortiaUserInviteInfoListRspMsg).inviteInfo
        assert [(r.id, r.consortiaName, r.chairmanNickname) for r in rows] == [
            (ids[1], "Corvos", "Bruxa"), (ids[0], "Lobos", "Maga")
        ]  # fmt: skip
        assert {(r.createDate[11:], r.inviteDate[11:], r.isexist, r.fromType) for r in rows} == {
            ("00:00:00", "00:00:00", True, False)
        }
