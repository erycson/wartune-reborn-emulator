import xml.etree.ElementTree as ET
import zlib
from datetime import timedelta
from pathlib import Path

from tests.game.harness import logged_in
from wartune_server.domain.repositories import UnitOfWork
from wartune_server.game import events as ev
from wartune_server.game import rankings
from wartune_server.protocol.messages import wartune_pb2 as pb


async def test_challenge_order_is_the_colosseum_top_like_the_official_file(tmp_path: Path) -> None:
    """HeroRankFrame lê ``..item`` com ``curRank`` (coliseu), ``order`` (gpOrder), guilda e VIP; zlib (loader 5)."""
    async with logged_in(tmp_path, novice=19000) as a:
        b = await a.join("outro")
        services = a.server.services
        sa, sb = a.server.online.get(a.user_id), a.server.online.get(b.user_id)
        assert sa is not None and sa.snapshot is not None and sb is not None and sb.snapshot is not None
        sb.snapshot.character.total_gp = 10_000  # mais EXP: order 1
        now = services.clock.now()
        vip = ev.state(sa.snapshot, "vip", now)
        vip.text = (now + timedelta(days=1)).strftime(ev.TIME_FMT)
        await services.characters.save(sb.snapshot.character, vip)
        sa.snapshot.character.grades, sa.snapshot.character.gold = 20, 1_000_000
        a.client.send(5130, pb.ConsortiaMsg(consortiaName="Lobos"))
        await a.idle()

        async def ranks(uow: UnitOfWork) -> None:
            await uow.arena.set_rank(b.user_id, 1)
            await uow.arena.set_rank(a.user_id, 2)

        await services.characters.write(ranks)
        body = await rankings.challenge_order(services.characters, services.guilds, 1, services.clock)
        items = ET.fromstring(zlib.decompress(body))
        got = [
            (i.get("userId"), i.get("curRank"), i.get("order"), i.get("IsVip"), i.get("consortiaName")) for i in items
        ]
        assert got == [(str(b.user_id), "1", "1", "false", ""), (str(a.user_id), "2", "2", "true", "Lobos")]

        rankings.write(tmp_path, "challengeorder.xml", body)
        assert (tmp_path / "challengeorder.xml").read_bytes() == body


async def test_fight_xml_is_the_power_ranking_the_sort_controller_reads(tmp_path: Path) -> None:
    """``SortController.read``: ``..PlayerFight`` com ``nikcName``/``fightCapaity`` (sic) e ``info@createDate``."""
    async with logged_in(tmp_path, novice=19000) as a:
        b = await a.join("outro")
        services = a.server.services
        sa, sb = a.server.online.get(a.user_id), a.server.online.get(b.user_id)
        assert sa is not None and sa.snapshot is not None and sb is not None and sb.snapshot is not None
        sa.snapshot.character.fighting_capacity, sb.snapshot.character.fighting_capacity = 500, 900
        sa.snapshot.character.total_gp = 10_000
        sc = a.server.online.get((await a.join("branco")).user_id)
        assert sc is not None and sc.snapshot is not None
        blank = sc.snapshot.character  # como a conta que só fez o POST /login: inativa e sem nome, fora dos rankings
        blank.active, blank.nickname, blank.fighting_capacity, blank.total_gp = False, None, 99_999, 99_999
        await services.characters.save(sa.snapshot.character, sb.snapshot.character, blank)
        root = ET.fromstring(
            zlib.decompress(await rankings.fight_order(services.characters, services.guilds, 1, services.clock))
        )
        assert root.find("info") is not None and root.find("info").get("createDate")  # type: ignore[union-attr]
        got = [
            (p.get("userid"), p.get("orderId"), p.get("fightCapaity"), p.get("CurrentOrder"))
            for p in root.iter("PlayerFight")
        ]
        assert got == [(str(b.user_id), "1", "900", "2"), (str(a.user_id), "2", "500", "1")]
        assert root.find("PlayerFight").get("job") == str(sb.snapshot.character.job)  # type: ignore[union-attr]
