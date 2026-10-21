"""Pets m14: avanço de qualidade (8621 op 4), encantar aptidão (7) e aprender skill (5)."""

from pathlib import Path

import pytest

from tests.game.harness import logged_in
from tests.test_end_to_end import TEMPLATES
from wartune_server.domain.models import Item, Pet
from wartune_server.game.handlers import pets
from wartune_server.protocol.messages import wartune_pb2 as pb
from wartune_server.templates.repository import GameTemplates

pytestmark = pytest.mark.skipif(not TEMPLATES.exists(), reason="precisa de data/templates")

AMAZON = 101101  # Amazon Queen, PetType 101, NeedGrade 1, cor 1: PowerApt "1179,2625", GrowthRate 615
MAHRA, BURNING_STRIKE, BOOK = 208023, 704001, 3037040  # a skill 704001 (SonType 7040) e o livro dela


def snap_of(g):  # type: ignore[no-untyped-def]
    session = g.server.online.get(g.user_id)
    assert session is not None and session.snapshot is not None
    return session.snapshot


def test_cor_estrela_e_teto_seguem_o_petdata() -> None:
    """``tempToQuality``/``tempToStar`` e o ``calculateCoeLimit`` (101101 na estrela 3: 2625 + int(524 / 5) × 2)."""
    assert [pets.tier(t) for t in (1, 5, 6, 20, 21, 25, 26, 30, 31)] == [1, 1, 2, 4, 5, 5, 5, 5, 6]
    assert [pets.tier_star(t) for t in (1, 5, 6, 20, 21, 30, 31)] == [1, 5, 1, 5, 1, 10, 1]
    rows = [
        {"TemplateId": "101101", "Quality": "1", "PowerApt": "1179,2625", "GrowthRate": "615"},
        {"TemplateId": "101102", "Quality": "2", "PowerApt": "1410,3149", "GrowthRate": "769"},
    ]
    templates = GameTemplates({"PetTempInfos": rows})
    tpl = rows[0]
    assert pets.coe_limit(templates, tpl, 3, "PowerApt") == 2833
    assert pets.coe_limit(templates, tpl, 3, "GrowthRate") == 675
    assert pets.coe_limit(templates, tpl, 6, "PowerApt") == 3149  # a cor 2 não tem a seguinte aqui: o valor dela


async def test_avanco_gasta_mahra_depois_balens_e_sobe_estrela(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Tabela 27: 10 até a estrela 2, 20 até a 3, 30 até a 4. 5 unidades sem bênção = 50 de EXP: estrela 3 e 20 na
    barra; 3 Mahra e 2 × 35 Balens."""
    monkeypatch.setattr(pets.random, "randrange", lambda n: n - 1)  # sem a bênção do Sylph
    async with logged_in(tmp_path, novice=19000) as g:
        snap = snap_of(g)
        pet = Pet(g.user_id, AMAZON, "Amazon", pos=0, is_bind=False)
        mahra = Item(g.user_id, MAHRA, pos=0, count=3, is_binds=False)
        snap.pets.append(pet)
        snap.items.append(mahra)
        snap.character.point = 70
        await g.server.services.characters.save(snap.character, pet, mahra)
        await g.idle()

        g.client.send(8621, pb.PlayerPetOpMsg(petId=pet.id, opType=4, value=5, payType=1))
        got = [*await g.until(3), *await g.idle()]  # o 3 traz o 4152 dos Balens atrás
        info = pb.PlayerPetMsg.FromString(next(p for p in got if p.code == 4540).body).petInfo[0]
        assert (info.quality, info.curQualityGp) == (3, 20)
        assert (mahra in snap.items, snap.character.point, pet.growth_rate, pet.is_bind) == (False, 0, 675, False)

        g.client.send(8621, pb.PlayerPetOpMsg(petId=pet.id, opType=4, value=1, payType=1))  # sem Mahra nem Balens
        assert await g.idle() == []
        assert (pet.quality, pet.quality_gp) == (3, 20)


async def test_encantar_sobe_aptidao_ate_o_teto(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Estrela 1 da 101101: tetos 2625, 431, 2635, 1869. Só a força tem espaço; o primeiro Sepulcrum a enche e o resto
    não é gasto; com tudo no teto, recusa."""
    monkeypatch.setattr(pets.random, "randint", lambda a, b: b)
    async with logged_in(tmp_path, novice=19000) as g:
        snap = snap_of(g)
        pet = Pet(g.user_id, AMAZON, "Amazon", pos=0, power_apti=2620, intel_apti=431, physi_apti=2635, armor_apti=1869)
        stones = Item(g.user_id, pets.SEPULCRUM, pos=0, count=3)
        snap.pets.append(pet)
        snap.items.append(stones)
        await g.server.services.characters.save(pet, stones)
        await g.idle()

        g.client.send(8621, pb.PlayerPetOpMsg(petId=pet.id, opType=7, value=3))
        got = await g.until(115)
        info = pb.PlayerPetMsg.FromString(got[0].body).petInfo[0]
        assert (info.powerApti, stones.count) == (2625, 2)

        g.client.send(8621, pb.PlayerPetOpMsg(petId=pet.id, opType=7, value=1))  # "Attributes maxed"
        assert await g.idle() == []


async def test_aprender_skill_compra_o_livro_e_o_aleatorio_gratis(tmp_path: Path) -> None:
    """Sem o livro, paga o preço da loja (871: 395 GiftToken); a skill ativa entra no fastKey. O aleatório é grátis na
    primeira vez e depois custa 100 Balens."""
    async with logged_in(tmp_path, novice=19000) as g:
        snap = snap_of(g)
        c = snap.character
        pet = Pet(g.user_id, AMAZON, "Amazon", pos=0)
        snap.pets.append(pet)
        c.grades, c.gift_token, c.point = 50, 395, 0
        await g.server.services.characters.save(c, pet)
        await g.idle()

        g.client.send(8621, pb.PlayerPetOpMsg(petId=pet.id, opType=5, value=1, skillId=BURNING_STRIKE, payType=0))
        got = [*await g.until(3), *await g.idle()]  # o 3 traz o 4152 dos Balens atrás
        info = pb.PlayerPetMsg.FromString(next(p for p in got if p.code == 4540).body).petInfo[0]
        assert (info.changeSkills, info.fastKey, c.gift_token) == (str(BURNING_STRIKE), "7040,-1,-1,-1,-1,", 0)
        g.client.send(8621, pb.PlayerPetOpMsg(petId=pet.id, opType=5, value=1, skillId=BURNING_STRIKE, payType=0))
        assert await g.idle() == []  # "You already have this skill!"

        g.client.send(8621, pb.PlayerPetOpMsg(petId=pet.id, opType=5, value=2, payType=0))
        await g.until(3)
        await g.idle()
        assert len(pet.change_skills.split(",")) == 2 and snap.systems.pet_free_skill_at is not None
        g.client.send(8621, pb.PlayerPetOpMsg(petId=pet.id, opType=5, value=2, payType=0))  # 100 Balens, sem saldo
        assert await g.idle() == []


def test_skill_nova_troca_uma_do_mesmo_tipo_com_tudo_cheio(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(pets.random, "choice", lambda xs: xs[0])
    skills = [{"TemplateId": str(i), "UseWay": "1", "SonType": str(i * 10)} for i in range(1, 7)]
    templates = GameTemplates({"SkillTempInfos": skills})
    pet = Pet(1, AMAZON, "A", change_skills="1,2,3,4,5", fast_key="20,10,30,40,50,", cha_skills="0,1,-1")
    pets.place_skill(pet, templates, skills[5])
    assert (pet.change_skills, pet.fast_key, pet.cha_skills) == ("6,2,3,4,5", "20,60,30,40,50,", "0,1,-1")
