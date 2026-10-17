"""Oráculo: os pacotes do cliente da captura oficial (tutorial inteiro) contra o nosso servidor.

Reenvia cada pacote do cliente (com os ids trocados pelos nossos) e compara quantas respostas de
cada opcode saem, contra o servidor oficial. A ordem fina (que oscila com o ritmo da batalha e do
cliente) fica com ``test_tutorial.py``; aqui o que importa é não faltar nem sobrar resposta.
Ignora os golpes da batalha e o que ainda não existe aqui (``NOT_IMPLEMENTED``). Precisa da
captura do relay.
"""

from __future__ import annotations

import json
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path

import pytest

from tests.game.harness import Game, logged_in
from tests.test_end_to_end import DATA
from wartune_server.game import battle as battle_mod
from wartune_server.protocol.messages import wartune_pb2 as pb
from wartune_server.protocol.registry import Direction, MessageRegistry
from wartune_server.services.clock import FakeClock

CAPTURE = Path("D:/wartune/server-relay/replay_packets.json")
FIRST, LAST = 116, 813  # 5127 (entra no tutorial) .. 4129 com as duas minas ocupadas (missão 60)
TIMING = {153, 75, 156, 69}  # golpes e confirmações saem no ritmo da batalha
NOT_IMPLEMENTED = {
    4476,  # SumActiveDataMsg (atividades)
    4484,  # AppellsMsg (títulos)
    4434,  # contrato do rei
    4542,  # livro de moda (8625)
    4122,  # patrulha dos monstros no mapa 10002
    4152,  # LeedUpdatedRspMsg (guia de metas)
}
# diferenças conhecidas, todas fora do tutorial em si (docs/pendencias.md):
# - "Emek oranınız ..." (83, taxa de trabalho: sistema que não existe aqui), uma no tutorial e uma por mina;
# - presente da atividade de soma no 8586 (#678: 3, 109, 115, 111, 83): pacote não implementado;
# - subida de nível na missão 51 (#625-#628: 139, 100, 4640): aqui só o 150, e o nível sobe uma
#   missão depois (EXP das lutas diferente), daí o 150 a mais; a missão 50 avança no 5017 20000 (112 a mais);
# - 11 (salas de outros jogadores) e 4248 (estado do chefe mundial) ao aceitar missão;
# - 140 ×2 da chegada do exército (#766): o timer é de 2,4 s reais e o próximo pacote chega antes.
KNOWN_GAPS = Counter({83: 3, 140: 2, 11: 2, 109: 1, 3: 1, 100: 1, 115: 1, 111: 1, 4248: 1, 139: 1, 4640: 1})
KNOWN_EXTRA = Counter({112: 2, 150: 1})
BATTLE_CLIENT = {10007, 10008, 10010, 10020, 10022, 20008, 5015, 5035}  # podem vir no meio da luta
SKIPPED_CLIENT = {8625, 15013, 20010, 8516, 5008}  # sem resposta relevante para o tutorial

pytestmark = [
    pytest.mark.skipif(not CAPTURE.exists(), reason="precisa da captura do relay"),
    pytest.mark.skipif(not (DATA / "xml/tempinfos.xml").exists(), reason="precisa de data/overlay"),
]


@pytest.fixture(autouse=True)
def fast_battles(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(battle_mod, "FRAME_SECONDS", 0.001)


def _filtered(codes: list[int]) -> list[int]:
    return [c for c in codes if c not in TIMING | NOT_IMPLEMENTED]


def _capture() -> list[dict]:  # type: ignore[type-arg]
    return [p for p in json.loads(CAPTURE.read_text(encoding="utf-8")) if FIRST <= p["index"] <= LAST]


def _building_id(g: Game, son_type: int) -> int:
    session = g.server.online.get(g.user_id)
    assert session is not None and session.snapshot is not None
    templates = session.ctx.templates
    return next(
        b.id or 0
        for b in session.snapshot.buildings
        if int((templates.get("BuildingTempInfos", b.template_id) or {}).get("SonType", 0)) == son_type
    )


async def test_tutorial_matches_capture(tmp_path: Path) -> None:
    registry = MessageRegistry.load_default()
    packets = _capture()
    official_army = 58073072
    expected = _filtered([p["code"] for p in packets if not p["isClient"]])
    # prédio oficial (4130) -> SonType, para trocar o buildingId do 8203 pelo nosso do mesmo tipo
    official_son = {
        b.buildingId: b.sonType
        for p in packets
        if not p["isClient"] and p["code"] == 4130
        for b in pb.BuildingInfoListMsg.FromString(bytes.fromhex(p["bodyHex"])).building
    }

    # o relógio anda como na captura: obras (10 s) e produção terminam no mesmo ponto que no oficial
    clock = FakeClock(datetime.fromtimestamp(packets[0]["time"], UTC))
    async with logged_in(tmp_path, novice=11000, clock=clock) as g:
        g.client.send(5012, pb.QuestAddedMsg(questId=[10]))  # #97 na captura, antes do 5127
        await g.until(112)
        got: list[int] = []
        battle_id, hero_id, hero_living, fighting = "", 0, 0, False

        def collect(replies: list) -> None:  # type: ignore[type-arg]
            nonlocal battle_id, hero_id, hero_living, fighting
            for reply in replies:
                got.append(reply.code)
                if reply.code == 157:
                    prepare = pb.BattlePrepareMsg.FromString(reply.body)
                    battle_id, fighting = prepare.battleId, True
                    hero_living = next(h.livingId for h in prepare.heros if h.userId == g.user_id)
                elif reply.code == 4103:
                    fighting = False
                elif reply.code == 150 and not hero_id:
                    hero_id = pb.ArmyArmyMsg.FromString(reply.body).simpleHeroInfo.heroId

        for p in packets:
            if not p["isClient"] or p["code"] in SKIPPED_CLIENT:
                continue
            if fighting and p["code"] not in BATTLE_CLIENT:
                # o nosso herói pode precisar de mais ordens que o da captura: termina a luta antes
                g.client.send(10022, pb.BattleReqMsg(battleId=battle_id))
                me = pb.HeroMsg(userId=g.user_id, livingId=hero_living)
                collect(await g.fight(pb.BattlePrepareMsg(battleId=battle_id, heros=[me])))
            msg = registry.decode(p["code"], Direction.CLIENT_TO_SERVER, bytes.fromhex(p["bodyHex"]))
            if msg is not None:
                if "buildingId" in msg.DESCRIPTOR.fields_by_name and msg.buildingId in official_son:
                    msg.buildingId = _building_id(g, official_son[msg.buildingId])
                for field in ("armyId", "battleId", "endObjId"):
                    if field in msg.DESCRIPTOR.fields_by_name and msg.HasField(field):
                        value = getattr(msg, field)
                        if field == "battleId":
                            setattr(msg, field, battle_id)
                        elif field == "endObjId" and value:
                            setattr(msg, field, hero_id)
                        elif value == official_army:
                            setattr(msg, field, g.user_id)
            clock.advance(max(0.0, p["time"] - clock.now().timestamp()))
            g.client.send(p["code"], msg)
            collect(await g.idle(0.1))

    ours, official = Counter(_filtered(got)), Counter(expected)
    missing, extra = official - ours, ours - official
    assert (missing, extra) == (KNOWN_GAPS, KNOWN_EXTRA), f"faltando {missing}, sobrando {extra}"
