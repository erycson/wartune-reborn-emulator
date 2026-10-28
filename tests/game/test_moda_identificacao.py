import random
from pathlib import Path

from tests.game.harness import logged_in
from tests.game.test_shop import codes, me
from wartune_server.domain.models import BagType, FashionBook, Item
from wartune_server.game.handlers import fashion
from wartune_server.protocol.messages import wartune_pb2 as pb

BEACH = 1100303  # Beach Style: SonType 110, Property1 600000 de ouro (visto: 109 de 26/10 #2521-#2525), TransformId 3
WINGS = 1090000  # Wings of Apollo: SonType 109
WILDCARD = 208020  # Fashion Core


class Fixed(random.Random):
    """Sorteio fixo: ``randrange`` devolve ``roll`` (0 acerta sempre, 99 erra as chances até 60%)."""

    def __init__(self, roll: int) -> None:
        super().__init__(0)
        self.roll = roll

    def randrange(self, *args: int, **kwargs: int) -> int:  # type: ignore[override]
        return self.roll


async def _prepare(g, items: list[Item], books: list[FashionBook], gold: int) -> None:  # type: ignore[no-untyped-def]
    snap = me(g)
    snap.character.gold = gold
    snap.character.grades = 30  # (cliente) identificação só a partir do nível 27
    snap.items.extend(items)
    snap.fashions.extend(books)
    await g.server.services.characters.save(snap.character, *items, *books)


def _books(g, *templates: int) -> list[FashionBook]:  # type: ignore[no-untyped-def]
    return [FashionBook(g.user_id, t, is_switch=True) for t in templates]


async def test_identificacao_com_sucesso(tmp_path: Path, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setattr(fashion, "RNG", Fixed(0))
    async with logged_in(tmp_path, novice=19000) as g:
        await _prepare(g, [Item(g.user_id, BEACH, is_binds=True, pos=0)], [], 1_000_000)
        g.client.send(8625)  # a moda vinculada entra no livro
        await g.until(4542)

        g.client.send(8781, pb.FashionMsg(templateId=BEACH))
        got = await g.until(4542)
        assert codes(got) == [109, 4542]  # (visto) 109 de 600000, sem 111 no sucesso

        saved = await g.server.services.characters.snapshot(g.user_id)
        assert saved is not None and saved.character.gold == 400_000
        skill = next(f.appraisal_skill for f in saved.fashions if f.template_id == BEACH)
        assert any(base <= skill < base + 25 for base in fashion.APPRAISAL_BASES)  # Strength/Intellect/Endurance/Armor
        book = pb.FashionMsg.FromString(got[-1].body)
        assert [(i.tempId, i.appraisalSkill) for i in book.info] == [(BEACH, skill)]


async def test_identificacao_com_falha(tmp_path: Path, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setattr(fashion, "RNG", Fixed(99))
    async with logged_in(tmp_path, novice=19000) as g:
        await _prepare(g, [Item(g.user_id, BEACH, is_binds=True, pos=0)], [], 1_000_000)
        g.client.send(8625)
        await g.until(4542)

        g.client.send(8781, pb.FashionMsg(templateId=BEACH))
        got = await g.until(4542)
        assert codes(got) == [109, 111, 4542]  # (visto) #2524-#2526: 109, 111 "Identification Failed.", livro
        assert pb.ChatChannelMsg.FromString(got[1].body).encodeMsg == "Identification Failed."
        saved = await g.server.services.characters.snapshot(g.user_id)
        assert saved is not None and saved.character.gold == 400_000  # o ouro gasto na falha não volta
        assert [f.appraisal_skill for f in saved.fashions if f.template_id == BEACH] == [0]


async def test_identificacao_sem_ouro_recusa(tmp_path: Path, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setattr(fashion, "RNG", Fixed(0))
    async with logged_in(tmp_path, novice=19000) as g:
        await _prepare(g, [Item(g.user_id, BEACH, is_binds=True, pos=0)], [], 100_000)
        g.client.send(8625)
        await g.until(4542)

        g.client.send(8781, pb.FashionMsg(templateId=BEACH))
        got = await g.until(4542)
        assert codes(got) == [4542]  # só o livro, sem 109 nem 111
        saved = await g.server.services.characters.snapshot(g.user_id)
        assert saved is not None and saved.character.gold == 100_000
        assert [f.appraisal_skill for f in saved.fashions if f.template_id == BEACH] == [0]


async def test_composicao_valida_do_mesmo_sontype(tmp_path: Path, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setattr(fashion, "RNG", Fixed(0))  # 0 < qualquer chance: sucesso
    async with logged_in(tmp_path, novice=19000) as g:
        rows = g.server.services.templates.rows("ItemTempInfos")
        other = next(
            r for r in rows if r["MasterType"] == "1" and r["SonType"] == "110" and r["TemplateId"] != str(BEACH)
        )
        other_id = int(other["TemplateId"])
        await _prepare(
            g,
            [
                Item(g.user_id, BEACH, bag_type=BagType.STORE, pos=0),
                Item(g.user_id, other_id, bag_type=BagType.STORE, pos=1),
            ],
            _books(g, BEACH, other_id),
            10_000_000,
        )
        g.client.send(8594, pb.StoreReqMsg(operate=False))
        got = await g.until(4487)
        rsp = pb.StoreRspMsg.FromString(got[-1].body)
        assert rsp.composeResult and rsp.bagType == BagType.BAG
        product = next(r for r in rows if int(r["TemplateId"]) == rsp.composeTemplateId)
        assert product["MasterType"] == "1" and product["SonType"] == "110"

        saved = await g.server.services.characters.snapshot(g.user_id)
        assert saved is not None
        assert not [i for i in saved.items if i.bag_type == BagType.STORE]  # as duas peças foram consumidas
        assert [i.template_id for i in saved.items if i.bag_type == BagType.BAG] == [rsp.composeTemplateId]


async def test_composicao_de_sontypes_diferentes_recusa(tmp_path: Path, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setattr(fashion, "RNG", Fixed(0))
    async with logged_in(tmp_path, novice=19000) as g:
        await _prepare(
            g,
            [
                Item(g.user_id, BEACH, bag_type=BagType.STORE, pos=0),
                Item(g.user_id, WINGS, bag_type=BagType.STORE, pos=1),
            ],
            _books(g, BEACH, WINGS),
            10_000_000,
        )
        g.client.send(8594, pb.StoreReqMsg(operate=False))
        got = await g.until(4487)
        rsp = pb.StoreRspMsg.FromString(got[-1].body)
        assert not rsp.composeResult  # (cliente) "Different parts can not be synthesized!"
        saved = await g.server.services.characters.snapshot(g.user_id)
        assert saved is not None and len([i for i in saved.items if i.bag_type == BagType.STORE]) == 2
        assert saved.character.gold == 10_000_000


async def test_composicao_com_curinga(tmp_path: Path, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setattr(fashion, "RNG", Fixed(0))
    async with logged_in(tmp_path, novice=19000) as g:
        await _prepare(
            g,
            [
                Item(g.user_id, WILDCARD, bag_type=BagType.STORE, pos=0),
                Item(g.user_id, BEACH, bag_type=BagType.STORE, pos=1),
            ],
            _books(g, BEACH),
            10_000_000,
        )
        g.client.send(8594, pb.StoreReqMsg(operate=False))
        got = await g.until(4487)
        rsp = pb.StoreRspMsg.FromString(got[-1].body)
        assert rsp.composeResult  # curinga + moda, sem o SonType 109 (asas) não pede 5 curingas
        saved = await g.server.services.characters.snapshot(g.user_id)
        assert saved is not None and not [i for i in saved.items if i.bag_type == BagType.STORE]
