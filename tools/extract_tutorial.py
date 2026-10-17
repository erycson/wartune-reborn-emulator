"""Extrai da captura oficial o conteúdo da campanha de treino (mapas 10001 e 10002).

O tempinfos.xml não tem os nós nem as tropas inimigas do tutorial: o servidor oficial os tinha no
banco dele. Esta ferramenta tira da captura só o conteúdo (nós, posições, tropas, EXP), descartando
tudo que é do jogador (ids, nome, herói), e grava ``src/wartune_server/content/tutorial.json``.

    uv run python tools/extract_tutorial.py D:/wartune/server-relay/replay_packets.json
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from google.protobuf.json_format import MessageToDict
from google.protobuf.message import Message

from wartune_server.protocol.registry import Direction, MessageRegistry

OUT = Path("src/wartune_server/content/tutorial.json")
TUTORIAL_MAPS = (10001, 10002)
OUTER_CITY_BOSS = "8251"  # batalha "retomar o castelo" do mapa externo (C_FIGHT_SPECIAL_BOSS)


def _dict(msg: Message) -> dict[str, Any]:
    return MessageToDict(msg, preserving_proto_field_name=True, always_print_fields_with_no_presence=False)


def extract(packets: list[dict[str, Any]]) -> dict[str, Any]:
    registry = MessageRegistry.load_default()
    maps: dict[str, dict[str, Any]] = {}
    battles: dict[str, dict[str, Any]] = {}
    runtime_to_camp: dict[int, int] = {}
    current_map = 0
    fighting_node = 0
    boss_requested = False
    player_id = 0
    nickname = ""
    battle: dict[str, Any] | None = None
    plots: list[dict[str, Any]] = []

    for p in packets:
        code, body = p["code"], bytes.fromhex(p["bodyHex"])
        if p["isClient"]:
            boss_requested = boss_requested or code == 8251
            continue
        msg = registry.decode(code, Direction.SERVER_TO_CLIENT, body) if body else None
        if code == 125 and msg is not None:
            current_map = msg.room.campaignId
        elif code == 21 and msg is not None and current_map in TUTORIAL_MAPS:
            me = msg.player[0]
            player_id, nickname = me.playerId, me.nickName
            maps.setdefault(str(current_map), {})["start"] = [me.curPosX, me.curPosY]
        elif code == 127 and msg is not None and current_map in TUTORIAL_MAPS:
            entry = maps.setdefault(str(current_map), {})
            if "nodes" not in entry:
                entry["nodes"] = [_dict(n) for n in reversed(msg.node)]  # oficial manda do último ao primeiro
                runtime_to_camp.update({n.nodeId: n.campDataId for n in msg.node})
        elif code == 128 and msg is not None and msg.nodeState == 4:
            fighting_node = msg.nodeId
        elif code == 157 and msg is not None:
            if msg.mapTempId in TUTORIAL_MAPS and fighting_node in runtime_to_camp:
                key = str(runtime_to_camp[fighting_node])
            elif boss_requested:
                boss_requested = False
                key = OUTER_CITY_BOSS
            else:
                battle = None
                continue
            battle = battles[key] = {
                "battleType": msg.battleType,
                "mapTempId": msg.mapTempId,
                "attackModel": msg.attackModel,
                "soldiers": [_dict(s) for s in msg.soldiers],
                # o herói do jogador sai do banco; aqui ficam só os heróis NPC (aliados e inimigos)
                "heroes": [_dict(h) for h in msg.heros if h.userId != player_id],
                "player": next({"livingId": h.livingId, "pos": h.pos} for h in msg.heros if h.userId == player_id),
            }
            fighting_node = 0
        elif code == 138 and msg is not None and current_map in TUTORIAL_MAPS:
            # diálogos na ordem em que aparecem; o roteiro (game/campaign/script.py) aponta pelo índice
            plot = _dict(msg)
            for info in plot.get("info", []):
                if info.get("roleName") == nickname:
                    info["roleName"] = "{nick}"  # o roteiro troca pelo apelido do jogador
            plots.append({"map": current_map, "extend2": p["extend2"], "plot": plot})
        elif code == 4103 and msg is not None and battle is not None:
            battle["gpBonus"] = msg.gpBonus
            battle["battleScene"] = msg.battleScene
            battle = None
    return {"maps": maps, "battles": battles, "plots": plots}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("capture", type=Path)
    args = parser.parse_args()
    data = extract(json.loads(args.capture.read_text(encoding="utf-8")))
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(data, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"{OUT}: {len(data['maps'])} mapas, batalhas {sorted(data['battles'])}")


if __name__ == "__main__":
    main()
