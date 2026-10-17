"""Extrai da captura oficial o conteúdo da masmorra Kurt İni (campanha 1001, mapas 1011 e 1021).

Mesmo padrão de ``tools/extract_tutorial.py``: tira da captura só o conteúdo (nós, névoa, batalhas,
Pandora, fim de mapa), sem nada do jogador (ids, nome, herói), e grava
``src/wartune_server/content/dungeon_1001.json``.

    uv run python tools/extract_dungeon.py D:/wartune/server-relay/replay_packets.json

``CHESTS`` não sai de um pacote só: o ouro dos baús vem do alerta "Kazanılan:Altın 500" (111) ou do
126 de Yol Çantası (replay #1410 e #1021), e o 128 de Yol Çantası traz ``param1`` 500. Os três baús
visitados na captura estão aqui; o 101104 (Bakır Hazinesi do 1011) não foi visitado e fica de fora.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from google.protobuf.json_format import MessageToDict
from google.protobuf.message import Message

from wartune_server.protocol.registry import Direction, MessageRegistry

OUT = Path("src/wartune_server/content/dungeon_1001.json")
CAMPAIGN = 1001
MAPS = (1011, 1021)

# baús de ouro (replay #979/#1338/#1420): mapa 1021, ouro 500. O 101108 do 1011 também dá 500 (#1021).
CHESTS = {
    "101108": {"gold": 500, "notify": "Kazanılan: Altın 500"},
    "102108": {"gold": 500, "notify": "Kazanılan: Altın 500"},
    "102104": {"gold": 500, "notify": None},
}
# aviso (126) quando o grupo de lobos cai e a passagem some (replay #1593, mapa 1021)
NOTICES = {"1021": "Tüm kurtlar yok edildiğinde, geçiş gözden kaybolur"}


def _dict(msg: Message) -> dict[str, Any]:
    return MessageToDict(msg, preserving_proto_field_name=True, always_print_fields_with_no_presence=False)


def _nick(packets: list[dict[str, Any]], registry: MessageRegistry) -> str:
    """Apelido do jogador da captura: só para trocar pelo ``{nick}`` nos diálogos."""
    for p in packets:
        if not p["isClient"] and p["code"] == 21 and p["bodyHex"]:
            msg = registry.decode(21, Direction.SERVER_TO_CLIENT, bytes.fromhex(p["bodyHex"]))
            if msg is not None and msg.player:
                return str(msg.player[0].nickName)
    return ""


def extract(packets: list[dict[str, Any]]) -> dict[str, Any]:
    registry = MessageRegistry.load_default()
    nick = _nick(packets, registry)
    maps: dict[str, dict[str, Any]] = {}
    battles: dict[str, dict[str, Any]] = {}
    plots: list[dict[str, Any]] = []
    runtime_to_camp: dict[int, int] = {}
    current_map = 0
    player_id = 0
    fighting_node = 0
    battle: dict[str, Any] | None = None
    pandora_map = 0  # mapa cujo 5033 (confirma a caixa) ainda espera o buff e o alerta
    exp_wait = False  # o 137 já saiu: o próximo 83 de EXP é o do fim do mapa
    entering = False  # o 138 só conta na entrada do mapa 1011 (o 5039 que inicia a masmorra)

    for p in packets:
        code, body = p["code"], bytes.fromhex(p["bodyHex"])
        if p["isClient"]:
            # a ordem C>S x S>C do relay não vale (o S>C chega ~30 pacotes atrasado: 10007 de 4c4d40c7 no
            # #1153, o 157 dele no #1186): daqui só o 5033 marca a Pandora, e a ordem S>C entre si
            if code == 5033 and current_map in MAPS:
                pandora_map = current_map
            continue
        msg = registry.decode(code, Direction.SERVER_TO_CLIENT, body) if body else None
        if code == 125 and msg is not None and msg.room.campaignId in MAPS:
            current_map = msg.room.campaignId
            entering = True
        elif code == 21 and msg is not None and current_map in MAPS:
            me = msg.player[0]
            player_id = me.playerId
            maps.setdefault(str(current_map), {})["start"] = [me.curPosX, me.curPosY]
        elif code == 127 and msg is not None and current_map in MAPS:
            entry = maps.setdefault(str(current_map), {})
            if "nodes" not in entry:
                entry["nodes"] = [_dict(n) for n in reversed(msg.node)]  # oficial manda do último ao primeiro
                runtime_to_camp.update({n.nodeId: n.campDataId for n in msg.node})
        elif code == 130 and msg is not None and current_map in MAPS:
            entry = maps.setdefault(str(current_map), {})
            if "fog" not in entry:
                entry["fog"] = {"row": msg.row, "col": msg.col, "forArray": [b.hex() for b in msg.forArray]}
        elif code == 138 and msg is not None and entering and current_map == MAPS[0]:
            plot = _dict(msg)
            for info in plot.get("info", []):
                if info.get("roleName") == nick:
                    info["roleName"] = "{nick}"  # o roteiro troca pelo apelido do jogador
            plots.append({"map": current_map, "extend2": p["extend2"], "plot": plot})
            entering = False
        elif code == 29 and msg is not None and current_map in MAPS:
            maps.setdefault(str(current_map), {}).setdefault("pandora", {})["confirm"] = _dict(msg)
        elif code == 4165 and msg is not None and pandora_map and msg.bufferInfo:
            pandora = maps[str(pandora_map)].setdefault("pandora", {})
            pandora["buff"] = msg.bufferInfo[0].bufferTempId
        elif code == 111 and msg is not None and pandora_map and "buff" in maps[str(pandora_map)].get("pandora", {}):
            maps[str(pandora_map)]["pandora"].setdefault("alert", msg.encodeMsg)
            pandora_map = 0
        elif code == 128 and msg is not None and msg.nodeState == 4:
            fighting_node = msg.nodeId
        elif code == 157 and msg is not None and current_map in MAPS and fighting_node in runtime_to_camp:
            camp = runtime_to_camp[fighting_node]
            battle = battles[str(camp)] = {
                "battleType": msg.battleType,
                "mapTempId": msg.mapTempId,
                "attackModel": msg.attackModel,
                "soldiers": [_dict(s) for s in msg.soldiers],
                # o herói do jogador sai do banco; aqui ficam só os heróis NPC (aliados e inimigos)
                "heroes": [_dict(h) for h in msg.heros if h.userId != player_id],
                "player": next({"livingId": h.livingId, "pos": h.pos} for h in msg.heros if h.userId == player_id),
                "map": current_map,
            }
            fighting_node = 0
        elif code == 4103 and msg is not None and battle is not None:
            battle["gpBonus"] = msg.gpBonus
            battle["strategyBonus"] = msg.strategyBonus
            battle["battleScene"] = msg.battleScene
            battle = None
        elif code == 137 and msg is not None and current_map in MAPS:
            maps.setdefault(str(current_map), {})["report"] = _dict(msg)
            exp_wait = True
        elif code == 83 and msg is not None and exp_wait and msg.encodeMsg.endswith("EXP kazanıldı"):
            maps[str(current_map)]["exp_text"] = msg.encodeMsg
            exp_wait = False
        elif code == 4151 and msg is not None and current_map in MAPS:
            maps.setdefault(str(current_map), {})["rank"] = _dict(msg)
        elif code == 135 and msg is not None and current_map in MAPS:
            maps.setdefault(str(current_map), {})["cards"] = _dict(msg)
    return {
        "campaign": CAMPAIGN,
        "maps": maps,
        "battles": battles,
        "plots": plots,
        "chests": CHESTS,
        "notices": NOTICES,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("capture", type=Path)
    args = parser.parse_args()
    data = extract(json.loads(args.capture.read_text(encoding="utf-8")))
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(data, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"{OUT}: mapas {sorted(data['maps'])}, batalhas {sorted(data['battles'])}")


if __name__ == "__main__":
    main()
