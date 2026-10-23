"""Extrai da captura oficial o conteúdo de uma campanha (masmorra ou pedreira) para a semente do banco.

Mesmo padrão de ``tools/extract_tutorial.py``: tira da captura só o conteúdo (nós, névoa, batalhas, diálogos,
baús, caixas de confirmação, drops, coleta), sem nada do jogador (ids, nome, herói), e grava a campanha no
JSON que a migração 0034 põe na tabela ``campaign_contents`` (``docs/salas-campanha.md``).

    uv run python tools/extract_dungeon.py captures/tutorial_en.json --campaign 1001
    uv run python tools/extract_dungeon.py captures/tutorial_en.json --campaign 1002
    uv run python tools/extract_dungeon.py captures/tutorial_en.json --campaign 6001

Os mapas da campanha vêm do ``MapInfos`` (``CampaignId``); as etapas, dos 125 da captura: ``createdType`` 1
abre uma etapa (um 5039, uma cobrança de energia), 3 passa ao mapa seguinte da mesma etapa (portal). Os textos
são os do oficial inglês ("Received: 500 Gold", "Received: Worg Tooth x2"); os ids dos itens saem pelo nome
no ``ItemTempInfos``.
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

from google.protobuf.json_format import MessageToDict
from google.protobuf.message import Message

from wartune_server.protocol.registry import Direction, MessageRegistry
from wartune_server.templates.repository import GameTemplates

OUT = Path("src/wartune_server/persistence/migrations/versions/0034_campanhas.json")
TEMPLATES = Path("data/templates/tempinfos.xml")
QUARRY_FIGHT = "8699"  # chave da luta da pedreira (C_NEW_GUILD_FIGHT, sem nó)
GROUP_LOOT, CONFIRM = 61, 61  # masterType do baú/caixa (61 também é a Pandora e a tumba)
COLLECT = 91  # masterType da pilha de madeira (6001)
RECEIVED = "Received: "
# Drops que a captura inglesa não mostra: (visto) captura turca replay #1355/#1374, o 102102 deu Lvl. 1 Luck Stone
# x1 além do Worg Tooth; a inglesa não. (dedução) 1 em 2: chance 0,5. A mesma dúvida no 1080011 do 114104 (#2910:
# um baú de drop, 4103 baseItem + 5129), que o 113104 (mesmo lugar na outra etapa) não deu: 0,5.
EXTRA_DROPS: dict[str, list[list[float]]] = {"102102": [[2040101, 1, 0.5]]}
CHANCES = {("114104", 1080011): 0.5}


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


class Names:
    """Texto "Received: ..." do oficial -> ``[TemplateId, quantidade]`` (moedas têm TemplateId < 0)."""

    def __init__(self, templates: GameTemplates) -> None:
        self.ids = {}
        for row in templates.rows("ItemTempInfos"):
            self.ids.setdefault(row.get("TemplateName", ""), int(row["TemplateId"]))

    def parse(self, text: str) -> list[int] | None:
        if not text.startswith(RECEIVED):
            return None
        body = text[len(RECEIVED) :]
        if m := re.fullmatch(r"([\d,]+) (.+)", body):  # moeda: "500 Gold", "10,000 Daru"
            return [self.ids[m.group(2)], int(m.group(1).replace(",", ""))] if m.group(2) in self.ids else None
        if m := re.fullmatch(r"(.+) x(\d+)", body):  # item: "Worg Tooth x2"
            return [self.ids[m.group(1)], int(m.group(2))] if m.group(1) in self.ids else None
        if body in self.ids:  # item único sem "x1" na caixa do caçador (oficial_20261023-153200-1 #527)
            return [self.ids[body], 1]
        return None  # "Received: Rage Boost" (buff da Pandora): não é drop


def _decode(registry: MessageRegistry, p: dict[str, Any]) -> Any:
    direction = Direction.CLIENT_TO_SERVER if p["isClient"] else Direction.SERVER_TO_CLIENT
    return registry.decode(p["code"], direction, bytes.fromhex(p["bodyHex"])) if p["bodyHex"] else None


def extract(packets: list[dict[str, Any]], templates: GameTemplates, campaign: int) -> dict[str, Any]:
    registry = MessageRegistry.load_default()
    names = Names(templates)
    nick = _nick(packets, registry)
    maps_of = {int(r["Id"]) for r in templates.find("MapInfos", CampaignId=campaign)}
    out: dict[str, Any] = {
        "campaign": campaign, "stages": [], "maps": {}, "battles": {}, "plots": {}, "chests": {},
        "confirms": {}, "wins": {}, "drops": {}, "notices": {}, "portals": {}, "collect": {}, "switches": {},
    }  # fmt: skip
    runtime_to_camp: dict[int, int] = {}
    current = 0  # mapa da campanha em que o jogador está (0 = fora)
    arrived = 0  # nó do último 5125 (baú, diálogo, portal)
    confirmed = 0  # nó do último 5033 (caixa: buff, aviso ou moeda, até a luta começar)
    collecting = 0  # sonType da pilha de madeira do último 5032
    fighting = 0  # nó do último 128 em combate (state 4)
    battle_key = ""  # luta cujo fim ainda pode trazer drop (até o próximo pedido do cliente)
    battle: dict[str, Any] | None = None  # espera o 4103
    quarry_fight = False  # 8699 pedido: o próximo 157 é a luta da pedreira
    army_wait: set[int] = set()  # mapas com 5038 esperando o 20
    stage_open = False  # 125 tipo 1 visto, o 138 seguinte é o diálogo da entrada

    for p in packets:
        code = p["code"]
        msg = _decode(registry, p)
        if p["isClient"]:
            if code == 5125 and msg is not None:
                arrived, confirmed, collecting, battle_key = msg.paraInt1, 0, 0, ""
            elif code == 5033 and msg is not None and msg.paraBool1:
                confirmed, battle_key = msg.paraInt2, ""
            elif code == 5032 and msg is not None:
                pile = _node(out, current, msg.nodeId)  # as pilhas iguais (mesmo sonType) dão o mesmo: chave sonType
                collecting = int(pile["sonType"]) if pile.get("masterType") == COLLECT else 0
                battle_key = ""
            elif code == 8699 and current:
                quarry_fight, collecting = True, 0
            elif code == 5038 and msg is not None and msg.paraInt1 in maps_of:
                army_wait.add(msg.paraInt1)
            continue
        if code in (134, 22):  # fim da campanha ou saída da sala: o que vier depois é da cidade
            current = 0
            continue
        if msg is None:
            continue
        if code == 125:
            target = msg.room.campaignId
            if target not in maps_of:
                current = 0
                continue
            if msg.createdType == 1:
                out["stages"].append([target])
                stage_open = True
            elif target not in out["stages"][-1]:
                out["stages"][-1].append(target)
                out["portals"][str(arrived)] = target  # o 5125 no portal levou ao mapa seguinte (#2502-#2504)
            current, arrived = target, 0
            out["maps"].setdefault(str(current), {})
        elif not current:
            continue
        entry = out["maps"][str(current)]
        if code == 21 and "start" not in entry:
            entry["start"] = [msg.player[0].curPosX, msg.player[0].curPosY]
        elif code == 127 and "nodes" not in entry:
            entry["nodes"] = [_dict(n) for n in reversed(msg.node)]  # oficial manda do último ao primeiro
            runtime_to_camp.update({n.nodeId: n.campDataId for n in msg.node})
        elif code == 130 and "fog" not in entry:
            entry["fog"] = {"row": msg.row, "col": msg.col, "forArray": [b.hex() for b in msg.forArray]}
        elif code == 20 and current in army_wait:
            entry.setdefault("army", {"hero": list(msg.heroTemplated), "soldier": list(msg.soldierTemplated)})
            army_wait.discard(current)
        elif code == 138:
            plot = _dict(msg)
            for info in plot.get("info", []):
                if info.get("roleName") == nick:
                    info["roleName"] = "{nick}"  # o roteiro troca pelo apelido do jogador
            if stage_open and not arrived:
                entry.setdefault("plot", {"extend2": p["extend2"], "plot": plot})
            elif arrived:
                out["plots"].setdefault(str(arrived), {"extend2": p["extend2"], "plot": plot})
        elif code == 29:
            out["confirms"].setdefault(str(msg.nodeId), {})["confirm"] = _dict(msg)
        elif code in (111, 126):
            text = msg.encodeMsg if code == 111 else msg.body
            _text(out, names, code, text, arrived, confirmed, collecting, battle_key)
        elif code == 128 and msg.nodeState == 4:
            fighting = runtime_to_camp.get(msg.nodeId, 0)
        elif code == 157:
            key = QUARRY_FIGHT if quarry_fight else str(fighting)
            battle = out["battles"][key] = {
                "battleType": msg.battleType,
                "mapTempId": msg.mapTempId,
                "attackModel": msg.attackModel,
                "soldiers": [_dict(s) for s in msg.soldiers],
                # o herói do jogador sai do banco; aqui ficam só os heróis NPC (aliados e inimigos)
                "heroes": [_dict(h) for h in msg.heros if h.userId == 0],
                "player": next({"livingId": h.livingId, "pos": h.pos} for h in msg.heros if h.userId != 0),
                "map": current,
            }
            battle_key, quarry_fight, fighting, stage_open = key, False, 0, False
        elif code == 4103 and battle is not None:
            battle["gpBonus"] = msg.gpBonus
            battle["strategyBonus"] = msg.strategyBonus
            battle["battleScene"] = msg.battleScene
            for item in msg.baseItem:  # baú de drop no chão (#2910 -> 5129 #2924): aqui sai direto
                _drop(out, battle_key, [item.templateId, item.count])
            battle = None
        elif code == 135:
            entry["cards"] = _dict(msg)
    for camp, extra in EXTRA_DROPS.items():
        if any(camp in (str(n["campDataId"]) for n in m.get("nodes", [])) for m in out["maps"].values()):
            out["drops"].setdefault(camp, []).extend(extra)
    out["collect"] = {k: [v[0], min(v[1]), max(v[1])] for k, v in out["collect"].items()}
    return {k: v for k, v in out.items() if v}


def _node(out: dict[str, Any], current: int, camp: int) -> dict[str, Any]:
    nodes = out["maps"].get(str(current), {}).get("nodes", [])
    return next((n for n in nodes if n["campDataId"] == camp), {})


def _drop(out: dict[str, Any], key: str, drop: list[int]) -> None:
    got = out["drops"].setdefault(key, [])
    if all(d[0] != drop[0] for d in got):  # o 111 do pick-up (#2938) repete o baseItem do 4103 (#2910)
        got.append([drop[0], drop[1], CHANCES.get((key, drop[0]), 1.0)])


def _text(
    out: dict[str, Any], names: Names, code: int, text: str,
    arrived: int, confirmed: int, collecting: int, battle_key: str,
) -> None:  # fmt: skip
    """Onde cai cada 111/126: coleta, luta (drop, moeda da caixa, aviso do grupo), caixa (aviso, moeda,
    alerta do buff) ou baú. Cada um só uma vez (o 83 repete o texto: não conta)."""
    drop = names.parse(text)
    if collecting:  # (visto) #1859: cada 5032 na pilha dá Wood x2 ou x3
        if drop is not None:
            out["collect"].setdefault(str(collecting), [drop[0], []])[1].append(drop[1])
        return
    if battle_key:
        if drop is not None and (drop[0] < 0 or code == 126):  # caixa da luta: 126 (#2631 Daru; #527 item)
            out["wins"].setdefault(battle_key, {"drops": [drop], "notify": code == 126})
        elif drop is not None:
            _drop(out, battle_key, drop)
        elif code == 126:  # (visto) #1410: "Defeat all the worgs..." quando o grupo cai (extend2 25)
            out["notices"].setdefault(_map_of(out, battle_key), text)
        return
    if confirmed:
        box = out["confirms"].setdefault(str(confirmed), {})
        if drop is not None:  # (visto) #2875: a tumba do 1141 deu 5,000 Daru, sem luta
            box.setdefault("drops", [drop])
            box.setdefault("notify", code == 126)
        elif code == 126:  # (visto) #2400: "You've startled a sentinel... begin battle!", e a luta começa
            box.setdefault("notice", text)
        # o 111 da Pandora ("Received: Rage Boost") é o nome do buff sorteado do param3: o servidor monta
        return
    if arrived and drop is None and code == 126:
        # alavanca (61 com ações no param4): o 5125 abre, com aviso (oficial_20261023-153200-1 #1117-#1126)
        out["switches"].setdefault(str(arrived), {"notice": text})
        return
    if arrived and drop is not None and str(arrived) not in out["chests"]:
        # (visto) #946: baú de ouro com 126 e 83; #1295: só 111 e 83 (o 102104)
        out["chests"][str(arrived)] = {"drops": [drop], "notify": code == 126}


def _map_of(out: dict[str, Any], camp: str) -> str:
    return next(m for m, d in out["maps"].items() if any(str(n["campDataId"]) == camp for n in d.get("nodes", [])))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("capture", type=Path)
    parser.add_argument("--campaign", type=int, required=True, help="CampaignId (ex. 1001, 1002, 6001)")
    parser.add_argument("--templates", type=Path, default=TEMPLATES)
    parser.add_argument("-o", "--out", type=Path, default=OUT)
    args = parser.parse_args()
    templates = GameTemplates.parse(args.templates.read_bytes())
    data = extract(json.loads(args.capture.read_text(encoding="utf-8")), templates, args.campaign)
    seed = json.loads(args.out.read_text(encoding="utf-8")) if args.out.exists() else {}
    seed[str(args.campaign)] = data
    args.out.write_text(json.dumps(dict(sorted(seed.items())), ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"{args.out}: campanha {args.campaign}, etapas {data.get('stages')}, batalhas {sorted(data['battles'])}")


if __name__ == "__main__":
    main()
