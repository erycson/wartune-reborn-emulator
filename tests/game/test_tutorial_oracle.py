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
from pathlib import Path

import pytest

from tests.game.harness import logged_in
from tests.test_end_to_end import DATA
from wartune_server.game import battle as battle_mod
from wartune_server.protocol.messages import wartune_pb2 as pb
from wartune_server.protocol.registry import Direction, MessageRegistry

CAPTURE = Path("D:/wartune/server-relay/replay_packets.json")
FIRST, LAST = 116, 580  # 5127 (entra no tutorial) .. respostas do 8281 (prédios do castelo)
TIMING = {153, 75, 156, 69}  # golpes e confirmações saem no ritmo da batalha
NOT_IMPLEMENTED = {
    4476,  # SumActiveDataMsg (atividades)
    4484,  # AppellsMsg (títulos)
    4434,  # contrato do rei
    4542,  # livro de moda (8625)
    4122,  # patrulha dos monstros no mapa 10002
    4152,  # LeedUpdatedRspMsg (guia de metas)
}
# respostas do oficial que não reproduzimos de propósito: "Emek oranınız 10'a ulaştı" (taxa de
# trabalho, sistema que não existe aqui) e o 150 repetido, idêntico, na saída do mapa 10002
KNOWN_GAPS = Counter({83: 1, 150: 1})
SKIPPED_CLIENT = {8625, 15013, 20010, 8516, 5008}  # sem resposta relevante para o tutorial

pytestmark = [
    pytest.mark.skipif(not CAPTURE.exists(), reason="precisa da captura do relay"),
    pytest.mark.skipif(not (DATA / "xml/tempinfos.xml").exists(), reason="precisa de data/overlay"),
]


@pytest.fixture(autouse=True)
def fast_battles(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(battle_mod, "FRAME_SECONDS", 0)


def _filtered(codes: list[int]) -> list[int]:
    return [c for c in codes if c not in TIMING | NOT_IMPLEMENTED]


def _capture() -> list[dict]:  # type: ignore[type-arg]
    return [p for p in json.loads(CAPTURE.read_text(encoding="utf-8")) if FIRST <= p["index"] <= LAST]


async def test_tutorial_matches_capture(tmp_path: Path) -> None:
    registry = MessageRegistry.load_default()
    packets = _capture()
    official_army = 58073072
    expected = _filtered([p["code"] for p in packets if not p["isClient"]])

    async with logged_in(tmp_path, novice=11000) as g:
        g.client.send(5012, pb.QuestAddedMsg(questId=[10]))  # #97 na captura, antes do 5127
        await g.until(112)
        got: list[int] = []
        battle_id, hero_id = "", 0
        for p in packets:
            if not p["isClient"] or p["code"] in SKIPPED_CLIENT:
                continue
            msg = registry.decode(p["code"], Direction.CLIENT_TO_SERVER, bytes.fromhex(p["bodyHex"]))
            if msg is not None:
                for field in ("armyId", "battleId", "endObjId"):
                    if field in msg.DESCRIPTOR.fields_by_name and msg.HasField(field):
                        value = getattr(msg, field)
                        if field == "battleId":
                            setattr(msg, field, battle_id)
                        elif field == "endObjId" and value:
                            setattr(msg, field, hero_id)
                        elif value == official_army:
                            setattr(msg, field, g.user_id)
            g.client.send(p["code"], msg)
            for reply in await g.idle(0.1):
                got.append(reply.code)
                if reply.code == 157:
                    battle_id = pb.BattlePrepareMsg.FromString(reply.body).battleId
                elif reply.code == 150 and not hero_id:
                    hero_id = pb.ArmyArmyMsg.FromString(reply.body).simpleHeroInfo.heroId

    ours, official = Counter(_filtered(got)), Counter(expected)
    missing, extra = official - ours, ours - official
    assert (missing, extra) == (KNOWN_GAPS, Counter()), f"faltando {missing}, sobrando {extra}"
