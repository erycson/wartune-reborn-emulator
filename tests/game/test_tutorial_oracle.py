"""Oráculo: os pacotes do cliente da captura oficial (tutorial inteiro) contra o nosso servidor.

Reenvia cada pacote do cliente (com os ids trocados pelos nossos) e compara quantas respostas de
cada opcode saem, contra o servidor oficial. A ordem fina (que oscila com o ritmo da batalha e do
cliente) fica com ``test_tutorial.py``; aqui o que importa é não faltar nem sobrar resposta.
Ignora os golpes da batalha e a patrulha sorteada (``TIMING``). Precisa da
captura inglesa (``captures/tutorial_en.json`` do checkout principal, fora do git).
"""

from __future__ import annotations

import json
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest

from tests.game.harness import Game, logged_in
from tests.test_end_to_end import TEMPLATES
from wartune_server.game import battle as battle_mod
from wartune_server.game.handlers import player as player_mod
from wartune_server.protocol.messages import wartune_pb2 as pb
from wartune_server.protocol.registry import Direction, MessageRegistry
from wartune_server.services.clock import FakeClock

CAPTURE = Path("D:/wartune/servidor/captures/tutorial_en.json")
FIRST, LAST = 98, 822  # 5127 (entra no tutorial) .. 169 depois do 4129 com as duas minas ocupadas (missão 60)
LOGIN_TAIL = range(99, 116)  # fim do login do oficial (4471 .. 4685): chega depois do 5127, não é resposta dele
# golpes e confirmações saem no ritmo da batalha; a patrulha dos monstros (4122, mapa 10002) é sorteada a cada ~6 s
# reais (handlers.campaign._patrol_loop), e o oráculo anda 0,1 s por pacote
TIMING = {153, 75, 156, 69, 4122}
# diferenças conhecidas (docs/tutorial.md, "Diferenças conhecidas"); #N = tools/dump_capture.py da inglesa.
# A última é do servidor, dentro do tutorial; as outras, ritmo ou outros jogadores:
# - 11 ×5 (salas de outros jogadores: #629, #649, #651, #757, #793): do servidor, não respostas;
#   o 4248 do #133 (estado da guerra 4008) já sai: warfield.push_states manda o 4248 quando um campo muda;
# - 140 ×2 da chegada do exército (#776-#777): o timer é de 2,4 s reais e o próximo pacote chega antes;
# O 8586 do #678 (login de 7 dias, dia 1) vai com o GUID do nosso pacote do mesmo tipo e ordem (_official_packages).
# 83: #664, chat do mundo de outro jogador (canal 10, "~" de Moondust); antes casava por acaso com o anúncio
# deduzido das 01:30 UTC, desativado na 0057
KNOWN_GAPS = Counter({11: 5, 140: 2, 83: 1})
# Sobrando: 109 e 3 nas duas minas (#742, #796). O guarda do oficial bateu no herói (#736) e ninguém morreu; o nosso
# mira o menor livingId (a tropa) e mata soldados, e a perda manda 109 e 3 (o Daru). O oficial escolhe o alvo ao
# acaso entre os vivos (tropas e herói, nas duas capturas inglesas)
KNOWN_EXTRA = Counter({109: 2, 3: 2})
BATTLE_CLIENT = {10007, 10008, 10010, 10020, 10022, 20008, 5015, 5035}  # podem vir no meio da luta
SKIPPED_CLIENT = {15013, 20010, 8516, 5008}  # sem resposta relevante para o tutorial

pytestmark = [
    pytest.mark.skipif(not CAPTURE.exists(), reason="precisa de captures/tutorial_en.json"),
    pytest.mark.skipif(not TEMPLATES.exists(), reason="precisa de data/templates"),
]


@pytest.fixture(autouse=True)
def fast_battles(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(battle_mod, "FRAME_SECONDS", 0.001)
    monkeypatch.setattr(player_mod, "ARMY_PHASE", 181.9)  # a fase do 150/4434 dos 5 min nesta captura (#365, #855)
    # o oráculo reenvia as ordens (10008) da captura, em número fixo: sem sorteio (±8%, crítico, bloqueio, alvo)
    # cada luta dura as mesmas ações do herói que no oficial
    # depois do __init__: o banco (game_settings.battle_formula, migração 0039) sobrepõe o FORMULA
    init = battle_mod.Battle.__init__

    def fixed(self: battle_mod.Battle, *args: Any, **kwargs: Any) -> None:
        init(self, *args, **kwargs)
        self.formula |= {"spread": 0.0, "crit_base": 1.0, "block_base": 1.0, "target_random": 0.0}

    monkeypatch.setattr(battle_mod.Battle, "__init__", fixed)


def _filtered(codes: list[int]) -> list[int]:
    return [c for c in codes if c not in TIMING]


def _capture() -> list[dict]:  # type: ignore[type-arg]
    return [p for p in json.loads(CAPTURE.read_text(encoding="utf-8")) if FIRST <= p["index"] <= LAST]


def _official_packages() -> dict[str, tuple[int, int]]:
    """``packageId`` das atividades do oficial (4475 do login da captura) -> ``(activeType, order)``, para trocar
    o pedido 8586 pelo pacote nosso do mesmo tipo e ordem (#678: login de 7 dias, dia 1)."""
    out = {}
    for p in json.loads(CAPTURE.read_text(encoding="utf-8")):
        if not p["isClient"] and p["code"] == 4475:
            for a in pb.SumActivesMsg.FromString(bytes.fromhex(p["bodyHex"])).actives:
                out |= {pk.packageId: (a.activeType, pk.order) for pk in a.packages}
    return out


def _castle_map(g: Game) -> int:
    session = g.server.online.get(g.user_id)
    assert session is not None and session.snapshot is not None and session.snapshot.castle is not None
    return session.snapshot.castle.map_id


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
    official_packages = _official_packages()
    official_army, official_map = 6837, 100000042  # exército e mapa da cidade externa no oficial
    expected = _filtered([p["code"] for p in packets if not p["isClient"] and p["index"] not in LOGIN_TAIL])
    # prédio oficial (4130) -> SonType, para trocar o buildingId do 8203 pelo nosso do mesmo tipo
    official_son = {
        b.buildingId: b.sonType
        for p in packets
        if not p["isClient"] and p["code"] == 4130
        for b in pb.BuildingInfoListMsg.FromString(bytes.fromhex(p["bodyHex"])).building
    }

    # o relógio anda como na captura: obras (10 s) e produção terminam no mesmo ponto que no oficial
    clock = FakeClock(datetime.fromtimestamp(packets[0]["time"], UTC))
    # fuso do oficial inglês (Pacífico): os avisos do Sylph Atoll das 18:55 (#3028-#3029) e a invasão fechada no login
    async with logged_in(tmp_path, novice=11000, clock=clock, timezone="America/Los_Angeles") as g:
        # a 10 nasce com o personagem (#81, antes do FIRST: o oficial nunca manda 5012 dela)
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
            if isinstance(msg, pb.SumActiveGetPackageMsg) and msg.packageId in official_packages:
                kind, order = official_packages[msg.packageId]
                session = g.server.online.get(g.user_id)
                assert session is not None
                ours = next(a for a in session.ctx.events.actives if a.active_type == kind)
                msg.activeId = ours.active_id
                msg.packageId = next(pk.package_id for pk in ours.packages if pk.order == order)
            if msg is not None:
                if "buildingId" in msg.DESCRIPTOR.fields_by_name and msg.buildingId in official_son:
                    msg.buildingId = _building_id(g, official_son[msg.buildingId])
                if "mapId" in msg.DESCRIPTOR.fields_by_name and msg.mapId == official_map:
                    msg.mapId = _castle_map(g)
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
