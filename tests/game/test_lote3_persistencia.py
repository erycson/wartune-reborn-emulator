"""Lote 3: o que vivia só na memória e sumia ao reiniciar ou relogar. Cada teste grava pelo caminho normal e faz o
"reinício": o snapshot relido do banco (personagem) ou o ``server_states`` relido e devolvido ao contexto
(``game/server_state.py``, migração 0109)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from tests.game.harness import Game, logged_in
from tests.game.test_convites_times_bencao import _friends, _team_de_dois
from tests.game.test_forge import CRYSTAL, SWORD, put
from tests.game.test_masmorra_1001 import _undying, back_to_map
from tests.game.test_shop import me
from tests.game.test_terra_secreta import INVADER, _enter, _fight
from tests.test_end_to_end import TEMPLATES
from wartune_server.domain.models import BagType, Item
from wartune_server.game import battle as battle_mod
from wartune_server.game import fam, rules, server_state
from wartune_server.game import fishing as fs
from wartune_server.game.handlers import fishing as fishing_handler
from wartune_server.game.handlers import systems
from wartune_server.game.handlers.pet_defend import _state
from wartune_server.game.session import GameSession
from wartune_server.protocol.messages import wartune_pb2 as pb
from wartune_server.services.clock import FakeClock

pytestmark = pytest.mark.skipif(not TEMPLATES.exists(), reason="precisa de data/templates")

TEAM_INFO = 4624
CLOTH = 1120101  # Lover's Gown: roupa de moda (espaço 10), qualquer classe


def _s(g: Game) -> GameSession:
    s = g.server.online.get(g.user_id)
    assert s is not None and s.snapshot is not None
    return s


async def _reler(g: Game) -> GameSession:
    """Reinício do personagem: a sessão passa a usar o snapshot do banco."""
    s = _s(g)
    s.snapshot = await g.server.services.characters.snapshot(g.user_id)
    return s


async def _reiniciar(g: Game) -> GameSession:
    """Reinício do servidor: esvazia o estado em memória e devolve o que ``server_states`` tem no banco."""
    s = _s(g)
    ctx = s.ctx
    ctx.wilds.shields.clear()
    ctx.pet_rage.clear()
    ctx.guilds.invasions.clear()
    ctx.teams.restore([])
    loaded = await server_state.ServerStates.load(g.server.services.characters, ctx.states.server_id)
    ctx.states.rows = {}
    server_state.restore(ctx, loaded)
    return s


async def test_time_volta_depois_do_reinicio_e_quem_cai_continua(tmp_path: Path) -> None:
    async with logged_in(tmp_path, novice=19000) as a:
        b = await a.join("Bruxa")
        await _friends(a, b, "Bruxa")
        await _team_de_dois(a, b)
        a.client.send(8736, pb.SimplePropertyMsg(param1=b.user_id))  # capitão para b
        await a.idle()
        b.client.send(8740)  # b sai por ora
        await b.idle()
        await a.idle()
        s = await _reiniciar(a)
        team = s.ctx.teams.of(a.user_id)
        assert team is not None and sorted(team.members) == sorted([a.user_id, b.user_id])
        assert team.captain == b.user_id and team.away == {b.user_id}
        assert s.ctx.teams.of(b.user_id) is team
        # um time novo não reusa o id do time relido
        s.ctx.teams.invite(900, 901)
        assert s.ctx.teams.accept(901, 900).id > team.id  # type: ignore[union-attr]

        b.client.writer.close()  # a desconexão não tira b do time; a recebe o 4624 sem o detalhe de b
        got = await a.idle()
        info = pb.TeamInfoMsg.FromString(next(p.body for p in got if p.code == TEAM_INFO))
        assert list(info.memberId) == team.members and [m.playerId for m in info.memberDetail] == [a.user_id]
        assert s.ctx.teams.of(b.user_id) is team


async def test_invasor_vencido_continua_vencido_depois_do_reinicio(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(battle_mod, "FRAME_SECONDS", 0.001)
    monkeypatch.setattr(battle_mod.Battle, "_floor_hp", _undying)
    async with logged_in(tmp_path, novice=33000) as g:
        await _enter(g)
        await back_to_map(g)
        await _fight(g)
        s = await _reiniciar(g)
        ((gid, inv),) = s.ctx.guilds.invasions.items()
        assert INVADER in inv.dead and not inv.fighting  # a luta em curso não volta
        now = s.ctx.clock.now()
        assert fam.invasion(s.ctx.guilds.invasions, gid, now) == (inv, False)  # mesma onda: sem aviso repetido
        nova, aviso = fam.invasion(s.ctx.guilds.invasions, gid, inv.wave + timedelta(hours=fam.INVADER_HOURS))
        assert aviso and not nova.dead  # a onda seguinte avisa, mesmo depois de reiniciar


async def test_protecao_do_castelo_npc_volta_depois_do_reinicio(tmp_path: Path) -> None:
    async with logged_in(tmp_path, novice=19000) as g:
        s = _s(g)
        now = s.ctx.clock.now()
        s.ctx.wilds.shield((0, 7), now, 7200)
        s.ctx.wilds.shield((g.user_id, 3), now - timedelta(hours=3), 7200)  # já venceu: não é gravada
        await server_state.save(s.ctx, server_state.SHIELDS)
        s = await _reiniciar(g)
        assert 7190 < s.ctx.wilds.shield_left((0, 7), now) <= 7200
        assert (g.user_id, 3) not in s.ctx.wilds.shields


async def test_furia_da_ilha_volta_depois_do_reinicio(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from wartune_server.domain import gameday
    from wartune_server.game.handlers.space import enter_pet_island
    from wartune_server.templates.repository import GameTemplates

    real = GameTemplates.get

    def weak(self: GameTemplates, table: str, value: object, **kw: object) -> object:
        row = real(self, table, value, **kw)  # type: ignore[arg-type]
        if table == "GameHeroTemp" and value == 75112 and row is not None:
            return {**row, "Live": "1", "Attack": "1", "MagicAttack": "1"}
        return row

    monkeypatch.setattr(GameTemplates, "get", weak)
    async with logged_in(
        tmp_path, novice=19000, clock=FakeClock(datetime(2026, 1, 1, 7, 0, tzinfo=gameday.GAME_TZ))
    ) as g:
        s = _s(g)
        s.snapshot.character.grades = 50  # type: ignore[union-attr]
        await g.idle()
        enter_pet_island(s, 20001)
        await g.idle()
        camp = next(c for c, n in s.campaign.nodes.items() if n["masterType"] == 1003 and n["heroTempId"] == 75112)  # type: ignore[union-attr]
        g.client.send(5125, pb.CampaignReqMsg(paraInt1=camp))
        await g.fight(pb.BattlePrepareMsg.FromString((await g.until(157))[-1].body))
        await g.idle()
        assert _state(s, peace=False).ragePoint == 2
        s = await _reiniciar(g)
        assert _state(s, peace=False).ragePoint == 2


async def test_bancada_devolve_ao_heroi_depois_de_relogar(tmp_path: Path) -> None:
    async with logged_in(tmp_path, novice=19000) as g:
        snap = me(g)
        hero = snap.leader.id  # type: ignore[union-attr]
        cloth = Item(g.user_id, CLOTH, bag_type=BagType.HERO, object_id=hero, pos=10)
        await put(g, cloth)
        g.client.send(5005, pb.ItemReqMsg(beginBagType=4, beginObjId=hero, beginPos=10, endBagType=0, endPos=0))
        await g.idle()
        assert cloth.bag_type == BagType.STORE
        s = await _reler(g)
        g.client.send(5005, pb.ItemReqMsg(beginBagType=0, beginPos=0, endBagType=1, endPos=0))
        await g.idle()
        back = next(i for i in s.snapshot.items if i.template_id == CLOTH)  # type: ignore[union-attr]
        assert (back.bag_type, back.object_id, back.pos) == (BagType.HERO, hero, 10)


async def test_refino_sorteado_sobrevive_ao_reinicio(tmp_path: Path) -> None:
    async with logged_in(tmp_path, novice=19000) as g:
        me(g).character.point = 45
        sword = Item(g.user_id, SWORD, bag_type=0, pos=0, random_skill=70302, random_skill_2=70407, is_binds=False)
        await put(g, sword, Item(g.user_id, CRYSTAL, pos=0, count=4, is_binds=False))
        g.client.send(8336, pb.SmithFreshReqMsg(lock=[True, False, False], bindType=2, payType=1))
        skills = list(pb.SmithFreshRspMsg.FromString((await g.until(4258))[-1].body).randomSkill)
        await g.idle()
        s = await _reler(g)
        g.client.send(8464, pb.RefreshPropertyReqMsg(itemId=sword.id))
        assert list(pb.RefreshPropertyRepMsg.FromString((await g.until(4368))[-1].body).randomSkill) == skills
        g.client.send(8339)
        got = await g.until(115)
        assert pb.SmithFreshReplaceRspMsg.FromString(got[0].body).result
        relida = next(i for i in s.snapshot.items if i.id == sword.id)  # type: ignore[union-attr]
        assert relida.random_skills[:3] == skills


async def test_cardume_volta_ao_relogar(tmp_path: Path) -> None:
    now = datetime(2026, 10, 27, 15, 0, tzinfo=UTC)
    async with logged_in(tmp_path, novice=19000, clock=FakeClock(now)) as g:
        s = _s(g)
        s.snapshot.character.grades = 30  # type: ignore[union-attr]
        g.client.send(9507, pb.FreshPoolMsg(op=fishing_handler.FRESH, paras=[fishing_handler.OPEN]))
        got = await g.idle()
        antes = [(f.fishId, f.templateId, f.beginTime) for f in pb.FishInfosMsg.FromString(got[-1].body).fishs]
        s = await _reler(g)
        s.fish_pool = None  # relogar: sessão nova
        s.snapshot.character.grades = 30  # type: ignore[union-attr]
        g.client.send(9507, pb.FreshPoolMsg(op=fishing_handler.FRESH, paras=[fishing_handler.OPEN]))
        got = await g.idle()
        depois = [(f.fishId, f.templateId, f.beginTime) for f in pb.FishInfosMsg.FromString(got[-1].body).fishs]
        assert depois == antes and len(antes) == sum(len(v) for v in fs.SLOTS.values())


async def test_data_de_ativacao_da_montaria_gravada(tmp_path: Path) -> None:
    async with logged_in(tmp_path, novice=19000) as g:
        snap = me(g)
        sy = rules.systems(snap)
        when = datetime(2026, 10, 20, 12, 0, tzinfo=UTC)
        assert systems.grant_mount(sy, 1000, 0, when)
        assert not systems.grant_mount(sy, 1000, 0, when + timedelta(days=1))  # já é dela: a data fica
        await g.server.services.characters.save(sy)
        s = await _reler(g)
        assert s.snapshot is not None
        info = systems.avatar_info(s.snapshot, 1000, when + timedelta(days=2))
        assert info.activeDate == systems.fmt_time(when) != systems.fmt_time(s.snapshot.character.created_at)
