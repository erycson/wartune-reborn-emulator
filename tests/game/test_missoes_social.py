"""Missões de amizade, guilda, mercado, bênção e árvore (tipos 20, 21, 22, 29, 30, 51, 56 e 57).

Cada teste faz a ação real do servidor e confere o 112 (progresso em ``condition_1``). Regras e
fontes em ``game/rules.py``. A árvore de amigo (missões 22, 261, 271) não entra: o servidor ainda recusa
regar a árvore de outro jogador.
"""

from datetime import UTC, datetime
from pathlib import Path

from tests.game.harness import Game, logged_in
from wartune_server.domain.models import Consortia, Item, PlayerSnapshot, Quest
from wartune_server.game.session import GameSession
from wartune_server.protocol import Packet
from wartune_server.protocol.messages import wartune_pb2 as pb

S_QUESTS = 112
HORN = 208002  # Bullhorn (Large): StartingPrice 10 (tests/game/test_mall.py)


def _session(g: Game) -> GameSession:
    s = g.server.online.get(g.user_id)
    assert s is not None and s.snapshot is not None
    return s


def _snap(g: Game) -> PlayerSnapshot:
    snap = _session(g).snapshot
    assert snap is not None
    return snap


def _guild(g: Game) -> Consortia:
    mine = _session(g).ctx.guilds.of(g.user_id)
    assert mine is not None
    return mine[0]


def _quests(got: list[Packet]) -> dict[int, tuple[int, bool]]:
    """templateId -> (condition_1, isComplete) de cada missão nos 112 recebidos."""
    out: dict[int, tuple[int, bool]] = {}
    for p in got:
        if p.code == S_QUESTS:
            for q in pb.QuestUpdatedRspMsg.FromString(p.body).quest:
                out[q.templateId] = (q.condition_1, q.isComplete)
    return out


def _open(g: Game, *template_ids: int) -> None:
    """Missões aceitas (sem passar pelo 5012, que exige a missão no template)."""
    now = datetime.now(UTC)
    _snap(g).quests.extend(Quest(g.user_id, t, now) for t in template_ids)


async def _create_guild(g: Game) -> None:
    c = _snap(g).character
    c.grades, c.gold, c.point = 20, 1_000_000, 100
    await g.idle()
    g.client.send(5130, pb.ConsortiaMsg(consortiaName="Lobos"))
    await g.idle()


async def test_pedir_amizade_avanca_a_missao_21(tmp_path: Path) -> None:
    async with logged_in(tmp_path, novice=19000) as a:
        b = await a.join("bruxa")
        for g in (a, b):
            _snap(g).character.grades = 40
        _open(a, 200)
        a.client.send(15003, pb.FriendRelationMsg(nickName=_snap(b).character.nickname, relation=1))
        got = await a.until(78) + await a.idle()  # o 112 sai depois do 78
        assert _quests(got) == {200: (1, False)}


async def test_criar_guilda_avanca_a_missao_22(tmp_path: Path) -> None:
    async with logged_in(tmp_path, novice=19000) as g:
        _open(g, 220)
        c = _snap(g).character
        c.grades, c.gold, c.point = 20, 1_000_000, 100
        await g.idle()
        g.client.send(5130, pb.ConsortiaMsg(consortiaName="Lobos"))
        assert _quests(await g.idle()) == {220: (1, False)}


async def test_entrar_na_guilda_avanca_a_missao_22_do_candidato(tmp_path: Path) -> None:
    """O líder aceita (5134) a candidatura de quem está online: o 112 vai para o candidato."""
    async with logged_in(tmp_path, novice=19000) as a:
        await _create_guild(a)
        other = await a.join("clara")
        _snap(other).character.grades = 20
        _open(other, 220)
        await other.idle()
        other.client.send(5135, pb.ConsortiaMsg(consortiaId=_guild(a).id))
        [apply] = [p for p in await other.idle() if p.code == 35]
        a.client.send(5134, pb.ConsortiaMsg(applyId=pb.ConsortiaMsg.FromString(apply.body).applyId, result=True))
        await a.idle()
        assert _quests(await other.idle()) == {220: (1, False)}


async def test_pesquisa_da_guilda_nao_avanca_a_missao_51(tmp_path: Path) -> None:
    """Pesquisa (tipo 6+) não é Para1 da 51: a 819 fica parada."""
    async with logged_in(tmp_path, novice=19000) as g:
        await _create_guild(g)
        _open(g, 819)
        guild = _guild(g)
        guild.offer, guild.levels, guild.school_level = 1_000_000, 5, 5  # requisito da pesquisa
        g.client.send(5133, pb.ConsortiaMsg(upgradeType=6))
        assert _quests(await g.idle()) == {}
        assert _guild(g).attack_level == 1  # a pesquisa foi feita


async def test_contribuicao_avanca_a_missao_29_pelo_total(tmp_path: Path) -> None:
    async with logged_in(tmp_path, novice=19000) as g:
        await _create_guild(g)
        _open(g, 221)  # Para2 10 (cliente: consortiaTotalOffer >= Para2)
        g.client.send(5144, pb.ConsortiaUserOfferReqMsg(offerGold=4000))  # 4 de contribuição
        assert _quests(await g.idle()) == {221: (4, False)}
        g.client.send(5144, pb.ConsortiaUserOfferReqMsg(offerGold=6000))  # total 10
        assert _quests(await g.idle()) == {221: (10, False)}


async def test_bencao_da_guilda_avanca_a_missao_30(tmp_path: Path) -> None:
    async with logged_in(tmp_path, novice=19000) as g:
        await _create_guild(g)
        _open(g, 241)
        _guild(g).altar_level = 1
        _snap(g).character.consortia_offer = 100
        g.client.send(5145, pb.SimplePropertyMsg(param1=1))
        assert _quests(await g.idle()) == {241: (1, False)}


async def test_melhoria_da_guilda_avanca_a_missao_51(tmp_path: Path) -> None:
    """Missão 819 (Para1 1, guilda nível 2) avança com a melhoria; a 820 (mercado) não."""
    async with logged_in(tmp_path, novice=19000) as g:
        await _create_guild(g)
        _open(g, 819, 820)
        _guild(g).offer = 10_000
        g.client.send(5133, pb.ConsortiaMsg(upgradeType=1))
        assert _quests(await g.idle()) == {819: (2, False)}


async def test_missao_51_conclui_pelo_estado_no_5014(tmp_path: Path) -> None:
    """A guilda já está no nível 2 quando a 819 é aceita (sem melhoria): o 5014 confere o estado."""
    async with logged_in(tmp_path, novice=19000) as g:
        await _create_guild(g)
        _guild(g).levels = 2
        _open(g, 819)
        g.client.send(5014, pb.QuestFinishedReqMsg(templateId=819))
        assert _quests(await g.idle()) == {819: (2, True)}


async def test_por_item_no_leilao_avanca_a_missao_56(tmp_path: Path) -> None:
    async with logged_in(tmp_path, novice=19000) as g:
        item = Item(g.user_id, HORN, pos=5, count=1)
        _snap(g).items.append(item)
        await g.server.services.characters.save(item)
        _open(g, 825)
        g.client.send(
            8448,
            pb.SellItemReqMsg(sellType=1, itemId=item.id or 0, itemPos=5, count=1, point=10, fixPoint=0, hour=8),
        )
        got = await g.idle()
        assert pb.SellItemRspMsg.FromString(next(p.body for p in got if p.code == 4352)).result == 0
        assert _quests(got) == {825: (1, False)}


async def test_bencao_do_seminario_avanca_a_missao_57(tmp_path: Path) -> None:
    async with logged_in(tmp_path, novice=19000) as g:
        _snap(g).character.crystals = 5000
        _open(g, 857)
        g.client.send(8489)
        assert _quests(await g.idle()) == {857: (1, False)}


async def test_regar_a_propria_arvore_avanca_a_missao_20_e_nao_a_de_amigo(tmp_path: Path) -> None:
    """Missão 260 (Para1 1, árvore própria) avança; as de amigo (261, Para1 0) continuam sem progresso."""
    async with logged_in(tmp_path, novice=19000) as g:
        _open(g, 260, 261)
        g.client.send(15017, pb.BuildingReqMsg(userId=g.user_id))
        got = await g.idle()
        assert any(p.code == 147 for p in got)  # a árvore foi regada
        assert _quests(got) == {260: (1, False)}
