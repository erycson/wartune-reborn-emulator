import random
from pathlib import Path

from tests.game.harness import logged_in
from wartune_server.domain.models import BagType, Item
from wartune_server.game import bag, drops


async def test_carta_da_masmorra_como_no_replay(tmp_path: Path) -> None:
    async with logged_in(tmp_path, novice=19000) as g:
        session = g.server.online.get(g.user_id)
        assert session is not None and session.snapshot is not None
        snap, templates = session.snapshot, g.server.services.templates
        now = session.ctx.clock.now()
        kurt = [1080003, 1080013, 1080002, 1080012, 2040101]  # Campaigns.Item da Kurt İni (1001)
        assert drops.pool(templates, 1001) == kurt
        assert drops.pool(templates, 8200) == [2131002]  # torre: o -700 (EXP) fica de fora
        assert drops.card(snap, templates, 1, 2, now=now) is None  # tutorial: lista vazia, sem 26 (replay #525)
        assert {71004, 70202, 71107, 70705} <= set(bag.random_skill_pool(templates))  # #1241 e #1744

        before = len(snap.items)
        got = drops.card(snap, templates, 1001, 2, random.Random(1), now=now)
        assert got is not None
        item, msg, text = got
        row = templates.get("ItemTempInfos", item.template_id) or {}
        slots = int(row.get("RandomSkillCount") or 0)
        assert item.template_id in kurt and len(snap.items) == before + 1 and item.bag_type == BagType.BAG
        assert (msg.index, msg.templateId, msg.count, msg.bind, msg.pay) == (2, item.template_id, 1, True, False)
        skills = [msg.randomSkill_1, msg.randomSkill_2, msg.randomSkill_3, msg.randomSkill_4, msg.randomSkill_5]
        assert skills == item.random_skills and sum(map(bool, skills)) == slots
        assert text == f"Received: {row['TemplateName']} x1"  # inglês (tutorial_en #507); turco #1242 "Kazanılan:..."

        cid = snap.character.id or 0
        snap.items.extend(Item(cid, 2040101, pos=p) for p in range(bag.BAG_BASE) if not bag.at(snap, BagType.BAG, 0, p))
        assert drops.card(snap, templates, 1001, 2, now=now) is None  # mochila cheia


async def test_carta_sorteia_pela_tabela_do_banco(tmp_path: Path) -> None:
    async with logged_in(tmp_path, novice=19000) as g:
        session = g.server.online.get(g.user_id)
        assert session is not None and session.snapshot is not None
        snap, templates = session.snapshot, g.server.services.templates
        now = session.ctx.clock.now()
        table = g.server.services.world.campaign_cards[1002]  # migração 0034
        assert (2040102, 2.0) in table  # Lvl. 2 Luck Stone: 2 em 2 na captura inglesa, fora do CampaignInfo.Item
        assert {t for t, _ in table} >= set(drops.pool(templates, 1002))  # os do template pesam 1
        got = [drops.card(snap, templates, 1002, 0, random.Random(seed), table=[(2040102, 1.0), (1011104, 0.0)], now=now)
               for seed in range(5)]  # fmt: skip
        assert {item.template_id for item, _, _ in filter(None, got)} == {2040102}  # peso 0 nunca sai
