"""Pets (composição 8621 op 13 pela ``PetComponseInfos``) e sorteio do refino da forja (8336)."""

from __future__ import annotations

from pathlib import Path

import pytest

from tests.game.harness import logged_in
from tests.test_end_to_end import DATA
from wartune_server.domain.models import Item, Pet
from wartune_server.game.handlers import forge, pets
from wartune_server.protocol.messages import wartune_pb2 as pb
from wartune_server.templates.repository import GameTemplates

pytestmark = pytest.mark.skipif(not (DATA / "xml/tempinfos.xml").exists(), reason="precisa de data/overlay")

PAN_T1_S4 = 104104  # receita 4: 10 de 2125054 + 1000 de 2125057 + 5 milhões de ouro
PAN_T2_S4 = 104204  # resultado da receita 4 (tier 2, mesma estrela)
PAN_T1_S1 = 104101  # estrela 1: nenhuma receita de um pet só
ORE, STAR_DUST = 2125054, 2125057  # Yıldız Kırığı-Rüzgar, Yıldız Tozu
GOLD = 5_000_000


def codes(packets: list) -> list[int]:  # type: ignore[type-arg]
    return [p.code for p in packets]


def snap_of(g):  # type: ignore[no-untyped-def]
    session = g.server.online.get(g.user_id)
    assert session is not None and session.snapshot is not None
    return session.snapshot


async def test_compose_pet_sobe_de_tier_e_gasta_material_e_ouro(tmp_path: Path) -> None:
    async with logged_in(tmp_path, novice=19000) as g:
        snap = snap_of(g)
        pet = Pet(g.user_id, PAN_T1_S4, "Pan", grade=12, gp=500, pos=0)
        ore, dust = Item(g.user_id, ORE, pos=0, count=10), Item(g.user_id, STAR_DUST, pos=1, count=1000)
        snap.pets.append(pet)
        snap.items.extend([ore, dust])
        snap.character.gold = GOLD + 10
        await g.server.services.characters.save(snap.character, pet, ore, dust)

        g.client.send(8621, pb.PlayerPetOpMsg(petId=pet.id, opType=13))
        got = await g.until(109)
        assert codes(got) == [4540, 115, 109]
        info = pb.PlayerPetMsg.FromString(got[0].body).petInfo[0]
        assert (info.templateId, info.curGrade, info.curGp) == (PAN_T2_S4, 12, 500)  # nível e EXP ficam
        assert (snap.character.gold, ore in snap.items, dust in snap.items) == (10, False, False)

        relogin = await g.connect()
        relogin.client.send(8224, pb.PlayerDataMsg(army=True))
        saved = pb.PlayerPetMsg.FromString((await relogin.until(4540))[-1].body)
        assert [p.templateId for p in saved.petInfo] == [PAN_T2_S4]


async def test_compose_pet_recusa_sem_material_ou_ouro(tmp_path: Path) -> None:
    async with logged_in(tmp_path, novice=19000) as g:
        snap = snap_of(g)
        pet = Pet(g.user_id, PAN_T1_S4, "Pan", grade=12, pos=0)
        ore, dust = Item(g.user_id, ORE, pos=0, count=10), Item(g.user_id, STAR_DUST, pos=1, count=999)  # falta 1
        snap.pets.append(pet)
        snap.items.extend([ore, dust])
        snap.character.gold = GOLD
        await g.server.services.characters.save(snap.character, pet, ore, dust)

        g.client.send(8621, pb.PlayerPetOpMsg(petId=pet.id, opType=13))  # falta a poeira
        assert await g.idle() == []
        dust.count = 1000
        snap.character.gold = GOLD - 1  # agora falta ouro
        g.client.send(8621, pb.PlayerPetOpMsg(petId=pet.id, opType=13))
        assert await g.idle() == []
        assert (pet.template_id, ore.count, dust.count, snap.character.gold) == (PAN_T1_S4, 10, 1000, GOLD - 1)


async def test_compose_pet_sem_receita_recusa(tmp_path: Path) -> None:
    async with logged_in(tmp_path, novice=19000) as g:
        snap = snap_of(g)
        star_one = Pet(g.user_id, PAN_T1_S1, "Pan", pos=0)
        legacy = Pet(g.user_id, 1, "Pan", pos=1)  # template antigo (NeedGrade 50): fora das receitas
        ore, dust = Item(g.user_id, ORE, pos=0, count=10), Item(g.user_id, STAR_DUST, pos=1, count=1000)
        snap.pets.extend([star_one, legacy])
        snap.items.extend([ore, dust])
        snap.character.gold = GOLD
        await g.server.services.characters.save(snap.character, star_one, legacy, ore, dust)

        for p in (star_one, legacy):
            g.client.send(8621, pb.PlayerPetOpMsg(petId=p.id, opType=13))
        assert await g.idle() == []
        assert (star_one.template_id, legacy.template_id, ore.count) == (PAN_T1_S1, 1, 10)


def test_receita_so_vale_se_o_pet_resultante_tem_template() -> None:
    recipe = {
        "Pet1Types": "104",
        "Pet2Types": "0",
        "Pet1Grade": "1",
        "Pet1Quality": "1",
        "NeedPoint": "0",
        "ResultPetTypes": "117",
        "ResultPetGrade": "2",
        "ResultQuality": "1",
    }  # tipo 117 não existe em PetTempInfos no servidor
    pet_row = {"TemplateId": "104101", "PetType": "104", "NeedGrade": "1", "Quality": "1"}
    pet = Pet(1, PAN_T1_S1, "Pan")
    assert pets.compose_recipe(GameTemplates({"PetTempInfos": [pet_row], "PetComponseInfos": [recipe]}), pet) is None
    result_row = {"TemplateId": "117201", "PetType": "117", "NeedGrade": "2", "Quality": "1"}
    with_result = GameTemplates({"PetTempInfos": [pet_row, result_row], "PetComponseInfos": [recipe]})
    found = pets.compose_recipe(with_result, pet)
    assert found is not None and found[1] == 117201


def test_refino_sorteia_so_atributos_com_grade() -> None:
    templates = GameTemplates.parse((DATA / "xml/tempinfos.xml").read_bytes())
    forge._refine_pool.clear()
    pool = set(forge._pool(templates))
    # atributos vistos nas capturas (login, ciftlik, atolye_item_basma_ve_mozaik): todos com Grades 1-10
    assert {70941, 71157, 72141, 70218, 71033, 70302} <= pool
    # +0 com valor 500000 (Güç+0), Sihirli Saldırı de Grades 0 e "Asker Miktarı" (Conat) nunca saem
    assert not pool & {70100, 70800, 71200}
    forge._refine_pool.clear()
