"""Batalha PvE simulada no servidor, em tempo real (o cliente só toca o que recebe).

Relógio em quadros de 40 ms (25 fps) a partir do 156. Cada ação vai num 153 no quadro em que
acontece; mandar adiantado faz o cliente saltar o relógio. Detalhes do protocolo em
``docs/batalha.md``.

Modelo observado na captura: rodadas em que cada unidade viva age uma vez; ações do mesmo lado
começam com 12 quadros de diferença, a troca de lado e a rodada seguinte vêm ~9 quadros depois do
fim da última animação (``frameNum``); a primeira ação sai por volta do quadro 100. O herói do
jogador espera a ordem (10008) do cliente.
"""

from __future__ import annotations

import asyncio
import random
import uuid
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any

import structlog
from google.protobuf.json_format import ParseDict
from google.protobuf.message import Message

from ..protocol.messages import wartune_pb2 as pb
from ..services.clock import Clock
from ..templates.repository import GameTemplates
from .builders.login import fmt_time

log = structlog.get_logger(__name__)

S_PREPARE, S_START, S_ATTACK, S_OVER, S_ORDER, S_STOP = 157, 156, 153, 154, 75, 69

FRAME_SECONDS = 0.04
FIRST_ACTION = 100
SAME_SIDE_GAP = 12  # entre inícios de ações do mesmo lado
NEXT_GAP = 9  # depois do fim da animação: troca de lado ou rodada nova
ORDER_DELAY = 25  # ordem recebida -> golpe
ORDER_WAIT = 75  # sem ordem por 3 s: golpe padrão do herói
END_DELAY = 90  # último golpe -> 154
COUNTDOWN_MS = 60000
DAMAGE_HP = 6  # DamageMsg.damageType: vida (bloodA)
VICTORY, DEFEAT = 3, 4  # PrepareOverLivingMsg.calcType = SkillTempInfo "Zafer"/"Başarısız"
ALL_ENEMIES = "3"  # SkillTempInfo.AcceptObject; 4 = si mesmo, 5 = aliado (curas e buffs)
SELF_OR_ALLY = {"4", "5"}
PLAYER_SIDE = 1
AUTO = 1  # AttackModeMsg.mode / BattlePrepareMsg.attackModel


@dataclass
class Unit:
    living_id: int
    side: int
    hp: int
    skills: list[int]
    attack: int
    default_skill: int
    is_player: bool = False
    sp: int = 0
    turn: int = 0

    @property
    def alive(self) -> bool:
        return self.hp > 0


@dataclass(frozen=True, slots=True)
class PlayerHero:
    """O que a batalha precisa do herói do jogador (montado pela sessão)."""

    msg: pb.HeroMsg
    attack: int
    default_skill: int


class Battle:
    def __init__(
        self,
        spec: dict[str, Any],
        player: PlayerHero,
        templates: GameTemplates,
        clock: Clock,
        send: Callable[[int, Message], None],
        on_end: Callable[[Battle, bool], Awaitable[None]],
    ) -> None:
        self.id = str(uuid.uuid4())
        self.spec, self.templates, self.clock = spec, templates, clock
        self._send, self._on_end = send, on_end
        self.frame = 0
        self.paused = False
        self.loaded = False
        self.auto = spec["attackModel"] == AUTO
        self._order: tuple[int, int] | None = None  # (skillId, quadro em que chegou)
        self._order_frame: int | None = None  # quadro da ordem usada no golpe atual do herói
        self._task: asyncio.Task[None] | None = None
        self._player_msg = player.msg
        self.units = self._units(player)
        self.player = next(u for u in self.units if u.is_player)

    # -- montagem --------------------------------------------------------------------------

    def _units(self, player: PlayerHero) -> list[Unit]:
        units = []
        for s in self.spec["soldiers"]:
            row = self.templates.get("PawnTempInfos", s["tempId"]) or {}
            skills = list(s.get("skillId", [])) or [int(row.get("DefaultSkill", 0))]
            attack = max(int(row.get("Attack", 0)), int(row.get("MagicAttack", 0)))
            units.append(Unit(s["livingId"], s["side"], s["hp"], skills, attack, skills[0]))
        for h in self.spec["heroes"]:
            row = self.templates.get("GameHeroTemp", h["tempId"]) or {}
            default = int(row.get("DefaultSkill", 0))
            attack = max(int(row.get("Attack", 0)), int(row.get("MagicAttack", 0)))
            units.append(
                Unit(h["livingId"], h["side"], h["hp"], list(h.get("skillId", [])) or [default], attack, default)
            )
        m = player.msg
        units.append(Unit(m.livingId, m.side, m.hp, list(m.skillId), player.attack, player.default_skill, True, m.sp))
        return units

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
        )
        for s in spec["soldiers"]:
            ParseDict(s, msg.soldiers.add())
        for h in spec["heroes"]:
            ParseDict(h, msg.heros.add())
        msg.heros.add().CopyFrom(self._player_msg)
        for skill in self._player_msg.skillId:
            msg.coolDown.add(templatedId=skill, coolDown=0, coolType=1, appearCoolDown=0)
        return msg

    # -- comandos do cliente ----------------------------------------------------------------

    def start(self) -> None:
        self._send(S_PREPARE, self.prepare_msg())
        self._task = asyncio.create_task(self._run(), name=f"battle-{self.id}")

    def cancel(self) -> None:
        if self._task is not None:
            self._task.cancel()

    def load_over(self) -> None:
        self.loaded = True

    def pause(self) -> None:
        self.paused = True
        self._send(S_STOP, pb.UserStopMsg(type=1, order=0))

    def resume(self) -> None:
        self.paused = False

    def set_auto(self, auto: bool) -> None:
        self.auto = auto

    def order(self, living_id: int, skill_id: int) -> None:
        """10008: aceita (75 result 0) ou recusa (result 1) a skill escolhida."""
        ok = living_id == self.player.living_id and skill_id in self.player.skills and self._affordable(skill_id)
        targets = [t.living_id for t in self._targets(self.player, skill_id)] if ok else []
        reply = pb.HeroOrderMsg(battleId=self.id, heroIndexId=living_id, skillId=skill_id, result=0 if ok else 1)
        reply.castTime, reply.qteTime = 0, 0
        reply.targetIndexs.extend(targets)
        self._send(S_ORDER, reply)
        if ok:
            self._order = (skill_id, self.frame)

    # -- simulação --------------------------------------------------------------------------

    async def _tick(self) -> None:
        await asyncio.sleep(FRAME_SECONDS)
        if not self.paused:
            self.frame += 1

    async def _until(self, frame: int) -> None:
        while self.frame < frame:
            await self._tick()

    async def _run(self) -> None:
        try:
            while not self.loaded or self.paused:  # noqa: ASYNC110  (dois sinalizadores; 40 ms não importam)
                await asyncio.sleep(FRAME_SECONDS)
            self._send(S_START, pb.BattleStartMsg(frame=0, mainType=self.spec["battleType"], countDown=COUNTDOWN_MS))
            won = await self._fight()
            winners = [u for u in self.units if u.alive and (u.side == PLAYER_SIDE) == won]
            over = pb.PrepareOverMsg(frame=self.frame)
            for u in winners:
                over.prepareOverLivings.add(calcType=VICTORY, livingId=u.living_id, sp=u.sp)
            self._send(S_OVER, over)
            await self._on_end(self, won)
        except asyncio.CancelledError:
            raise
        except Exception:
            log.exception("batalha quebrou", battle=self.id)

    def _side_alive(self, player_side: bool) -> bool:
        return any(u.alive for u in self.units if (u.side == PLAYER_SIDE) == player_side)

    def _round_order(self) -> list[Unit]:
        # ponytail: a iniciativa do oficial não foi decifrada; aliados NPC, inimigos e o herói por último
        allies = [u for u in self.units if u.side == PLAYER_SIDE and not u.is_player]
        enemies = [u for u in self.units if u.side != PLAYER_SIDE]
        return sorted(allies, key=lambda u: u.living_id) + sorted(enemies, key=lambda u: u.living_id) + [self.player]

    async def _fight(self) -> bool:
        start, end, side = 0, FIRST_ACTION - NEXT_GAP, 0
        while True:
            first = True
            for unit in self._round_order():
                if not unit.alive:
                    continue
                if not (self._side_alive(True) and self._side_alive(False)):
                    break
                due = end + NEXT_GAP if first or unit.side != side else start + SAME_SIDE_GAP
                self._order_frame = None
                skill = await self._player_skill(due) if unit.is_player else self._npc_skill(unit)
                if self._order_frame is not None:
                    due = max(due, self._order_frame + ORDER_DELAY)
                await self._until(due)
                start, side, first = self.frame, unit.side, False
                end = start + self._act(unit, skill)
            if not (self._side_alive(True) and self._side_alive(False)):
                await self._until(start + END_DELAY)
                return self._side_alive(True)

    async def _player_skill(self, due: int) -> int:
        self._order_frame = None
        if self.auto and self._order is None:
            return self._auto_skill()
        deadline = max(due, self.frame) + ORDER_WAIT
        while self._order is None and (self.frame < deadline or self.paused):
            await self._tick()
        if self._order is None:
            return self._auto_skill()
        skill, self._order_frame = self._order
        self._order = None
        return skill if self._affordable(skill) else self._auto_skill()

    def _auto_skill(self) -> int:
        return next((s for s in self.player.skills if self._affordable(s)), self.player.default_skill)

    def _npc_skill(self, unit: Unit) -> int:
        # rotação da HeroAi; curas e buffs (alvo próprio/aliado) ficam de fora por enquanto
        for k in range(len(unit.skills)):
            skill = unit.skills[(unit.turn + k) % len(unit.skills)]
            row = self.templates.get("SkillTempInfos", skill)
            if row is not None and row.get("AcceptObject") not in SELF_OR_ALLY:
                return skill
        return unit.default_skill

    def _cost(self, skill: int) -> int:
        row = self.templates.get("SkillTempInfos", skill)
        return int(row["Cost"]) if row else 0

    def _affordable(self, skill: int) -> bool:
        return self.player.sp + self._cost(skill) >= 0

    def _targets(self, unit: Unit, skill: int) -> list[Unit]:
        foes = sorted((u for u in self.units if u.alive and u.side != unit.side), key=lambda u: u.living_id)
        row = self.templates.get("SkillTempInfos", skill)
        if not foes or (row is not None and row.get("AcceptObject") == ALL_ENEMIES):
            return foes
        return [foes[0]]

    def _act(self, unit: Unit, skill: int) -> int:
        """Executa e manda o 153; devolve a duração da animação em quadros."""
        row = self.templates.get("SkillTempInfos", skill) or {}
        action = self.templates.get("ActionTempInfos", int(row.get("ActionId", skill)), key="ActionId") or {}
        frames = int(action.get("FrameNum", 30)) + 5
        hits = max(1, int(action.get("AttackTimes", 1)))
        cost = int(row.get("Cost", 0)) if unit.is_player else 0
        unit.sp += cost
        unit.turn += 1
        msg = pb.AttackOrderMsg(
            battleId=self.id,
            frame=self.frame,
            orderId=skill,
            isPassive=False,
            livingId=unit.living_id,
            sp=unit.sp,
            spAdded=cost,
            execFrame=self.frame,
            frameNum=frames,
            attackMillis=fmt_time(self.clock.now()),
            awake=0,
            curturn=unit.turn,
        )
        raw = unit.attack * int(row.get("Parameter1", 100)) / 100 + int(row.get("Parameter2", 0))
        for target in self._targets(unit, skill):
            for _ in range(hits):
                # ponytail: fórmula de dano desconhecida; calibrado na captura (herói mata os soldados
                # do tutorial com um golpe, soldados tiram ~35% do ataque). Trocar quando houver a real.
                factor = 0.65 if unit.side == PLAYER_SIDE else random.uniform(0.3, 0.4)
                value = max(1, int(raw * factor / hits))
                target.hp = max(0, target.hp - value)
                msg.damages.add(
                    livingId=target.living_id, damageType=DAMAGE_HP, damageValue=value, leftValue=target.hp, parry=False
                )
        self._send(S_ATTACK, msg)
        return frames
