"""Gera as masmorras sem captura a partir das capturadas: TODO(inventado) tudo o que sai daqui.

Solo (1101-1602, migração 0099) e, com ``grupo``, as em grupo (9000-9112, migração 0101: planta da 9002 capturada,
2031 no meio com portal e 2033 no fim com o chefe; monstros 4xxx e chefes 3xxx, a família das em grupo).

Nenhuma fonte tem os nós dessas masmorras: o ``CampaignData`` só tem 40001/40002, o ``MapNodeInfos`` só o 10000 e
os ``.maps`` do mirror (AMF3 com zlib, ``PathManager.getOuterCityMapsData``) só trazem decoração; o campo
``campaign`` dos objetos vem zerado em todos os mapas de masmorra. Então, pela ordem cliente > captura > inventado:

- (cliente) mapas e etapas: ``MapInfos`` (``CampaignId``; etapa = ``Id // 10``), nível: ``Campaigns.MinLevel``.
- (cliente) casas andáveis: ``maps/<id>/<id>.titles`` do mirror; os nós vão para a casa andável mais perto.
- TODO(inventado) a planta (nós, ligações, lutas, baús, caixas, portal, chefe no fim, névoa) é a de uma capturada:
  etapa de um mapa = 1104 (1091); de vários = 1201 (1291 com portal nos do meio, 1292 com o chefe no último).
- TODO(inventado) monstros: ``PawnTempInfos`` (MasterType 101) e ``GameHeroTemp`` (HeroType 3) do nível
  (o da captura + a diferença de ``MinLevel``); a vida escala pelo ``Live`` do template novo.
- TODO(inventado) prêmios: ouro/moedas da planta escalados pelo nível; dos itens só as Luck Stones ficam (os outros
  são da história da capturada). Diálogos e avisos da planta não vão (falam da história dela).

Cada campanha gerada leva ``"inventado"`` com os mapas gerados: é a marca para trocar por captura.

    uv run python tools/gera_masmorras.py
    uv run python tools/gera_masmorras.py grupo
    uv run python tools/gera_masmorras.py torres  # 8200-8204 (migração 0102, ver TOWERS)
"""

from __future__ import annotations

import contextlib
import copy
import json
import re
import struct
import sys
import zlib
from pathlib import Path
from typing import Any

from wartune_server.templates.repository import GameTemplates

VERSIONS = Path("src/wartune_server/persistence/migrations/versions")
CAPTURED = VERSIONS / "0098_masmorras_solo.json"
OUT = VERSIONS / "0099_masmorras_geradas.json"
TEMPLATES = Path("data/templates/tempinfos.xml")
MIRROR = Path("D:/xampp/htdocs/wartune/mirror/res134-bmclas-sq.7road.net/maps")
SINGLE = ("1104", ["1091"])  # planta de etapa de um mapa
MULTI = ("1201", ["1291", "1292"])  # planta de etapa de vários mapas: meio (portal) e fim (chefe)
LUCK_STONES = range(2040101, 2040110)
SKELETON_KEY = 208005  # o baú VIP (0084/0100): a chave não é da história da planta
TILE = 20  # fixX = posX * 20 + 9 (captura: 48 -> 969)
GROUP = {
    "captured": VERSIONS / "0100_masmorras_grupo.json",
    "out": VERSIONS / "0101_masmorras_grupo_geradas.json",
    "ids": range(9000, 9113),
    "single": ("9002", ["2033"]),  # 9013 (um mapa): o fim da 9002, com o chefe e as cartas
    "multi": ("9002", ["2031", "2033"]),  # o 2032 é cheio de nós da história (catacumbas, invocador)
    "family": True,  # monstros 4xxx e chefes 3xxx só das em grupo (os solo têm outra vida)
}
SOLO = {"captured": CAPTURED, "out": OUT, "ids": range(1101, 1603), "single": SINGLE, "multi": MULTI, "family": False}
# Torres (Tower of Kings 8200/8202-8204 e The Spire 8201, migração 0102): em grupo (Capacity 4, sala), um mapa cada
# (MapFileId 8201). TODO(inventado) a planta é o fim da 9002 (chefe); a dificuldade sobe TOWER_STEP níveis de monstro
# por DifficultyGrade (as quatro têm MinLevel 38 e StandardDamage 10000 no cliente); a Spire leva SPIRE_WAVES ondas de
# reforço na luta do chefe (cliente: andar = ``currentWave``/``ReinforceMsg.reinforceWave``; 24 andares,
# internet). Sem carta no fim (internet: o prêmio é o baú por luta).
# battleType (cliente): 290 na King (BattleModel.isKingTower), 25 na Spire (TrailCountView.isTrail).
# EXP por luta (internet, docs/fontes-internet.md): King 100.000/300.000/900.000/2.500.000, Spire 300.000 por andar.
# TODO(inventado): a wiki dá 5 níveis na King contra sombras dos 16 melhores; aqui são as 4 lutas da planta.
TOWERS = GROUP | {"out": VERSIONS / "0102_torres.json", "ids": range(8200, 8205), "multi": GROUP["single"]}
TOWER_STEP = 10  # TODO(inventado)
SPIRE, SPIRE_WAVES = 8201, 23  # internet: 24 chefes (cliente: além do 24 é "clear instantly")
KING_GP = {1: 100_000, 2: 300_000, 3: 900_000, 4: 2_500_000}  # internet
SPIRE_GP = 300_000
KING_TYPE, SPIRE_TYPE = 290, 25


def _amf3(data: bytes) -> list[Any]:
    """Leitor AMF3 mínimo (o que os .titles usam: objetos, arrays, strings, números)."""
    pos, strs, objs, traits = 0, [], [], []

    def u29() -> int:
        nonlocal pos
        v = 0
        for n in range(4):
            c = data[pos]
            pos += 1
            if n == 3:
                return (v << 8) | c
            v = (v << 7) | (c & 0x7F)
            if not c & 0x80:
                return v
        return v

    def string() -> str:
        nonlocal pos
        r = u29()
        if not r & 1:
            return strs[r >> 1]
        s = data[pos : pos + (r >> 1)].decode("utf-8", "replace")
        pos += r >> 1
        if s:
            strs.append(s)
        return s

    def val() -> Any:
        nonlocal pos
        t = data[pos]
        pos += 1
        if t in (0, 1, 2, 3):
            return None if t < 2 else t == 3
        if t == 4:
            v = u29()
            return v - (1 << 29) if v & (1 << 28) else v
        if t == 5:
            pos += 8
            return struct.unpack(">d", data[pos - 8 : pos])[0]
        if t == 6:
            return string()
        if t == 9:
            r = u29()
            if not r & 1:
                return objs[r >> 1]
            d: dict[str, Any] = {}
            objs.append(d)
            while k := string():
                d[k] = val()
            d.update(enumerate(val() for _ in range(r >> 1)))
            return d
        if t == 10:
            r = u29()
            if not r & 1:
                return objs[r >> 1]
            if r & 2:
                dyn, _ = bool(r & 8), string()
                traits.append((dyn, [string() for _ in range(r >> 4)]))
            dyn, keys = traits[r >> 2] if not r & 2 else traits[-1]
            d = {}
            objs.append(d)
            for k in keys:
                d[k] = val()
            while dyn and (k := string()):
                d[k] = val()
            return d
        raise ValueError(f"AMF3 tipo {t} em {pos}")

    out = []
    while pos < len(data):
        out.append(val())
    return out


def walkable(map_id: int) -> list[tuple[int, int]]:
    raw = (MIRROR / str(map_id) / f"{map_id}.titles").read_bytes()
    with contextlib.suppress(zlib.error):
        raw = zlib.decompress(raw)
    return [tuple(int(v) for v in k.split("_")) for k in _amf3(raw)[0]]  # type: ignore[misc]


def _near(tiles: list[tuple[int, int]], x: int, y: int) -> tuple[int, int]:
    return min(tiles, key=lambda t: (t[0] - x) ** 2 + (t[1] - y) ** 2)


class Gen:
    def __init__(self, t: GameTemplates, family: bool = False) -> None:
        self.t, self.family = t, family
        self.rows = {int(r["CampaignId"]): r for r in t.rows("Campaigns")}
        self.level = {int(r["CampaignId"]): int(r["MinLevel"]) for r in t.rows("Campaigns")}
        self.file = {int(r["Id"]): int(r.get("MapFileId") or r["Id"]) for r in t.rows("MapInfos")}
        self.pawns = {int(r["TemplateId"]): r for r in t.rows("PawnTempInfos")}
        self.monsters = [r for r in self.pawns.values() if r["MasterType"] == "101" and int(r["Live"]) > 0]
        self.heroes = {int(r["TemplateId"]): r for r in t.rows("GameHeroTemp")}
        self.bosses = [r for r in self.heroes.values() if r["HeroType"] == "3" and int(r["Live"]) > 0]

    def pawn(self, old: int, delta: int) -> dict[str, Any]:
        o = self.pawns[old]
        want = int(o["Level"]) + delta
        pool = [r for r in self.monsters if not self.family or int(r["TemplateId"]) // 1000 == old // 1000]
        return min(pool, key=lambda r: (abs(int(r["Level"]) - want), int(r["TemplateId"])))

    def hero(self, old: int, delta: int) -> dict[str, Any]:
        o = self.heroes[old]
        want = int(o["Grades"]) + delta
        pool = [r for r in self.bosses if not self.family or int(r["TemplateId"]) // 1000 == old // 1000]
        return min(pool, key=lambda r: (abs(int(r["Grades"]) - want), r["Captain"] != o["Captain"],
                                               r["AddName"] != o["AddName"], int(r["TemplateId"])))  # fmt: skip


def _retarget(obj: Any, old: int, new: int) -> Any:
    """campDataId = mapa * 100 + n: troca o prefixo do mapa da planta pelo do mapa novo (ints e textos)."""
    lo, pat = old * 100, re.compile(rf"\b{old}(\d\d)\b")
    if isinstance(obj, dict):
        return {_retarget(k, old, new): _retarget(v, old, new) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_retarget(v, old, new) for v in obj]
    if isinstance(obj, bool):
        return obj
    if isinstance(obj, int) and lo <= obj < lo + 100:
        return new * 100 + obj - lo
    if isinstance(obj, str):
        return pat.sub(lambda m: f"{new}{m.group(1)}", obj)
    return obj


def _prize(drops: list[list[Any]], ratio: float) -> list[list[Any]]:
    out = []
    for d in drops:
        if d[0] < 0:
            out.append([d[0], round(d[1] * ratio), *d[2:]])
        elif d[0] in LUCK_STONES or d[0] == SKELETON_KEY:
            out.append(list(d))
    return out


def stage(g: Gen, plan: dict[str, Any], plan_maps: list[str], maps: list[int], cid: int) -> dict[str, Any]:
    """Uma etapa gerada: cada mapa novo clona o mapa da planta (meio ou fim) e troca nível, monstros e lugar."""
    delta = g.level[cid] - g.level[int(plan["campaign"])]
    ratio = g.level[cid] / g.level[int(plan["campaign"])]
    out: dict[str, Any] = {k: {} for k in ("maps", "battles", "confirms", "wins", "drops", "chests", "portals")}
    for i, new in enumerate(maps):
        src = plan_maps[-1] if i == len(maps) - 1 else plan_maps[0]
        old = int(src)
        tiles = walkable(g.file.get(new, new))
        entry = copy.deepcopy({k: v for k, v in plan["maps"][src].items() if k != "plot"})
        entry = _retarget(entry, old, new)
        if "start" in entry:
            entry["start"] = list(_near(tiles, *entry["start"]))
        swap_p: dict[int, dict[str, Any]] = {}
        swap_h: dict[int, dict[str, Any]] = {}
        for key, battle in plan["battles"].items():
            if battle["map"] != old:
                continue
            b = _retarget(copy.deepcopy(battle), old, new)
            b["mapTempId"] = b["map"] = new
            b["gpBonus"] = round(b.get("gpBonus", 0) * ratio)
            for s in b["soldiers"]:
                if g.pawns.get(s["tempId"], {}).get("MasterType") == "101":
                    p = swap_p.setdefault(s["tempId"], g.pawn(s["tempId"], delta))
                    k = int(p["Live"]) / int(g.pawns[s["tempId"]]["Live"])
                    s["tempId"] = int(p["TemplateId"])
                    s["initHp"] = s["hp"] = max(1, round(s["hp"] * k))
            for wave in b.get("reinforce", []):
                for s in wave:
                    if g.pawns.get(s["tempId"], {}).get("MasterType") == "101":
                        s["tempId"] = int(swap_p.setdefault(s["tempId"], g.pawn(s["tempId"], delta))["TemplateId"])
            for h in b["heroes"]:
                if h["tempId"] in g.heroes:
                    r = swap_h.setdefault(h["tempId"], g.hero(h["tempId"], delta))
                    live = int(r["Live"])
                    h.update(tempId=int(r["TemplateId"]), grade=int(r["Grades"]), nickName=r["TemplateName"],
                             res=r["ResPath"], maxHp=live, initHp=live, hp=live)  # fmt: skip
                    h["skillId"] = [int(r["DefaultSkill"])] * len(h.get("skillId") or [1])
            out["battles"][str(_retarget(int(key), old, new))] = b
        renamed = {g.pawns[o]["PawnName"]: p["PawnName"] for o, p in swap_p.items()}
        for n in entry.get("nodes", []):
            x, y = _near(tiles, n["posX"], n["posY"])
            n.update(posX=x, posY=y, curX=x, curY=y, fixX=x * TILE + 9, fixY=y * TILE + 9)
            if n.get("resetX"):
                n["resetX"], n["resetY"] = _near(tiles, n["resetX"], n["resetY"])
            if n.get("level"):
                n["level"] = max(1, n["level"] + delta)
            n["fightCapaity"] = round(n.get("fightCapaity", 0) * ratio)
            if n["sonType"] in swap_p:
                p = swap_p[n["sonType"]]
                n["sonType"], n["nodeName"] = int(p["TemplateId"]), p["PawnName"]
            elif g.family and (new_name := renamed.get(n["nodeName"])):
                n["nodeName"] = new_name  # em grupo o sonType do nó não é o pawn (2126 "Scimitar Assassin" = 4024)
            if n.get("heroTempId", -1) in swap_h:
                r = swap_h[n["heroTempId"]]
                prefix = "[Elite] " if n["nodeName"].startswith("[Elite] ") else ""
                n["heroTempId"], n["nodeName"] = int(r["TemplateId"]), prefix + r["TemplateName"]
        if "army" in entry:
            entry["army"] = {
                "hero": [int(swap_h[h]["TemplateId"]) if h in swap_h else h for h in entry["army"]["hero"]],
                "soldier": [int(swap_p[p]["TemplateId"]) if p in swap_p else p for p in entry["army"]["soldier"]],
            }
        out["maps"][str(new)] = entry
        camps = {str(n["campDataId"]) for n in plan["maps"][src].get("nodes", [])}
        for part in ("confirms", "wins", "chests"):
            for k, v in plan.get(part, {}).items():
                if k in camps:
                    v = _retarget(copy.deepcopy(v), old, new)
                    if "drops" in v:
                        v["drops"] = _prize(v["drops"], ratio)
                    out[part][str(_retarget(int(k), old, new))] = v
        for k, v in plan.get("drops", {}).items():
            if k in camps and (d := _prize(v, ratio)):
                out["drops"][str(_retarget(int(k), old, new))] = d
        for k in plan.get("portals", {}):
            if k in camps and i < len(maps) - 1:
                out["portals"][str(_retarget(int(k), old, new))] = maps[i + 1]
    return out


def nightmare(content: dict[str, Any], row: dict[str, Any], normal: dict[str, Any]) -> None:
    """Pesadelo (``DifficultyGrade`` 2): mesmo ``MinLevel`` da normal; (cliente) ``Campaigns`` traz o dano esperado
    (``StandardDamage``, 1,5x na 9104) e a EXP (``BaseGp``, 1,2x). TODO(inventado) a vida dos monstros escala pelo
    ``StandardDamage`` e o gpBonus pelo ``BaseGp`` da normal para o pesadelo."""
    hp = int(row["StandardDamage"]) / int(normal["StandardDamage"])
    gp = int(row["BaseGp"]) / int(normal["BaseGp"])
    for b in content["battles"].values():
        b["gpBonus"] = round(b.get("gpBonus", 0) * gp)
        for u in b["soldiers"] + b["heroes"] + [s for w in b.get("reinforce", []) for s in w]:
            for k in ("hp", "initHp", "maxHp"):
                if k in u:
                    u[k] = round(u[k] * hp)


def tower(content: dict[str, Any], grade: int, spire: bool) -> None:
    """Torres: battleType e EXP de cada luta, sem carta no fim. Na Spire a luta do chefe vira os andares (``trial``:
    o cliente mostra o andar), com SPIRE_WAVES ondas de reforço iguais às tropas dela; a EXP é por andar
    (``gpBonus`` x andar no servidor). TODO(inventado) a composição das ondas."""
    for entry in content["maps"].values():
        entry.pop("cards", None)
    for b in content["battles"].values():
        b["battleType"], b["gpBonus"] = (SPIRE_TYPE, SPIRE_GP) if spire else (KING_TYPE, KING_GP[grade])
        enemies = [s for s in b["soldiers"] if s["side"] != 1]
        if not spire or not enemies or not b["heroes"]:
            continue
        top = max(u["livingId"] for k in ("soldiers", "heroes") for u in b[k])
        waves = []
        for _ in range(SPIRE_WAVES):
            waves.append([dict(s, livingId=(top := top + 1)) for s in enemies])
        b["reinforce"], b["trial"] = waves, True


def main(cfg: dict[str, Any]) -> None:
    t = GameTemplates.parse(TEMPLATES.read_bytes())
    g = Gen(t, cfg["family"])
    captured = json.loads(cfg["captured"].read_text(encoding="utf-8"))
    if cfg["captured"] == GROUP["captured"]:  # a semente que a 0100 grava (com as caixas dos baús VIP)
        import importlib.util

        spec = importlib.util.spec_from_file_location("m0100", VERSIONS / "0100_masmorras_grupo.py")
        assert spec is not None and spec.loader is not None
        spec.loader.exec_module(mod := importlib.util.module_from_spec(spec))
        captured = mod.seed()
    if cfg is TOWERS:
        for cid in cfg["ids"]:
            g.level[cid] += TOWER_STEP * (int(g.rows[cid]["DifficultyGrade"]) - 1)
    result: dict[str, Any] = {}
    for row in t.rows("Campaigns"):
        cid = int(row["CampaignId"])
        if cid not in cfg["ids"]:
            continue
        ids = sorted(int(r["Id"]) for r in t.rows("MapInfos") if r.get("CampaignId") == str(cid))
        groups: dict[int, list[int]] = {}
        for m in ids:
            groups.setdefault(m // 10, []).append(m)
        content = copy.deepcopy(captured.get(str(cid))) or {"campaign": cid, "stages": []}
        done = {m for s in content["stages"] for m in s}
        made: list[int] = []
        for maps in groups.values():
            if done & set(maps):
                continue
            pid, pmaps = cfg["single"] if len(maps) == 1 else cfg["multi"]
            part = stage(g, captured[pid], pmaps, maps, cid)
            for k, v in part.items():
                content.setdefault(k, {}).update(v)
            content["stages"].append(maps)
            made += maps
        if made and row.get("DifficultyGrade") == "2" and (normal := g.rows.get(cid - 100)):
            nightmare(content, row, normal)
        if made and cfg is TOWERS:
            tower(content, int(row["DifficultyGrade"]), cid == SPIRE)
        if made:
            content["inventado"] = made
            result[str(cid)] = {k: v for k, v in content.items() if v != {}}
    cfg["out"].write_text(json.dumps(result, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"{cfg['out']}: {len(result)} campanhas, {sum(len(c['inventado']) for c in result.values())} mapas gerados")


if __name__ == "__main__":
    main({"grupo": GROUP, "torres": TOWERS}.get(sys.argv[1] if sys.argv[1:] else "", SOLO))
