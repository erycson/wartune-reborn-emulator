"""Pets (composição 8621 op 13 pela ``PetComponseInfos``) e sorteio do refino da forja (8336)."""

from __future__ import annotations

from pathlib import Path

import pytest

from tests.game.harness import logged_in
from tests.test_end_to_end import TEMPLATES
from wartune_server.domain.models import Item, Pet
from wartune_server.game import bag
from wartune_server.game.handlers import pets
from wartune_server.protocol.messages import wartune_pb2 as pb
from wartune_server.templates.repository import GameTemplates

pytestmark = pytest.mark.skipif(not TEMPLATES.exists(), reason="precisa de data/templates")

PAN_T1_S4 = 104104  # receita 4: 10 de 2125054 + 1000 de 2125057 + 5 milhões de ouro
PAN_T2_S4 = 104204  # resultado da receita 4 (tier 2, mesma estrela)
PAN_T1_S1 = 104101  # estrela 1: nenhuma receita de um pet só
ORE, STAR_DUST = 2125054, 2125057  # Star Tear - Wind, Star Sand
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
        snap.character.grades = pets.COMPOSE_GRADE - 1  # PetComposeView: o herói precisa do nível 60
        await g.server.services.characters.save(snap.character, pet, ore, dust)

        g.client.send(8621, pb.PlayerPetOpMsg(petId=pet.id, opType=13))
        assert await g.idle() == []
        snap.character.grades = pets.COMPOSE_GRADE
        g.client.send(8621, pb.PlayerPetOpMsg(petId=pet.id, opType=13))
        got = await g.until(109)
        assert codes(got) == [4540, 115, 109]
        info = pb.PlayerPetMsg.FromString(got[0].body).petInfo[0]
        assert (info.templateId, info.curGrade, info.totalGp) == (PAN_T2_S4, 12, 500)  # nível e EXP ficam
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
        snap.character.gold, snap.character.grades = GOLD, pets.COMPOSE_GRADE
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
        snap.character.gold, snap.character.grades = GOLD, pets.COMPOSE_GRADE
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
    templates = GameTemplates.parse(TEMPLATES.read_bytes())
    bag._random_pool.clear()
    pool = set(bag.random_skill_pool(templates))
    # atributos vistos nas capturas (só turco: login, ciftlik, atolye_item_basma_ve_mozaik): todos com Grades 1-10
    assert {70941, 71157, 72141, 70218, 71033, 70302} <= pool
    # +0 com valor 500000 (Power+0), MATK de Grades 0 e Conat (tropas) nunca saem
    assert not pool & {70100, 70800, 71200}
    bag._random_pool.clear()


async def test_equipamento_do_mascote_na_bolsa_26_soma_nos_bag(tmp_path: Path) -> None:
    """5005 com ``endBagType`` 26, ``endObjId`` 0 e ``objectId`` = mascote (PetBagCellClickMediator); espaço pelo
    SonType (113 -> 0/1); vincula; o 4540 traz o ``bagLiving`` (Live + encantamento ``int(base × 1,08^g − base)``)."""
    guard = 1130301  # Empress' Guard: MasterType 5, SonType 113, Live 650
    async with logged_in(tmp_path, novice=19000) as g:
        snap = snap_of(g)
        pet = Pet(g.user_id, PAN_T1_S1, "Pan", pos=0, is_bind=False)
        item = Item(g.user_id, guard, pos=0, is_binds=False, mould_grade=2)
        snap.pets.append(pet)
        snap.items.append(item)
        await g.server.services.characters.save(pet, item)
        await g.idle()

        def move(begin: tuple[int, int, int], end: tuple[int, int, int], pet_id: int) -> None:
            req = pb.ItemReqMsg(beginBagType=begin[0], beginObjId=begin[1], beginPos=begin[2], count=1)
            req.endBagType, req.endObjId, req.endPos, req.objectId = *end, pet_id
            g.client.send(5005, req)

        move((1, 0, 0), (26, 0, 2), pet.id or 0)  # 2 é do SonType 114
        move((1, 0, 0), (26, 0, 0), 999)  # mascote de outro
        assert await g.idle() == []
        move((1, 0, 0), (26, 0, 1), pet.id or 0)
        got = await g.idle()
        assert codes(got)[-1] == 4540
        info = pb.PlayerPetMsg.FromString(got[-1].body).petInfo[0]
        assert (info.bagLiving, info.isBind) == (650 + int(650 * 1.08**2 - 650), True)
        assert (item.bag_type, item.object_id, item.pos, item.is_binds) == (26, pet.id, 1, True)
        assert pets.pet_info(pet, g.server.services.templates).maxHp + info.bagLiving == info.maxHp

        move((26, pet.id or 0, 1), (1, 0, 3), pet.id or 0)  # tirar (PetEquipBagCellClickMediator)
        got = await g.idle()
        assert pb.PlayerPetMsg.FromString(got[-1].body).petInfo[0].bagLiving == 0
        assert (item.bag_type, item.object_id, item.pos) == (1, 0, 3)


async def test_encantar_equipamento_de_mascote_8644(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """PetEquipStrengView: 3 + 3 materiais (o que falta em Balens pelo Point 80 da loja); sucesso sobe o
    ``mouldGrade``, falha soma 5 de bênção; o 4558 traz ``strengResult``."""
    from wartune_server.game.handlers import forge

    async with logged_in(tmp_path, novice=19000) as g:
        snap = snap_of(g)
        item = Item(g.user_id, 1130301, bag_type=0, pos=0, is_binds=False)
        light, glint = Item(g.user_id, 3250101, pos=0, count=3), Item(g.user_id, 3260101, pos=1, count=3)
        snap.items.extend([item, light, glint])
        snap.character.point = 1000
        await g.server.services.characters.save(snap.character, item, light, glint)
        await g.idle()

        monkeypatch.setattr(forge.random, "randint", lambda a, b: 50)  # taxa 50 no nível 0: sucesso
        g.client.send(8644, pb.PayTypeMsg(payType=0))
        got = await g.until(4558)
        assert pb.StoreRspMsg.FromString(got[-1].body).strengResult
        assert (item.mould_grade, item.bless_value, item.is_binds) == (1, 0, True)
        assert (light in snap.items, glint in snap.items, snap.character.point) == (False, False, 1000)

        monkeypatch.setattr(forge.random, "randint", lambda a, b: 41)  # taxa 40 no nível 1: falha
        g.client.send(8644, pb.PayTypeMsg(payType=1))  # sem material: 6 × 80 Balens
        got = await g.until(4558)
        assert not pb.StoreRspMsg.FromString(got[-1].body).strengResult
        assert (item.mould_grade, item.bless_value, snap.character.point) == (1, 5, 1000 - 6 * 80)
        assert forge.mould_rate(item) == 45


async def _two_pets(g, grades: int, **second):  # type: ignore[no-untyped-def]
    snap = snap_of(g)
    snap.character.grades = grades
    main = Pet(g.user_id, PAN_T1_S1, "Main", pos=0, is_bind=False)
    other = Pet(g.user_id, PAN_T1_S1, "Second", pos=1, **second)
    snap.pets.extend([main, other])
    await g.server.services.characters.save(snap.character, main, other)
    await g.idle()
    return snap, main, other


async def test_devorar_da_metade_da_exp_total_e_para_no_nivel_do_heroi(tmp_path: Path) -> None:
    """8621 op 1 (payType -1): 50% da EXP total do secundário. Tabela 25: nível 2 = 3000, 3 = 7000, 4 = 12000. Com o
    herói no 3 a EXP para em 12000 (5000 dentro do nível 3 = o Data do 4: ``isFullExp``); o secundário vai com
    ``isDel`` e o principal fica vinculado."""
    async with logged_in(tmp_path, novice=19000) as g:
        snap, main, other = await _two_pets(g, 3, gp=30000)
        g.client.send(8621, pb.PlayerPetOpMsg(petId=main.id, opType=1, value=other.id, payType=-1))
        got = await g.until(4540)
        info, gone = pb.PlayerPetMsg.FromString(got[-1].body).petInfo
        assert (info.petId, info.curGrade, info.curGp, info.totalGp, info.isBind) == (main.id, 3, 5000, 12000, True)
        assert (gone.petId, gone.isDel, other in snap.pets) == (other.id, True, False)
        assert pets.full_exp(main, g.server.services.templates, 3)

        third = Pet(g.user_id, PAN_T1_S1, "Third", pos=2, gp=1000)
        snap.pets.append(third)
        await g.server.services.characters.save(third)
        g.client.send(8621, pb.PlayerPetOpMsg(petId=main.id, opType=1, value=third.id, payType=-1))  # EXP cheia
        assert await g.idle() == []


async def test_devorar_com_100_porcento_cobra_balens_ou_a_heritage_stone(tmp_path: Path) -> None:
    async with logged_in(tmp_path, novice=19000) as g:
        snap, main, other = await _two_pets(g, 10, gp=3000)
        snap.character.point = 295  # swallow_fullgp_points
        g.client.send(8621, pb.PlayerPetOpMsg(petId=main.id, opType=1, value=other.id, payType=3))  # sem a pedra
        assert await g.idle() == []
        g.client.send(8621, pb.PlayerPetOpMsg(petId=main.id, opType=1, value=other.id, payType=1))
        await g.idle()
        assert (main.grade, main.gp, snap.character.point) == (2, 3000, 0)

        third = Pet(g.user_id, PAN_T1_S1, "Third", pos=2, gp=4000)
        stone = Item(g.user_id, pets.HERITAGE_STONE, pos=0, count=1)
        snap.pets.append(third)
        snap.items.append(stone)
        await g.server.services.characters.save(third, stone)
        g.client.send(8621, pb.PlayerPetOpMsg(petId=main.id, opType=1, value=third.id, payType=3))
        await g.idle()
        assert (main.grade, main.gp, stone in snap.items) == (3, 7000, False)


async def test_devorar_recusa_secundario_em_batalha_ou_equipado(tmp_path: Path) -> None:
    async with logged_in(tmp_path, novice=19000) as g:
        snap, main, other = await _two_pets(g, 10, gp=3000, is_fight=True)
        g.client.send(8621, pb.PlayerPetOpMsg(petId=main.id, opType=1, value=other.id, payType=-1))
        assert await g.idle() == []
        other.is_fight = False
        armor = Item(g.user_id, 1130301, bag_type=26, object_id=other.id or 0, pos=0)
        snap.items.append(armor)
        await g.server.services.characters.save(other, armor)
        g.client.send(8621, pb.PlayerPetOpMsg(petId=main.id, opType=1, value=other.id, payType=-1))
        assert await g.idle() == []
        assert other in snap.pets


async def test_sacrificio_da_sepulcrum_pela_estrela_e_nunca_o_ultimo(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """8621 op 6: Quality 11 é a estrela 3 do cliente (16~20 Sepulcrum, ``PetShowView.getSacrificeTip``)."""
    assert (pets.sepulcrum(1), pets.sepulcrum(6), pets.sepulcrum(11), pets.sepulcrum(16)) == (
        (1, 1),
        (2, 3),
        (16, 20),
        (160, 200),
    )
    async with logged_in(tmp_path, novice=19000) as g:
        snap, main, other = await _two_pets(g, 10, quality=11)
        monkeypatch.setattr(pets.random, "randint", lambda a, b: b)
        g.client.send(8621, pb.PlayerPetOpMsg(petId=other.id, opType=6))
        got = await g.idle()
        assert codes(got) == [4540, 115, 109]
        assert pb.PlayerPetMsg.FromString(got[0].body).petInfo[0].isDel
        assert other not in snap.pets
        assert bag.count_of(snap, pets.SEPULCRUM) == 20
        g.client.send(8621, pb.PlayerPetOpMsg(petId=main.id, opType=6))  # o último
        assert await g.idle() == []


async def test_batalha_pede_nivel_e_vincula(tmp_path: Path) -> None:
    async with logged_in(tmp_path, novice=19000) as g:
        snap, main, _ = await _two_pets(g, 3)
        main.grade = 4
        g.client.send(8621, pb.PlayerPetOpMsg(petId=main.id, opType=9))  # acima do herói
        assert await g.idle() == []
        main.grade = 3
        g.client.send(8621, pb.PlayerPetOpMsg(petId=main.id, opType=9))
        await g.until(4540)
        assert (main.is_fight, main.is_bind) == (True, True)


async def test_skills_do_torneio_8726_ficam_no_mascote(tmp_path: Path) -> None:
    """``chaSkillIndexs``: 3 índices em ``changeSkills`` (-1 = vazio), sem repetir; volta no 4540 do login."""
    async with logged_in(tmp_path, novice=19000) as g:
        snap, main, _ = await _two_pets(g, 10, change_skills="")
        main.change_skills = "40101,40201"
        await g.server.services.characters.save(main)
        for bad in ("0,0,-1", "2,-1,-1", "0,1"):
            g.client.send(8726, pb.PetInfoMsg(petId=main.id, chaSkillIndexs=bad))
        assert await g.idle() == []
        g.client.send(8726, pb.PetInfoMsg(petId=main.id, chaSkillIndexs="1,-1,0"))
        await g.until(4540)
        assert main.cha_skills == "1,-1,0"
        assert pets.pet_info(main, g.server.services.templates).chaSkillIndexs == "1,-1,0"
