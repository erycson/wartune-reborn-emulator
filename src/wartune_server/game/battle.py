"""Batalha simulada no servidor, em tempo real (o cliente só toca o que recebe).

Relógio em quadros de 40 ms (25 fps) a partir do 156. Cada ação vai num 153 no quadro em que
acontece; mandar adiantado faz o cliente saltar o relógio. Detalhes do protocolo em
``docs/batalha.md``.

Modelo observado na captura: rodadas em que cada unidade viva age uma vez; ações do mesmo lado
começam com 12 quadros de diferença, a troca de lado e a rodada seguinte vêm ~9 quadros depois do
fim da última animação (``frameNum``); a primeira ação sai por volta do quadro 100. O herói do
jogador usa a ordem (10008) do cliente; sem ordem na vez dele, dá o golpe básico. Com ``spec["undying"]`` (as
lutas roteirizadas do tutorial e o chefe do mundo antes do ``killTurn``) o lado dele não morre; nas outras ele morre
e pode perder (visto: #1466 o herói
na masmorra 1021, #1657 e #1930 os três). Com ``spec["pvp"]`` o herói inimigo anuncia a skill no 75.
Sem herói do jogador (torneio de fadas) a luta é toda automática e, depois de ``notice`` quadros,
o 4361 avisa que o dano sobe ``damageImprove`` %.

Dano pelos atributos reais (``damage``) e buffers de ``SkillBufferTempInfos`` (``Buff``): passivas do
herói (talento, destino, skills ``UseWay`` 2) entram no 157; os das skills, no golpe.
"""

from __future__ import annotations

import asyncio
import itertools
import random
import re
import time
import uuid
from collections.abc import Awaitable, Callable, Iterable, Mapping
from dataclasses import dataclass, field
from typing import Any

import structlog
from google.protobuf.json_format import ParseDict
from google.protobuf.message import Message

from ..protocol.messages import wartune_pb2 as pb
from ..services.clock import Clock
from ..templates.repository import GameTemplates, Row
from .builders.login import fmt_time

log = structlog.get_logger(__name__)

S_PREPARE, S_START, S_ATTACK, S_OVER, S_ORDER, S_STOP, S_NOTICE = 157, 156, 153, 154, 75, 69, 4361
S_VIEW_CLOSE = 4803  # U_CROSS_BATTLE_VIEW: fecha a tela de quem assiste
S_REINFORCE, S_LOAD_RES = 72, 4149
_WAVE_IDS = itertools.count(1)  # armyId do 4149
TRIAL_TYPE = 25  # battleType da Spire (cliente TrailCountView.isTrail)
SPIRE_CLEAR = 24  # (cliente) pular para além do 24 é "clear instantly"


def skip_to(layer: int, turns: int, battle_type: int) -> int:
    """O próximo andar ao vencer o ``layer`` com o chefe em ``turns`` turnos (cliente TrailCountView.refreshTurn).
    Spire (battleType 25): até 3 turnos pula para layer+4 ("Defeat within {0} turns to skip to Stage {1}");
    nos andares 1 e múltiplos de 5 abaixo de 36: até 5 turnos pula para layer+5 (o 1 vai para o 5)."""
    if battle_type == TRIAL_TYPE:
        return layer + 4 if turns <= 3 else layer + 1
    if layer < 36 and (layer % 5 == 0 or layer == 1) and turns <= 5:
        return 5 if layer == 1 else layer + 5
    return layer + 1


def _shuffled_waves(waves: Iterable[Iterable[Mapping[str, Any]]]) -> list[list[dict[str, Any]]]:
    """As ondas em ordem sorteada; os livingIds seguem a ordem nova (a primeira onda pega os menores). (visto) nó
    103105 da 1003: 171155 #2135/#3445 com 2032 e depois 2033, 153200 #444 com 2033 e depois 2032; nos três a
    primeira onda vem com livingId 6."""
    out = [[dict(s) for s in w] for w in waves]
    ids = sorted(s["livingId"] for w in out for s in w)
    random.shuffle(out)
    it = iter(ids)
    for w in out:
        for s in w:
            s["livingId"] = next(it)
    return out


S_AWAKE = 4600  # AwakeMsg: despertar do herói com mascote
MORPH, UNMORPH = 700001, 700002  # (cliente SelfAwakenView) transformar no mascote e desfazer

FRAME_SECONDS = 0.04
FIRST_ACTION = 100
SAME_SIDE_GAP = 12  # entre inícios de ações do mesmo lado
NEXT_GAP = 9  # depois do fim da animação: troca de lado ou rodada nova
ORDER_DELAY = 25  # ordem recebida -> golpe
END_DELAY = 90  # último golpe -> 154
COUNTDOWN_MS = 60000
DAMAGE_HP, DAMAGE_SP = 6, 9  # DamageMsg.damageType: vida (bloodA), fúria (cliente BloodType)
VICTORY, DEFEAT = 3, 4  # PrepareOverLivingMsg.calcType = SkillTempInfo 3 "Victory!"/4 "Failure!"
ALL_ENEMIES, SELF = "3", "4"  # SkillTempInfo.AcceptObject
PASSIVE = "2"  # SkillTempInfo.UseWay: passiva (vira buffer no 157, não se usa)
MAGIC = "2"  # SkillTempInfo.CountWay: 2 mágico (maga 30000/30711/30811), 1 e 3 físico (visto tutorial_en)
PLAYER_SIDE = 1
AUTO = 1  # AttackModeMsg.mode / BattlePrepareMsg.attackModel
TEAM_POS = (4, 7, 2, 5, 8)  # TODO(inventado) lugares dos outros jogadores no lado 1 (o 157 da captura não decodifica)
ORDER_TIMEOUT = 112  # PvP: espera a ordem até 4,5 s (castTime do herói) antes de agir sozinho
# HeroOrderMsg.castTime do herói inimigo, fixo por skill (visto: tutorial_en #1662, #1675, #1689 e os coliseus
# turcos 171155/215937/231733). Não sai dos frames do ActionTempInfos (33 frames -> 3500, 23 -> 4500, 27 -> 4900)
# shortcut: skill fora da tabela usa 3500, o valor mais visto; acrescentar a cada captura nova
ENEMY_CAST_MS = {10711: 3500, 10000: 4500, 10811: 4900, 20721: 3500, 20811: 3900, 30721: 3900, 30821: 4500, 31211: 3900}
DEFAULT_CAST_MS = 3500

# Fórmula de dano (visto tutorial_en, 153 contra os atributos do 150 e dos templates; docs/batalha.md):
# base = max((A - D) × defence_factor, A × floor); golpe = base × Parameter1/100 + Parameter2, ±spread,
# dividido pelos AttackTimes. Crítico (extraData & 1, cliente DannyAction) ×crit_damage; bloqueio (parry)
# ×block_damage. Chances (internet) https://breezewiki.discard.no/wartune/wiki/Statistics: 1 - 0,9995^pontos.
# O banco pode trocar qualquer chave (game_settings.battle_formula).
FORMULA: dict[str, float] = {
    "defence_factor": 0.5,
    "floor": 0.1,
    "spread": 0.08,
    "crit_base": 0.9995,
    "crit_damage": 1.5,
    "block_base": 0.9995,
    "block_damage": 0.75,
    # despertar: teto (cliente HeroRoleInfo.updateAwaken), ganho por ação/golpe e gasto no modo mascote (só turco:
    # exp_kitabi +250 depois de cada 153 do herói; peri_uyanis -150 a cada ação transformado; internet: wiki Sylph,
    # +250 e 3000 para despertar)
    "awake_max": 3000,
    "awake_gain": 250,
    "awake_cost": 150,
    # TODO(inventado): resistência elemental. O cliente não calcula dano (só repassa fireResi..reduceResi no
    # HeroMsg/DebugBattleCreater); dedução: golpe de elemento × (1 - (resistência do alvo - ReduceResi do autor) /
    # resist_div), com o fator entre resist_min e resist_max (template: mascote 200 no próprio, -200 na fraqueza)
    "resist_div": 1000,
    "resist_min": 0.5,
    "resist_max": 1.5,
}
# PetTempInfos.PetType (= Property1 das gemas da guarda) -> coluna de resistência (conferido nos templates:
# Lvl. 1 Fire Resistance Crystal 101 FireResi; Pan 104 com WindResi 200)
PET_ELEMENT = {101: "FireResi", 102: "WaterResi", 103: "ElectResi", 104: "WindResi", 105: "DarkResi", 106: "LightResi"}
RESIST_KEYS = (*PET_ELEMENT.values(), "ReduceResi")
STATS = ("PhyAttack", "PhyDefence", "MagicAttack", "MagicDefence", "ForceHit", "Parry")
TEMPLATE_STATS = dict(
    zip(STATS, ("Attack", "Defence", "MagicAttack", "MagicDefence", "ForceHit", "Parry"), strict=True)
)

# SkillBufferTempInfo.AttackType (nomes dos templates; o cliente só trata 19 como "restrito")
PATK, PDEF, MATK, MDEF, HP, RAGE, RECEIVED, CRIT, CRIT_DAMAGE = 1, 2, 3, 4, 5, 6, 15, 16, 17
STUN, CONFUSED, AMNESIA, DEALT, HP_PERCENT, DEALT2, IGNORE_PDEF, IGNORE_MDEF = 19, 38, 39, 20, 33, 40, 28, 29
REVIVE = 37  # buffer 103 "Revive" (Sacred Nirvana): volta com ValuePercent % da vida (dedução)
NO_ACTION = {STUN, 101}  # 101 "昏迷，无法行动" (desmaio, não age)
STAT_BUFF = {"PhyAttack": PATK, "PhyDefence": PDEF, "MagicAttack": MATK, "MagicDefence": MDEF}
# AttackWay = cliente BufferEffectiveType/BufferActiveTime: 1 ao agir, 2 ao levar dano, 3 ao causar, 4 na hora
ON_ACTION, ON_HIT, ON_DEALT, AT_ONCE = 1, 2, 3, 4
CHANCE = re.compile(r"(\d+)% chance")


def _parse[M: Message](data: dict[str, Any], msg: M) -> M:
    # as specs levam chaves só do servidor ("attack", "stats", "defaultSkill"), fora do protobuf
    return ParseDict(data, msg, ignore_unknown_fields=True)


def damage(attack: float, defence: float, p1: int, p2: int, formula: Mapping[str, float] = FORMULA) -> float:
    """Golpe antes do sorteio: ``max((A - D) × fator, A × piso) × P1/100 + P2``. (visto) tutorial_en: maga
    MAtk 20 Lightning Bolt (102%+15) -> 25; Lancer 64 contra Def 66 -> 6; 10102 (84) skill 11 (150%) contra
    PDef 44 -> 30; cura (P1 0, P2 -50) -> -50."""
    base = max((attack - defence) * formula["defence_factor"], attack * formula["floor"])
    return base * p1 / 100 + p2


def resist_factor(unit: Unit, target: Unit, formula: Mapping[str, float] = FORMULA) -> float:
    """Multiplicador do golpe de elemento pela resistência do alvo menos o ReduceResi (Willpower) do autor."""
    if not unit.element:
        return 1.0
    base = target.resists.get(unit.element, 0)
    res = max(base - unit.resists.get("ReduceResi", 0), min(base, 0))  # a redução não passa de 0 (dedução)
    return min(formula["resist_max"], max(formula["resist_min"], 1 - res / formula["resist_div"]))


@dataclass
class Buff:
    """Um buffer de ``SkillBufferTempInfos`` sobre ``target`` (visto tutorial_en #1484-#1493 e o 30111).

    ``turn``: turnos que faltam; cai 1 a cada ação do portador e some no 0. Permanente (ValidCount -1)
    começa em -1 e segue negativo. ``see``: 0 novo, 1 em efeito, 2 removido (cliente BufferProcessType);
    ``way``: o último AttackWay executado (0 antes do primeiro)."""

    id: int
    row: Row
    source: int
    target: int
    turn: int
    see: int = 0
    way: int = 0
    damage: list[pb.DamageMsg] = field(default_factory=list)

    @property
    def kind(self) -> int:
        return int(self.row["AttackType"])

    @property
    def value(self) -> int:
        return int(self.row.get("AttackValue") or 0)

    @property
    def percent(self) -> int:
        return int(self.row.get("ValuePercent") or 0)

    @property
    def active(self) -> bool:
        return self.turn != 0

    def msg(self, battle_turns: bool = True) -> pb.BufferMsg:
        out = pb.BufferMsg(
            bufferId=self.id,
            templateId=int(self.row["Id"]),
            sourceId=self.source,
            targetId=self.target,
            curTurn=self.turn,
            execFrame=0,
            seeType=self.see,
            exeWay=self.way,
            pressedNum=1,
        )
        out.damage.extend(self.damage)
        if battle_turns:  # no 157 o oficial não manda maxTurn
            out.maxTurn = int(self.row["ValidCount"])
        return out


@dataclass
class Unit:
    living_id: int
    side: int
    hp: int
    skills: list[int]
    default_skill: int
    stats: dict[str, int]
    max_hp: int = 0
    is_player: bool = False
    sp: int = 0
    turn: int = 0
    hero: bool = False  # herói NPC (o PvP anuncia a skill dele no 75)
    reject: frozenset[int] = frozenset()  # GameHeroTemp.RejectType: tipos de buffer que não pegam
    element: str = ""  # coluna de resistência do golpe (mascote: PetType -> PET_ELEMENT); "" = sem elemento
    resists: dict[str, int] = field(default_factory=dict)  # FireResi..DarkResi e ReduceResi (guarda/template)

    @property
    def alive(self) -> bool:
        return self.hp > 0


@dataclass
class SharedHp:
    """Vida de uma unidade que vive fora da luta (chefe do mundo: todo o servidor bate no mesmo). Antes de cada
    ação a vida da unidade vem de ``hp()``; o dano nela passa por ``hit()``, que devolve o que tirou de fato."""

    living_id: int
    hp: Callable[[], int]
    hit: Callable[[int], int]
    bonus: int = 0  # dano a mais por golpe do lado do jogador (moral do chefe)
    dealt: int = 0  # o que esta luta tirou


@dataclass(frozen=True, slots=True)
class PlayerHero:
    """O que a batalha precisa do herói do jogador (montado pela sessão).

    ``stats``: ``HeroStats.total``. ``passives``: skills passivas de talento e destino (viram buffers no 157,
    como as ``UseWay`` 2 da lista de skills). ``army``: pilhas da tropa (``outer_city.army_soldiers``) que
    trocam as do jogador na spec; ``None`` não mexe. ``once``: skills de runa, uma vez por batalha. ``pet``: o
    mascote em batalha (entrada do ``pets``, livingId posto pela luta; ``follow``: as skills com que ele age,
    ``change``: as do modo mascote). ``on_awake``: grava o despertar novo (ele passa de uma luta para outra)."""

    msg: pb.HeroMsg
    stats: Mapping[str, int]
    default_skill: int
    passives: tuple[int, ...] = ()
    army: tuple[dict[str, Any], ...] | None = None
    once: frozenset[int] = frozenset()
    pet: Mapping[str, Any] | None = None
    on_awake: Callable[[int], None] | None = None

    @property
    def attack(self) -> int:
        return max(int(self.stats.get("PhyAttack", 0)), int(self.stats.get("MagicAttack", 0)))


def is_player_troop(templates: GameTemplates, soldier: Mapping[str, Any]) -> bool:
    """Pilha da tropa do jogador na spec: lado 1 e PawnTempInfos.MasterType 1 (os monstros são 101)."""
    row = templates.get("PawnTempInfos", soldier["tempId"]) or {}
    return soldier["side"] == PLAYER_SIDE and row.get("MasterType") == "1"


class Battle:
    def __init__(
        self,
        spec: dict[str, Any],
        player: PlayerHero | None,
        templates: GameTemplates,
        clock: Clock,
        send: Callable[[int, Message], None],
        on_end: Callable[[Battle, bool], Awaitable[None]],
        shared: SharedHp | None = None,
        settings: Mapping[str, Any] | None = None,
        rng: random.Random | None = None,
    ) -> None:
        self.id = str(uuid.uuid4())
        self.shared = shared
        self._kill_turn = int(spec.get("killTurn", 0))  # a ação do inimigo que mata o lado do jogador inteiro
        self.templates, self.clock = templates, clock
        self.formula = FORMULA | dict((settings or {}).get("battle_formula") or {})
        self.rng = rng or random.Random()
        self._out, self._on_end = send, on_end
        self.forfeit: Callable[[], Awaitable[None]] | None = None  # quem conduz caiu: fecha a luta (arena em grupo)
        self.joined: list[Any] = []  # reforços de jogador (``join``, 8255/8745): sessões que recebem o resto da luta
        self.viewers: list[Any] = []  # espectadores (8985, ``watch``): recebem tudo e o 4803 no fim
        self._t0: float | None = None  # time.monotonic() do 156
        self._paused_at: float | None = None
        self._paused_total = 0.0
        self.loaded = False
        self.auto = spec["attackModel"] == AUTO
        self._order: tuple[int, int] | None = None  # (skillId, quadro em que chegou)
        self._order_frame: int | None = None  # quadro da ordem usada no golpe atual do herói
        self._task: asyncio.Task[None] | None = None
        self.pvp = bool(spec.get("pvp"))
        self._notice: int | None = spec.get("notice")  # quadro do 4361 (só pets)
        self._improve = 0  # % de dano a mais depois do 4361
        self._skip = False  # finish(): resolve o resto sem esperar nem mandar 153
        self._player_msg = player.msg if player is not None else None
        self._once = set(player.once) if player is not None else set()
        self.spec = self._with_army(spec, player)
        self.pet_id = 0  # livingId do mascote do jogador (0: sem mascote, sem despertar)
        if player is not None and player.pet is not None:
            self.spec = self._with_pet(player, player.pet)
        self.buffs: list[Buff] = []
        self._buff_seq = 0  # bufferId: 1, 2... por batalha (visto #1466 e #1484)
        self.units = self._units(player)
        self._waves = _shuffled_waves(spec.get("reinforce", []))  # ondas de reforço que faltam
        self.layer = 1 if spec.get("trial") else 0  # andar da Spire (cliente ``BattleModel.trialLayer``)
        if self.layer:  # a Spire não sorteia: os andares vão em ordem
            self._waves = [[dict(s) for s in w] for w in spec.get("reinforce", [])]
        self._wave = [u for u in self.units if u.side != PLAYER_SIDE]  # quem conta os turnos do pulo
        # cargas das Spire Runes (skill -> quantas), do ``HeroMsg.trials`` do jogador
        self.trials = {int(t.skillId): int(t.count) for t in player.msg.trials} if player is not None else {}
        self.player = next((u for u in self.units if u.is_player), None)
        self.wound = self.hurt = 0  # dano causado e sofrido pelo lado do jogador (relatório 137 da masmorra)
        if player is not None and self.player is not None:
            self._passives(self.player, [*player.msg.skillId, *player.passives])
        self.awake = player.msg.awake if player is not None else 0
        self.morphed = False
        self._hit_awake = False  # já ganhou pelo golpe levado desde a última ação do herói
        self._hero_skills = list(self.player.skills) if self.player is not None else []
        self._change = list(player.msg.changeSkillId) if player is not None else []
        pet = player.pet if player is not None else None
        self._morph_passives = [s for s in (pet or {}).get("change", []) if not self._usable(s)]
        self._on_awake = player.on_awake if player is not None else None

    def send(self, code: int, msg: Message) -> None:
        """Para quem já estava na luta e para os reforços (``joined``)."""
        self._out(code, msg)
        self.viewers = [v for v in self.viewers if not v.gone.is_set()]  # espectador que caiu sai da lista
        for viewer in [*self.joined, *self.viewers]:
            viewer.send(code, msg)

    def watch(self, viewer: Any) -> bool:
        """Espectador entra (8985): o 157 com a vida de agora e, se já começou, o 156 (o cliente só anda com ele);
        daí recebe tudo o que a luta manda. TODO(inventado): nenhuma captura de assistir; o 156 com ``frame`` 0."""
        if not self.running or viewer in self.viewers:
            return False
        viewer.send(S_PREPARE, self.prepare_msg())
        if self._t0 is not None:
            viewer.send(S_START, pb.BattleStartMsg(frame=0, mainType=self.spec["battleType"], countDown=COUNTDOWN_MS))
        self.viewers.append(viewer)
        return True

    def unwatch(self, viewer: Any, close_type: int = 0) -> None:
        """Tira o espectador e fecha a tela dele: 4803 (cliente ``BattleViewManager.onCloseBattleViewHandler``:
        ``param1`` 1 vitória, 2 derrota, outro só sai; ``param7`` saída normal)."""
        if viewer in self.viewers:
            self.viewers.remove(viewer)
            viewer.send(S_VIEW_CLOSE, pb.SimplePropertyMsg(param1=close_type, param7=True))

    def release_viewers(self, won: bool) -> None:
        """Fim da luta: todos os espectadores recebem o 4803 (vitória/derrota do lado 1, o que eles viam)."""
        for viewer in list(self.viewers):
            self.unwatch(viewer, 1 if won else 2)

    @property
    def player_sp(self) -> int:
        return self.player.sp if self.player is not None else 0

    def troops(self) -> tuple[int, int] | None:
        """(vida que sobrou, vida do começo) das pilhas da tropa do jogador; ``None`` sem tropa na luta."""
        ids = {
            s["livingId"]: int(s.get("initHp", s["hp"]))
            for s in self.spec["soldiers"]
            if is_player_troop(self.templates, s)
        }
        if not ids:
            return None
        return sum(max(0, u.hp) for u in self.units if u.living_id in ids), sum(ids.values())

    @property
    def frame(self) -> int:
        """Quadro atual, pelo relógio (somar sleeps acumula erro; no Windows o sleep anda de 15,6 ms)."""
        if self._t0 is None:
            return 0
        now = self._paused_at if self._paused_at is not None else time.monotonic()
        return int((now - self._t0 - self._paused_total) / FRAME_SECONDS)

    @property
    def running(self) -> bool:
        """Começou e não acabou nem foi cancelada (sessão que caiu cancela a luta)."""
        return self._task is not None and not self._task.done()

    @property
    def paused(self) -> bool:
        return self._paused_at is not None

    # -- montagem --------------------------------------------------------------------------

    def _with_army(self, spec: dict[str, Any], player: PlayerHero | None) -> dict[str, Any]:
        """Troca as pilhas da tropa do jogador gravadas na spec (as da captura) pelas do exército atual.
        (dedução) só onde a spec já tem pilhas: nas lutas roteirizadas sem tropa os livingIds são outros."""
        if player is None or player.army is None:
            return spec
        mine = [s for s in spec["soldiers"] if is_player_troop(self.templates, s)]
        if not mine:
            return spec
        others = [s for s in spec["soldiers"] if s not in mine]
        if self._player_msg is not None:
            self._player_msg.pawnTempId = int(player.army[0]["tempId"]) if player.army else 0
        return spec | {"soldiers": [*player.army, *others]}

    def _with_pet(self, player: PlayerHero, pet: Mapping[str, Any]) -> dict[str, Any]:
        """O mascote entra nos ``pets`` com o primeiro livingId livre; ele e o herói se apontam pelo ``livingId2``
        (visto peri_uyanis #50: herói 1 com livingId2 2, pet 2 com livingId2 1)."""
        spec = self.spec
        used = [u["livingId"] for k in ("soldiers", "heroes", "pets") for u in spec.get(k, [])]
        used += [u["livingId"] for wave in spec.get("reinforce", []) for u in wave]
        self.pet_id = max([*used, player.msg.livingId]) + 1
        player.msg.livingId2 = self.pet_id
        entry = dict(pet) | {"livingId": self.pet_id, "livingId2": player.msg.livingId}
        return spec | {"pets": [*spec.get("pets", []), entry]}

    def _units(self, player: PlayerHero | None) -> list[Unit]:
        """Soldados, heróis NPC e pets da spec, mais o herói do jogador. Atributos do template; ``stats`` e
        ``attack``/``defaultSkill`` na spec valem mais (cópia de jogador, robô, pet)."""
        units = [self._soldier(s) for s in self.spec["soldiers"]]
        for kind in ("heroes", "pets"):
            units += [self._npc(kind, h) for h in self.spec.get(kind, [])]
        if player is not None:
            m = player.msg
            stats = {k: int(player.stats.get(k, 0)) for k in STATS}
            units.append(
                Unit(
                    m.livingId, m.side, m.hp, list(m.skillId), player.default_skill, stats, m.maxHp or m.hp, True, m.sp
                )
            )
            # as gemas da guarda (HeroMsg.fireResi..reduceResi); o ReduceResi do dono vale para o mascote dele
            units[-1].resists = {k: v for k in RESIST_KEYS if (v := getattr(m, k[0].lower() + k[1:]))}
            reduce = units[-1].resists.get("ReduceResi", 0)
            for u in units:
                if reduce and u.living_id == self.pet_id:
                    u.resists["ReduceResi"] = reduce
        return units

    def _npc(self, kind: str, h: Mapping[str, Any]) -> Unit:
        row = self.templates.get("GameHeroTemp" if kind == "heroes" else "PetTempInfos", h["tempId"]) or {}
        default = int(h.get("defaultSkill") or row.get("DefaultSkill") or row.get("DefaultSkills") or 0)
        skills = list(h.get("follow") or h.get("skillId", [])) or [default]
        hp = int(h["hp"])
        reject = frozenset(int(x) for x in str(row.get("RejectType", "")).split(",") if x)
        unit = Unit(h["livingId"], h["side"], hp, skills, default, _stats(row, h), int(h.get("maxHp") or hp))
        unit.hero, unit.reject = kind == "heroes", reject
        if kind == "pets":
            unit.element = PET_ELEMENT.get(int(row.get("PetType") or 0), "")
            unit.resists = {k: v for k in RESIST_KEYS if (v := int(row.get(k) or 0))}
        return unit

    def _soldier(self, s: Mapping[str, Any]) -> Unit:
        row = self.templates.get("PawnTempInfos", s["tempId"]) or {}
        skills = list(s.get("skillId", [])) or [int(row.get("DefaultSkill", 0))]
        hp = int(s["hp"])
        return Unit(s["livingId"], s["side"], hp, skills, skills[0], _stats(row, s), int(s.get("initHp", hp)))

    def _preload_waves(self) -> None:
        """Um 4149 por onda logo depois do 156, para o cliente carregar os soldados: (visto) oficial_20261023-171155-1
        #2135-#2136 e 231733 #580-#581, ``soldierSkill`` = as skills de cada soldado em fila, ``reinforceCount`` 3 e
        ``reinforceType`` 1 com duas ondas. (cliente) ``ReinfoResTransaction``: carrega as skills, o ``reinforceCount``
        é o total de ondas do painel (``setReinforceWaveInfo``: as ondas mais a tropa inicial) e o ``armyId`` não é
        lido (o oficial usa um número global, ~1300695008)."""
        for wave in self._waves:
            res = pb.ArmyResMsg(reinforceCount=len(self._waves) + 1, reinforceType=1)
            entry = res.loadRes.add(armyId=next(_WAVE_IDS))
            entry.soldierTempId.extend(int(s["tempId"]) for s in wave)
            entry.soldierSkill.extend(int(k) for s in wave for k in s.get("skillId", []))
            self.send(S_LOAD_RES, res)

    def _reinforce(self) -> bool:
        """O lado inimigo caiu e a luta tem outra onda (``reinforce``, os 72 da captura): (visto) oficial_20261023-
        231733-1 #4458-#4459, o 72 sai logo depois do golpe que mata o último e a luta segue com os novos."""
        if not self._waves or not self._side_alive(True) or self._side_alive(False):
            return False
        if self.layer:
            jump = skip_to(self.layer, max((u.turn for u in self._wave), default=0), self.spec["battleType"])
            if jump > SPIRE_CLEAR:  # "Defeat within {0} turns to clear instantly"
                self.layer, self._waves = len(self._waves) + self.layer, []
                return False
            del self._waves[: jump - self.layer - 1]  # os andares pulados contam como vencidos
            self.layer = jump - 1
            if not self._waves:
                return False
        wave = self._waves.pop(0)
        self._wave = [self._soldier(s) for s in wave]
        self.units += self._wave
        msg = _parse({"side": wave[0]["side"], "soldiers": wave}, pb.ReinforceMsg())
        if self.layer:  # (cliente) ReinforceHandler: trialLayer = reinforceWave
            self.layer += 1
            msg.reinforceWave = self.layer
        self.send(S_REINFORCE, msg)
        return True

    def join(self, hero: dict[str, Any], viewer: Any) -> bool:
        """Reforço de jogador (8255, 8745): o herói (cópia, ``arena.copy_hero``) entra no lado 1 numa posição livre
        e age a partir da próxima rodada (``_round_order`` relê ``units``). Os de dentro recebem o 72 com o herói
        (cliente ``ReinforceHandler``: ``hero`` vira papel novo); ``viewer`` (quem tem ``send``) recebe o 157 com o
        estado atual e daí o resto da luta. TODO(inventado): nenhuma captura tem o 8255; a ordem (72 para os de
        dentro, 157 para quem chega) e as posições são deduções."""
        if not self.running or self._skip or not (self._side_alive(True) and self._side_alive(False)):
            return False
        spec = self.spec
        taken = {u["pos"] for k in ("soldiers", "heroes") for u in spec.get(k, []) if u.get("side") == PLAYER_SIDE}
        if self._player_msg is not None:
            taken.add(self._player_msg.pos)
        free = [p for p in TEAM_POS if p not in taken]
        if not free:
            return False
        used = [u.living_id for u in self.units] + [self.pet_id] + [s["livingId"] for w in self._waves for s in w]
        hero = hero | {"side": PLAYER_SIDE, "pos": free[0], "livingId": max(used) + 1}
        spec["heroes"] = [*spec.get("heroes", []), hero]
        self.units.append(self._npc("heroes", hero))
        self.send(S_REINFORCE, _parse({"side": PLAYER_SIDE, "hero": [hero]}, pb.ReinforceMsg()))
        viewer.send(S_PREPARE, self.prepare_msg())
        self.joined.append(viewer)
        return True

    def _passives(self, unit: Unit, skills: Iterable[int]) -> None:
        """Skills passivas (``UseWay`` 2) viram buffers permanentes do herói no 157: (visto) tutorial_en #1466
        ``buffers {bufferId 1, templateId 30111, curTurn -1, seeType 1, exeWay 0, pressedNum 1}``."""
        for skill in skills:
            row = self.templates.get("SkillTempInfos", skill)
            if row is None or row.get("UseWay") != PASSIVE:
                continue
            for buffer_id in filter(None, row.get("BufferIds", "").split(",")):
                buff = self._apply(unit, unit, int(buffer_id))
                if buff is not None:
                    buff.turn, buff.see = -1, 1
                    if self._player_msg is not None:
                        self._player_msg.buffers.append(buff.msg(battle_turns=False))

    def prepare_msg(self) -> pb.BattlePrepareMsg:
        spec = self.spec
        msg = pb.BattlePrepareMsg(
            battleId=self.id,
            battleType=spec["battleType"],
            mapTempId=spec["mapTempId"],
            needAnimation=True,
            side=PLAYER_SIDE,
            hasAssault=False,
            useWay=0,
            attackModel=spec["attackModel"],
            reinforceCount=0,
            currentReinforce=0,
            battleCapity=1,
            damageImprove=0,
            currentWave=self.layer,  # (cliente) CreateGameTransaction: trialLayer = currentWave
        )
        for s in spec["soldiers"]:
            _parse(s, msg.soldiers.add())
        for h in spec["heroes"]:
            _parse(h, msg.heros.add())
        for p in spec.get("pets", []):
            _parse(p, msg.pets.add())
        if self._player_msg is not None:
            msg.heros.add().CopyFrom(self._player_msg)
            for skill in self._player_msg.skillId:
                if self._usable(skill):
                    msg.coolDown.add(templatedId=skill, coolDown=0, coolType=1, appearCoolDown=0)
        hp = {u.living_id: max(0, u.hp) for u in self.units}  # quem chega no meio (``join``) vê a vida de agora
        for soldier in msg.soldiers:
            soldier.hp = hp.get(soldier.livingId, soldier.hp)
        for hero in msg.heros:
            hero.hp = hp.get(hero.livingId, hero.hp)
        for pet in msg.pets:
            pet.hp = hp.get(pet.livingId, pet.hp)
        return msg

    # -- comandos do cliente ----------------------------------------------------------------

    def start(self) -> None:
        self.send(S_PREPARE, self.prepare_msg())
        self._task = asyncio.create_task(self._run(), name=f"battle-{self.id}")

    def cancel(self) -> None:
        if self._task is not None:
            self._task.cancel()

    def load_over(self) -> None:
        self.loaded = True

    def pause(self) -> None:
        if self._paused_at is None:
            self._paused_at = time.monotonic()
        self.send(S_STOP, pb.UserStopMsg(type=1, order=0))

    def resume(self) -> None:
        if self._paused_at is None:
            return
        if self._t0 is not None:  # pausa antes do 156 não conta: o relógio nem começou
            self._paused_total += time.monotonic() - self._paused_at
        self._paused_at = None

    def set_auto(self, auto: bool) -> None:
        self.auto = auto

    def finish(self) -> None:
        """Termina já (8727, "encerrar a luta" do torneio de fadas): o resto é resolvido sem 153."""
        self._skip = True
        self.auto = True

    def use_trial(self, skill_id: int) -> int | None:
        """10507: uma Spire Rune (skill 101-104) vira a próxima ação do herói. Devolve as cargas que sobram, ou
        ``None`` se não tem carga (ou o herói caiu)."""
        p = self.player
        row = self.templates.get("SkillTempInfos", skill_id) or {}
        if p is None or self.trials.get(skill_id, 0) <= 0:
            return None
        if row.get("IsUseOnDead") == "1":  # Sacred Nirvana: "Revives a random team member or yourself" — já
            fallen = [u for u in self.units if u.side == p.side and u.hp <= 0 and (u.hero or u.is_player)]
            if not fallen:
                return None
            target = p if p.hp <= 0 else self.rng.choice(fallen)
            for buffer_id in filter(None, str(row.get("BufferIds", "")).split(",")):
                self._apply(p, target, int(buffer_id))
        elif p.hp <= 0:
            return None
        else:
            self._order = (skill_id, self.frame)
        self.trials[skill_id] -= 1
        return self.trials[skill_id]

    def order(self, living_id: int, skill_id: int) -> None:
        """10008: aceita (75 result 0) ou recusa (result 1) a skill escolhida."""
        p = self.player
        ok = (
            p is not None
            and living_id == p.living_id
            and (self._awaken_ok(skill_id) or skill_id in p.skills and self._affordable(skill_id))
        )
        targets = [t.living_id for t in self._targets(p, skill_id)] if ok and p is not None else []
        reply = pb.HeroOrderMsg(battleId=self.id, heroIndexId=living_id, skillId=skill_id, result=0 if ok else 1)
        reply.castTime, reply.qteTime = 0, 0
        reply.targetIndexs.extend(targets)
        self.send(S_ORDER, reply)
        if ok:
            self._order = (skill_id, self.frame)

    # -- simulação --------------------------------------------------------------------------

    async def _tick(self) -> None:
        await asyncio.sleep(FRAME_SECONDS)
        if self._notice is not None and self.frame >= self._notice:
            self._notice, self._improve = None, int(self.spec.get("damageImprove", 0))
            self.send(
                S_NOTICE, pb.BattleNoticeMsg(battleId=self.id, countDown=COUNTDOWN_MS, damageImprove=self._improve)
            )

    async def _until(self, frame: int) -> None:
        while self.frame < frame and not self._skip:
            await self._tick()

    async def _run(self) -> None:
        try:
            while not self.loaded or self.paused:  # noqa: ASYNC110  (dois sinalizadores; 40 ms não importam)
                await asyncio.sleep(FRAME_SECONDS)
            self._t0 = time.monotonic()
            self.send(S_START, pb.BattleStartMsg(frame=0, mainType=self.spec["battleType"], countDown=COUNTDOWN_MS))
            self._preload_waves()
            won = await self._fight()
            winners = [u for u in self.units if u.alive and (u.side == PLAYER_SIDE) == won]
            over = pb.PrepareOverMsg(frame=self.frame)
            for u in winners:
                over.prepareOverLivings.add(calcType=VICTORY, livingId=u.living_id, sp=u.sp)
            self.send(S_OVER, over)
            try:
                await self._on_end(self, won)
            finally:
                self.release_viewers(won)
        except asyncio.CancelledError:
            raise
        except Exception:
            log.exception("batalha quebrou", battle=self.id)

    def _side_alive(self, player_side: bool) -> bool:
        return any(u.alive for u in self.units if (u.side == PLAYER_SIDE) == player_side)

    def _round_order(self) -> list[Unit]:
        # ponytail: a iniciativa do oficial não foi decifrada (#727 e #782 têm as mesmas unidades e ordens
        # diferentes); aliados NPC, inimigos e o herói por último
        allies = [u for u in self.units if u.side == PLAYER_SIDE and not u.is_player]
        enemies = [u for u in self.units if u.side != PLAYER_SIDE]
        hero = [self.player] if self.player is not None else []
        return sorted(allies, key=lambda u: u.living_id) + sorted(enemies, key=lambda u: u.living_id) + hero

    async def _fight(self) -> bool:
        start, end, side = 0, FIRST_ACTION - NEXT_GAP, 0
        while True:
            first = True
            for unit in self._round_order():
                self._sync()
                if not unit.alive:
                    continue
                if not (self._side_alive(True) and self._side_alive(False)) and not self._reinforce():
                    break
                if self._has(unit, NO_ACTION):
                    # (dedução) atordoado perde a vez sem 153; o turno do controle conta, e o fim dele vai no
                    # próximo 153 em que a unidade aparecer. Falta captura de uma luta com atordoamento
                    self._turn_buffs(unit)
                    continue
                due = end + NEXT_GAP if first or unit.side != side else start + SAME_SIDE_GAP
                self._order_frame = None
                skill = await self._player_skill(due) if unit.is_player else self._npc_skill(unit)
                if self._has(unit, {AMNESIA}):  # esqueceu as skills: só o golpe básico
                    skill = unit.default_skill
                if self.pvp and unit.hero and unit.side != PLAYER_SIDE and not self._skip:
                    self._announce(unit, skill)
                if self._order_frame is not None:
                    due = max(due, self._order_frame + ORDER_DELAY)
                await self._until(due)
                start, side, first = self.frame, unit.side, False
                end = start + self._act(unit, skill)
            self._sync()
            if not (self._side_alive(True) and self._side_alive(False)) and not self._reinforce():
                await self._until(start + END_DELAY)
                return self._side_alive(True)

    def _sync(self) -> None:
        """A vida compartilhada pode ter caído pelos golpes de outros jogadores enquanto esta luta esperava."""
        if self.shared is not None:
            unit = next((u for u in self.units if u.living_id == self.shared.living_id), None)
            if unit is not None:
                unit.hp = self.shared.hp()

    def _announce(self, unit: Unit, skill: int) -> None:
        """75 do herói inimigo: o cliente mostra a skill que ele vai usar (inglês #1662)."""
        msg = pb.HeroOrderMsg(battleId=self.id, heroIndexId=unit.living_id, skillId=skill, result=0)
        msg.castTime, msg.qteTime = ENEMY_CAST_MS.get(skill, DEFAULT_CAST_MS), 0
        msg.targetIndexs.extend(t.living_id for t in self._targets(unit, skill))
        self.send(S_ORDER, msg)

    async def _player_skill(self, due: int) -> int:
        assert self.player is not None
        self._order_frame = None
        if self.morphed and self.awake <= 0:  # (dedução) o cliente espera o 700002 (isWaitingChangeBody)
            return UNMORPH
        if self.auto:
            return self._auto_skill()
        # manual: sem ordem na vez dele, golpe básico (visto: tutorial_en #152, #271, #274, sem 10008, e o
        # 30000 do #1657 ao #1704, com fúria sobrando). No PvE a vez é o ``due``; o guia que ensina a 30811
        # pausa a luta (10010), e a pausa congela o relógio. No PvP espera até ORDER_TIMEOUT (#1667, quadro 111).
        limit = max(due, self.frame + ORDER_TIMEOUT) if self.pvp else due
        while self._order is None and not self.auto and self.frame < limit:
            await self._tick()
        if self._order is None:
            return self._auto_skill() if self.auto else self.player.default_skill
        skill, self._order_frame = self._order
        self._order = None
        # ordem que não dá mais (fúria): golpe básico (visto #279 recusada, #281 com 30000)
        return skill if self._awaken_ok(skill) or self._affordable(skill) else self.player.default_skill

    def _awaken_ok(self, skill: int) -> bool:
        """Cliente HeroRoleInfo.canMorph/canCancelMorph: transforma com o despertar cheio, desfaz com mais que 0."""
        if skill == MORPH:
            return not self.morphed and bool(self._change) and self.awake >= int(self.formula["awake_max"])
        return skill == UNMORPH and self.morphed and self.awake > 0

    def _auto_skill(self) -> int:
        assert self.player is not None
        return next((s for s in self.player.skills if self._affordable(s)), self.player.default_skill)

    def _npc_skill(self, unit: Unit) -> int:
        # rotação da HeroAi, sem as passivas
        for k in range(len(unit.skills)):
            skill = unit.skills[(unit.turn + k) % len(unit.skills)]
            if self._usable(skill):
                return skill
        return unit.default_skill

    def _usable(self, skill: int) -> bool:
        row = self.templates.get("SkillTempInfos", skill)
        return row is not None and row.get("UseWay") != PASSIVE

    def _cost(self, skill: int) -> int:
        row = self.templates.get("SkillTempInfos", skill)
        return int(row["Cost"]) if row else 0

    def _affordable(self, skill: int) -> bool:
        return self._usable(skill) and self.player_sp + self._cost(skill) >= 0

    @staticmethod
    def _heals(row: Mapping[str, str]) -> bool:
        """Cura: só o Parameter2 e negativo (visto: 40183 da Dinah, P1 0 P2 -50, dano -53 e -51 no aliado)."""
        return int(row.get("Parameter1") or 0) == 0 and int(row.get("Parameter2") or 0) < 0

    def _targets(self, unit: Unit, skill: int) -> list[Unit]:
        row = self.templates.get("SkillTempInfos", skill) or {}
        if row.get("AcceptObject") == SELF:
            return [unit]
        if row and self._heals(row):  # (dedução) o aliado com menos vida proporcional
            allies = [u for u in self.units if u.alive and u.side == unit.side]
            return sorted(allies, key=lambda u: (u.hp / max(1, u.max_hp), u.living_id))[:1]
        if self._has(unit, {CONFUSED}):  # (dedução) confuso: qualquer um vivo, até aliado
            others = [u for u in self.units if u.alive and u is not unit]
            return [self.rng.choice(others)] if others else []
        foes = sorted((u for u in self.units if u.alive and u.side != unit.side), key=lambda u: u.living_id)
        if not foes or row.get("AcceptObject") == ALL_ENEMIES:
            return foes
        return [foes[0]]

    # -- buffers ----------------------------------------------------------------------------

    def _has(self, unit: Unit, kinds: set[int]) -> bool:
        return any(b.target == unit.living_id and b.active and b.kind in kinds for b in self.buffs)

    def _mods(self, unit: Unit, kinds: set[int]) -> tuple[int, int]:
        """(% somado, valor fixo somado) dos buffers ativos de ``unit`` desses tipos."""
        mine = [b for b in self.buffs if b.target == unit.living_id and b.active and b.kind in kinds]
        return sum(b.percent for b in mine), sum(b.value for b in mine)

    def _stat(self, unit: Unit, key: str) -> float:
        percent, flat = self._mods(unit, {STAT_BUFF[key]})
        return unit.stats[key] * (100 + percent) / 100 + flat

    def _apply(self, source: Unit, target: Unit, buffer_id: int) -> Buff | None:
        """Põe (ou renova) o buffer. Tipo na ``RejectType`` do alvo não pega (Karda 1023: 19,100,38,39)."""
        row = self.templates.get("SkillBufferTempInfos", buffer_id, key="Id")
        if row is None or int(row["AttackType"]) in target.reject:
            return None
        turns = int(row["ValidCount"])
        old = next((b for b in self.buffs if b.target == target.living_id and b.row is row and b.active), None)
        if old is not None:
            old.turn, old.see = turns, 0
            return old
        self._buff_seq += 1
        buff = Buff(self._buff_seq, row, source.living_id, target.living_id, turns)
        self.buffs.append(buff)
        if int(row["AttackWay"]) == AT_ONCE:
            self._effect(buff, target, AT_ONCE)
        return buff

    def _effect(self, buff: Buff, unit: Unit, way: int) -> None:
        """Efeito de vida (5 fixo, 33 % da vida máxima) ou de fúria (6) do buffer no portador; o valor vai no
        ``damage`` do BufferMsg (visto #1485: sangramento 60023 com damageType 6 e valor 25)."""
        buff.way = way
        if buff.kind in (HP, HP_PERCENT):
            delta = buff.value + unit.max_hp * buff.percent // 100
            if delta < 0:
                delta = -min(-delta, self._floor_hp(unit, -delta))
            unit.hp = max(0, min(unit.max_hp, unit.hp + delta))
            buff.damage.append(pb.DamageMsg(livingId=unit.living_id, damageType=DAMAGE_HP, damageValue=-delta,
                                            leftValue=unit.hp, parry=False))  # fmt: skip
        elif buff.kind == REVIVE and unit.hp <= 0:
            unit.hp = max(1, unit.max_hp * buff.percent // 100)
            buff.damage.append(pb.DamageMsg(livingId=unit.living_id, damageType=DAMAGE_HP, damageValue=-unit.hp,
                                            leftValue=unit.hp, parry=False))  # fmt: skip
        elif buff.kind == RAGE and buff.value:
            unit.sp += buff.value
            buff.damage.append(pb.DamageMsg(livingId=unit.living_id, damageType=DAMAGE_SP, damageValue=buff.value,
                                            leftValue=unit.sp, parry=False))  # fmt: skip

    def _turn_buffs(self, unit: Unit) -> None:
        """Ação do portador: cada buffer dele perde um turno (o permanente vai a -2, -3...) e os de ação
        (sangramento, cura por turno, fúria por ação) agem. No 0 o buffer sai (seeType 2)."""
        for buff in self.buffs:
            if buff.target != unit.living_id or not buff.active:
                continue
            buff.turn -= 1
            buff.see = 2 if buff.turn == 0 else 1
            if int(buff.row["AttackWay"]) == ON_ACTION:
                self._effect(buff, unit, ON_ACTION)

    def _listed(self, ids: set[int]) -> list[Buff]:
        """Buffers que vão no 153: os do autor e dos alvos (visto: #1486 sem buffer nenhum envolvido, vazio)."""
        return [b for b in self.buffs if b.target in ids and (b.active or b.see == 2)]

    # -- golpe ------------------------------------------------------------------------------

    def _floor_hp(self, target: Unit, value: int) -> int:
        """Com ``undying`` (tutorial roteirizado, chefe do mundo) o lado do jogador não cai abaixo de 1 de vida."""
        if target.side == PLAYER_SIDE and self.spec.get("undying") and not self.pvp:
            return min(value, max(0, target.hp - 1))
        return value

    def _hit(self, unit: Unit, target: Unit, row: Mapping[str, str], hits: int) -> tuple[int, bool, bool]:
        """Um golpe em ``target``: (valor, crítico, bloqueio). Valor negativo é cura."""
        f = self.formula
        p1, p2 = int(row.get("Parameter1") or 100), int(row.get("Parameter2") or 0)
        spread = self.rng.uniform(1 - f["spread"], 1 + f["spread"])
        if self._heals(row):
            return int(p2 * spread), False, False
        magic = row.get("CountWay") == MAGIC
        attack = self._stat(unit, "MagicAttack" if magic else "PhyAttack")
        ignore = self._mods(unit, {IGNORE_MDEF if magic else IGNORE_PDEF})[1]
        defence = max(0.0, self._stat(target, "MagicDefence" if magic else "PhyDefence") - ignore)
        value = damage(attack, defence, p1, p2, f)
        dealt_pct, dealt_flat = self._mods(unit, {DEALT, DEALT2})
        taken_pct, taken_flat = self._mods(target, {RECEIVED})
        value = value * (100 + dealt_pct) / 100 + dealt_flat
        value = value * (100 + taken_pct) / 100 + taken_flat
        value *= (100 + self._improve) / 100 * spread * resist_factor(unit, target, f)
        crit_pct, crit_flat = self._mods(unit, {CRIT})
        crit = self.rng.random() < 1 - f["crit_base"] ** unit.stats["ForceHit"] + (crit_pct + crit_flat) / 100
        if crit:
            value *= f["crit_damage"] + self._mods(unit, {CRIT_DAMAGE})[0] / 100
        block = self.rng.random() < 1 - f["block_base"] ** target.stats["Parry"]
        if block:
            value *= f["block_damage"]
        return max(1, int(value / hits)), crit, block

    def _act(self, unit: Unit, skill: int) -> int:
        """Executa e manda o 153; devolve a duração da animação em quadros."""
        row = self.templates.get("SkillTempInfos", skill) or {}
        action = self.templates.get("ActionTempInfos", int(row.get("ActionId", skill)), key="ActionId") or {}
        frames = int(action.get("FrameNum", 30)) + 5
        hits = max(1, int(action.get("AttackTimes", 1)))
        cost = int(row.get("Cost", 0)) if unit.is_player else 0
        unit.sp += cost
        unit.turn += 1
        if unit.is_player and skill in self._once:
            self._once.discard(skill)
            unit.skills = [s for s in unit.skills if s != skill]  # runa: uma vez por batalha
        msg = pb.AttackOrderMsg(
            battleId=self.id,
            frame=self.frame,
            orderId=skill,
            isPassive=False,
            livingId=unit.living_id,
            spAdded=cost,
            execFrame=self.frame,
            frameNum=frames,
            attackMillis=fmt_time(self.clock.now()),
            awake=self.awake if unit.is_player else 0,  # (visto) só o 153 do herói leva o despertar
            curturn=unit.turn,
        )
        self._turn_buffs(unit)  # sangramento antes do golpe (visto #1485: 222 -> 197, depois o golpe)
        shared = self.shared
        kills = unit.side != PLAYER_SIDE and 0 < self._kill_turn <= unit.turn
        if kills:
            targets = [u for u in self.units if u.alive and u.side == PLAYER_SIDE]
        else:
            targets = self._targets(unit, skill) if unit.alive else []
        dealt = 0
        for target in targets:
            if target is unit and row.get("AcceptObject") == SELF:  # (visto #562) Fury: dano 0, leftValue 0
                msg.damages.add(livingId=unit.living_id, damageType=DAMAGE_HP, damageValue=0, leftValue=0, parry=False)
                continue
            for k in range(hits):
                value, crit, block = (target.hp, False, False) if kills else self._hit(unit, target, row, hits)
                if value < 0:
                    value = -min(-value, target.max_hp - target.hp)
                    target.hp -= value
                else:
                    value = value if kills else self._floor_hp(target, value)
                    if shared is not None and target.living_id == shared.living_id:
                        value = shared.hit(value + shared.bonus)  # síncrono: dois golpes nunca levam a mesma vida
                        shared.dealt += value
                        target.hp = shared.hp()
                    else:
                        target.hp = max(0, target.hp - value)
                    if unit.side == PLAYER_SIDE and target.side != PLAYER_SIDE:
                        self.wound += value
                    elif target.side == PLAYER_SIDE and unit.side != PLAYER_SIDE:
                        self.hurt += value
                    dealt += target.side != unit.side
                msg.damages.add(
                    livingId=target.living_id,
                    damageType=DAMAGE_HP,
                    damageValue=value,
                    leftValue=target.hp,
                    extraData=int(crit),
                    parry=block,
                    order=k,
                )
        for buff in self._listed({unit.living_id}):  # fúria por golpe causado (30111: +1 por dano, visto #3136)
            if int(buff.row["AttackWay"]) == ON_DEALT and buff.active:
                buff.way = ON_DEALT
                for _ in range(dealt if buff.kind == RAGE else 0):
                    self._effect(buff, unit, ON_DEALT)
        self._skill_buffs(unit, row, targets)
        msg.sp = unit.sp
        listed = self._listed({unit.living_id} | {t.living_id for t in targets})
        msg.buffers.extend(b.msg() for b in listed)
        for buff in listed:
            buff.damage = []
        sent = {id(b) for b in listed}  # o removido sai depois de ir num 153 (o do atordoado espera o próximo)
        self.buffs = [b for b in self.buffs if b.active or id(b) not in sent]
        if not self._skip:
            self.send(S_ATTACK, msg)
        self._awaken(unit, skill, targets)
        return frames

    def _awaken(self, unit: Unit, skill: int, targets: list[Unit]) -> None:
        """Despertar (4600 depois do 153, só com mascote): ganha por ação do herói e por golpe levado (um só entre
        duas ações dele; dedução: exp_kitabi #59-#63, três golpes e um 4600); transformado, cada ação gasta e golpe
        não dá. 700001 troca as skills pelas ``changeSkillId`` e põe as passivas do mascote; 700002 desfaz."""
        hero, f = self.player, self.formula
        if hero is None or not self.pet_id:
            return
        old = self.awake
        if unit is hero:
            if skill == MORPH:
                self.morphed, hero.skills = True, list(self._change)
                self._morph_buffs(hero, on=True)
            elif skill == UNMORPH:
                self.morphed, hero.skills = False, list(self._hero_skills)
                self._morph_buffs(hero, on=False)
            if self.morphed:
                self.awake -= int(f["awake_cost"])
            elif skill != UNMORPH:
                self.awake += int(f["awake_gain"])
            self._hit_awake = False
        elif hero in targets and unit.side != hero.side and not self.morphed and not self._hit_awake:
            self.awake += int(f["awake_gain"])
            self._hit_awake = True
        self.awake = max(0, min(int(f["awake_max"]), self.awake))
        if self.awake == old:
            return
        if self._on_awake is not None:
            self._on_awake(self.awake)
        if not self._skip:
            self.send(S_AWAKE, pb.AwakeMsg(awake=[pb.AwakeInfoMsg(livingId=hero.living_id, awake=self.awake)]))

    def _morph_buffs(self, hero: Unit, on: bool) -> None:
        """Passivas do modo mascote (731201 Breath Shield): buffer permanente ao transformar, sai ao desfazer
        (visto peri_uyanis #60: 731201 no herói com curTurn -1)."""
        for skill in self._morph_passives:
            row = self.templates.get("SkillTempInfos", skill) or {}
            for buffer_id in filter(None, str(row.get("BufferIds", "")).split(",")):
                if on:
                    buff = self._apply(hero, hero, int(buffer_id))
                    if buff is not None:
                        buff.turn = -1
                    continue
                for b in self.buffs:
                    if b.target == hero.living_id and b.active and int(b.row["Id"]) == int(buffer_id):
                        b.turn, b.see = 0, 2

    def _skill_buffs(self, unit: Unit, row: Mapping[str, str], targets: list[Unit]) -> None:
        """BufferIds da skill nos alvos vivos (no próprio autor se ``AcceptObject`` 4). A chance vem do texto
        da skill ("50% chance", cliente SkillTempInfo.Description); sem texto, sempre (dedução)."""
        ids = [int(x) for x in str(row.get("BufferIds", "")).split(",") if x]
        if not ids or row.get("UseWay") == PASSIVE:
            return
        found = CHANCE.search(str(row.get("Description", "")))
        if found and self.rng.random() * 100 >= int(found.group(1)):
            return
        for target in [unit] if row.get("AcceptObject") == SELF else [t for t in targets if t.alive]:
            for buffer_id in ids:
                self._apply(unit, target, buffer_id)


def _stats(row: Mapping[str, str], spec: Mapping[str, Any]) -> dict[str, int]:
    """Atributos do template (Attack, Defence...), trocados pelos ``stats`` e pelo ``attack`` da spec."""
    stats = {k: int(row.get(col) or 0) for k, col in TEMPLATE_STATS.items()}
    stats.update({k: int(v) for k, v in (spec.get("stats") or {}).items() if k in stats})
    if spec.get("attack"):
        stats["PhyAttack"] = stats["MagicAttack"] = int(spec["attack"])
    return stats
