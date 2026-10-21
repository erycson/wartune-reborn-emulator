"""Montarias: ativar (8529 op 4), carta de montaria (5006, SonType 218), voo (op 13) e as do Beast Soul Lvl."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from tests.game.harness import logged_in
from tests.test_end_to_end import TEMPLATES
from wartune_server.domain.models import Item, PlayerSystems
from wartune_server.game import rules
from wartune_server.game.handlers import systems
from wartune_server.protocol.messages import wartune_pb2 as pb
from wartune_server.services.clock import FakeClock
from wartune_server.templates.repository import GameTemplates

pytestmark = pytest.mark.skipif(not TEMPLATES.exists(), reason="precisa de data/templates")

RUBY, SHADOW, TEMP = 1001, 1002, 1107  # MountType 1 (carta 2180001 ou 1198 Balens), 1, 2 (carta de 10 dias)
RUBY_CARD, TEMP_CARD = 2180001, 2180021


def snap_of(g):  # type: ignore[no-untyped-def]
    session = g.server.online.get(g.user_id)
    assert session is not None and session.snapshot is not None
    return session.snapshot


def owned(got: list) -> dict[int, pb.AvatarInfoMsg]:  # type: ignore[type-arg]
    return {a.mountTempId: a for a in pb.MountAvatarMsg.FromString(got[-1].body).avatarInfo}


async def test_ativar_com_a_carta_ou_com_balens_e_dar_voo(tmp_path: Path) -> None:
    async with logged_in(tmp_path, novice=19000) as g:
        snap = snap_of(g)
        assert snap.systems is not None
        c = snap.character
        c.point = 1198
        card, stone = Item(g.user_id, RUBY_CARD, pos=0), Item(g.user_id, systems.FLYSTONE, pos=1, count=1)
        snap.items.extend([card, stone])
        await g.server.services.characters.save(c, snap.systems, card, stone)
        await g.idle()

        g.client.send(8529, pb.MountEditMsg(op=4, payType=1, param1=RUBY))  # a carta vai primeiro
        got = await g.until(4427)
        assert owned(got)[RUBY].validity == -1 and owned(got)[RUBY].expairDate == "2000-01-01 00:00:00"
        assert (card in snap.items, c.point) == (False, 1198)
        g.client.send(8529, pb.MountEditMsg(op=4, payType=1, param1=RUBY))  # já é dele
        g.client.send(8529, pb.MountEditMsg(op=4, payType=1, param1=1000))  # MountType 0: vem do Beast Soul
        assert await g.idle() == []

        g.client.send(8529, pb.MountEditMsg(op=4, payType=1, param1=SHADOW))  # sem a carta: Property1 Balens
        got = await g.until(4427)
        assert (sorted(owned(got)), c.point) == ([RUBY, SHADOW], 0)

        g.client.send(8529, pb.MountEditMsg(op=13, param1=RUBY))
        got = await g.until(4427)
        assert (owned(got)[RUBY].isBuyFly, owned(got)[SHADOW].isBuyFly, stone in snap.items) == (True, False, False)
        g.client.send(8529, pb.MountEditMsg(op=13, param1=SHADOW))  # acabou a Flystone
        assert await g.idle() == []


async def test_carta_temporaria_soma_dias_e_vence(tmp_path: Path) -> None:
    """2180021: 10 dias da 1107 (``Property2``); a segunda carta soma; vencida some da lista."""
    clock = FakeClock(datetime(2026, 1, 1, tzinfo=UTC))
    async with logged_in(tmp_path, novice=19000, clock=clock) as g:
        snap = snap_of(g)
        assert snap.systems is not None
        snap.character.grades = 40  # NeedGrades da carta
        cards = Item(g.user_id, TEMP_CARD, pos=0, count=2)
        snap.items.append(cards)
        await g.server.services.characters.save(snap.character, snap.systems, cards)
        await g.idle()

        g.client.send(5006, pb.ItemUseMsg(pos=0, count=1, bagType=1))
        assert owned(await g.until(4427))[TEMP].validity == 10
        g.client.send(5006, pb.ItemUseMsg(pos=0, count=1, bagType=1))
        assert owned(await g.until(4427))[TEMP].validity == 20
        now = clock.now()
        assert systems.avatars(snap.systems, now + timedelta(days=19)) == [TEMP]
        assert systems.avatars(snap.systems, now + timedelta(days=21)) == []

        g.client.send(8529, pb.MountEditMsg(op=2, param1=TEMP))
        await g.until(4426)
        clock.advance(21 * 86400)
        g.client.send(20008)  # relógio: a montaria vencida sai de uso
        got = await g.until(4427)
        assert (snap.systems.mount_template, owned(got)) == (0, {})


def test_beast_soul_da_as_montarias_do_nivel() -> None:
    """Tabela 19: nível 2 com 13000 de EXP total dá a 1006 (``ActiveObject``)."""
    templates = GameTemplates(
        {
            "UpGradeTempInfos": [
                {"Types": "19", "Grades": "1", "Data": "0", "ActiveObject": "0"},
                {"Types": "19", "Grades": "2", "Data": "13000", "ActiveObject": "1006"},
                {"Types": "19", "Grades": "3", "Data": "64000", "ActiveObject": "2001"},
            ]
        }
    )
    sy = PlayerSystems(1, mount_gp="5000,5000,2999,0", mount_avatars="1000")
    now = datetime(2026, 1, 1, tzinfo=UTC)
    assert (systems.soul_grade(templates, sy), systems.soul_mounts(templates, sy, now)) == (1, False)
    sy.mount_gp = "5000,5000,3000,0"
    assert (systems.soul_grade(templates, sy), systems.soul_mounts(templates, sy, now)) == (2, True)
    assert sy.mount_avatars == "1000,1006"


async def test_estrela_gasta_hoof_enche_a_bencao_e_sobe(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """op 6 na 1000 (GradeType 5: 50 de bênção até a estrela 1, StarAddition +10): o primeiro refino é de graça
    (firstBless), o 10x gasta 10 Hoofs; a estrela soma nos 4 atributos da montaria em uso."""
    monkeypatch.setattr(systems.random, "randrange", lambda n: n - 1)  # sem o "Therion's Blessing"
    async with logged_in(tmp_path, novice=19000) as g:
        snap = snap_of(g)
        sy = snap.systems
        assert sy is not None
        snap.character.grades = systems.STAR_GRADE
        sy.mount_avatars, sy.mount_template = "1000", 1000
        hoofs = Item(g.user_id, systems.HOOF, pos=0, count=20)
        snap.items.append(hoofs)
        await g.server.services.characters.save(snap.character, sy, hoofs)
        await g.idle()
        before = rules.mount_stats(snap, g.server.services.templates)

        g.client.send(8529, pb.MountEditMsg(op=6, propertyType=1000))
        star = pb.AvatarInfoMsg.FromString((await g.until(4679))[-1].body)
        assert (star.mountTempId, star.starLevel, star.blessing, hoofs.count) == (1000, 0, 10, 20)

        g.client.send(8529, pb.MountEditMsg(op=6, propertyType=1000, param1=1))
        got = await g.until(4426)
        star = pb.AvatarInfoMsg.FromString(next(p for p in got if p.code == 4679).body)
        assert (star.starLevel, star.blessing, hoofs.count) == (1, 60, 10)  # 4 refinos até 50, mais 6
        info = pb.MountInfoMsg.FromString(got[-1].body)
        assert info.power == before["Power"] + 10
        assert [p.code for p in await g.idle()] == [150]  # o exército com a montaria nova

        snap.character.grades = systems.STAR_GRADE - 1
        g.client.send(8529, pb.MountEditMsg(op=6, propertyType=1000))
        assert await g.idle() == []
