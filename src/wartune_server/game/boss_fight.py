"""Chefe do mundo: a vida compartilhada de uma janela, o ranking de dano, a moral e os prêmios do fim.

Todo o servidor bate no mesmo chefe. O dano entra no ``Pool`` dentro do golpe (``Battle._act``, sem await), então
dois golpes nunca levam a mesma vida e só um pode ser o último. O pool vive no processo (``Bosses``) e no banco: a
janela (``WorldBossFight``) e o dano de cada um (``WorldBossWound``), gravados no fim de cada luta; a vida atual é
a cheia menos a soma dos danos, então um restart só perde a luta em curso.

Fontes (docs/boss-eventos.md):
- (cliente) help ``worldboss.view.BaseHelpFrame.helpText``: ouro e Ruh por golpe, "HP e tropas não se esgotam",
  prêmio do último golpe (Şanslı Ödülü), top 10 do dano, prêmio por 0,3%/0,5%/0,8% do dano total.
- (cliente) ``WoundInfoView.buffTip``/``buffGradeTip``: a moral sobe a cada 500 mil do maior dano e dá
  ``bufferGrade * 500``; ``WorldBossModel.commit`` guarda até 30 e monta o top 10 geral e o da classe.
- (internet) a config de cada chefe e dos prêmios, no banco (``world_bosses``, ``world_boss_rewards``).
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import datetime

from ..domain.models import WorldBossFight, WorldBossWound
from ..domain.repositories import UnitOfWork
from ..domain.world import World, WorldBoss
from ..protocol.messages import wartune_pb2 as pb
from ..services.characters import CharacterService
from ..templates.repository import GameTemplates
from . import worldboss

# (cliente) buffTip, buffGradeTip; CampaignBufferTemps 701-720
INSPIRE_STEP, INSPIRE_BONUS, INSPIRE_MAX = 500_000, 500, 20
RANKED = 30  # (cliente) WorldBossModel.commit guarda até 30


def job_class(job: int) -> int:
    """Classe para o top 10 da classe (cliente: ``ThaneInfoHelper.getJob``, o ícone usa ``job % 3``)."""
    return job % 3


@dataclass
class Pool:
    """Uma janela aberta de um chefe."""

    boss: WorldBoss
    fight: WorldBossFight
    wounds: dict[int, WorldBossWound] = field(default_factory=dict)  # personagem -> dano
    lock: asyncio.Lock = field(default_factory=asyncio.Lock)  # gravar e pagar o fim, um de cada vez
    dead: dict[int, datetime] = field(default_factory=dict)  # personagem -> quando revive
    timers: dict[int, asyncio.TimerHandle] = field(default_factory=dict)

    @property
    def hp(self) -> int:
        return max(0, self.fight.total_hp - sum(w.wound for w in self.wounds.values()))

    @property
    def alive(self) -> bool:
        return self.hp > 0 and not self.fight.settled

    def wound_of(self, character_id: int, nickname: str, job: int) -> WorldBossWound:
        row = self.wounds.get(character_id)
        if row is None:
            row = self.wounds[character_id] = WorldBossWound(self.fight.id or 0, character_id, nickname, job)
        return row

    def hit(self, character_id: int, nickname: str, job: int, value: int, now: datetime) -> int:
        """Tira até ``value`` da vida (síncrono). Devolve o que tirou; quem zera é o último golpe."""
        taken = min(max(0, value), self.hp) if self.alive else 0
        if taken:
            self.wound_of(character_id, nickname, job).wound += taken
            if self.hp == 0:
                self.fight.killer_id, self.fight.killed_at = character_id, now
        return taken

    def is_dead(self, character_id: int, now: datetime) -> bool:
        until = self.dead.get(character_id)
        return until is not None and now < until

    def ranking(self) -> list[WorldBossWound]:
        return sorted((w for w in self.wounds.values() if w.wound > 0), key=lambda w: (-w.wound, w.id or 0))

    def inspire(self) -> int:
        """Grau da moral: um a cada 500 mil do maior dano, até 20."""
        top = max((w.wound for w in self.wounds.values()), default=0)
        return min(INSPIRE_MAX, top // INSPIRE_STEP)

    def battle_reward(self, wound: int) -> int:
        """Ouro (e o mesmo de daru) de uma luta: o dano // ``damage_per_gold``, até ``battle_cap``."""
        return min(self.boss.battle_cap, wound // max(1, self.boss.damage_per_gold))

    def info(self, templates: GameTemplates, character_id: int, now: datetime) -> pb.WorldBossInfoMsg:
        """4174: vida, participantes, os 30 primeiros, o dano de quem recebe e a moral."""
        hero = templates.get("GameHeroTemp", self.boss.hero_id) or {}
        mine = self.wounds.get(character_id)
        msg = pb.WorldBossInfoMsg(
            curHp=self.hp, totalNum=sum(w.wound > 0 for w in self.wounds.values()),
            campaignId=self.boss.campaign_id, totalHp=self.fight.total_hp, myWound=mine.wound if mine else 0,
            grades=int(hero.get("Grades") or 0), currentMillis=int(now.timestamp() * 1000), bufferGrade=self.inspire(),
        )  # fmt: skip
        for w in self.ranking()[:RANKED]:
            msg.woundInfo.add(userId=w.character_id, nickName=w.nickname, wound=w.wound, woundAddation=0, job=w.job)
        return msg


def next_hp(boss: WorldBoss, fight: WorldBossFight) -> int:
    """Vida cheia da próxima janela: cresce se morreu rápido, cai se não morreu (internet: a wiki; % dedução)."""
    if fight.killed_at is not None:
        fast = (fight.killed_at - fight.opened_at).total_seconds() < boss.fast_seconds
        return fight.total_hp * (100 + boss.grow_pct) // 100 if fast else fight.total_hp
    return max(boss.min_hp, fight.total_hp * (100 - boss.shrink_pct) // 100)


def end_rewards(world: World, pool: Pool) -> dict[int, tuple[int, int]]:
    """Ouro e daru do fim por personagem: top 10 da classe, o maior degrau da fração do dano e o último golpe
    (somam: guia da Koram "Players can acquire Beating Reward as well as other rewards")."""
    total = sum(w.wound for w in pool.wounds.values())
    out: dict[int, tuple[int, int]] = {}

    def add(character_id: int, gold: int, daru: int) -> None:
        g, d = out.get(character_id, (0, 0))
        out[character_id] = (g + gold, d + daru)

    ranking = pool.ranking()
    for cls in {job_class(w.job) for w in ranking}:
        for rank, w in enumerate((w for w in ranking if job_class(w.job) == cls), 1):
            for r in world.world_boss_rewards:
                if r.kind == "rank" and r.rank_from <= rank <= r.rank_to:
                    add(w.character_id, r.gold, r.daru)
    shares = sorted((r for r in world.world_boss_rewards if r.kind == "share"), key=lambda r: r.share)
    for w in ranking:
        best = [r for r in shares if total and w.wound / total >= r.share]
        if best:
            add(w.character_id, best[-1].gold, best[-1].daru)
    if pool.fight.killer_id:
        add(pool.fight.killer_id, pool.boss.last_hit_gold, pool.boss.last_hit_daru)
    return out


def milestones(world: World, pool: Pool, character_id: int) -> pb.WorldBossWoundRewardListMsg:
    """4369: os degraus da fração do dano (o cliente tem 3 ícones, ``core.WorldBossReward1..3``)."""
    total, mine = pool.fight.total_hp, pool.wounds.get(character_id)
    msg = pb.WorldBossWoundRewardListMsg()
    shares = sorted((r for r in world.world_boss_rewards if r.kind == "share"), key=lambda r: r.share)
    for i, r in enumerate(shares, 1):
        reached = mine is not None and total > 0 and mine.wound / total >= r.share
        msg.rewardinfo.add(campaignId=pool.boss.campaign_id, rewardid=i, woundmsg=f"Deal {r.share:.1%} of total damage",
                           rewardmsg=f"{r.gold:,} Gold and {r.daru:,} Daru", state=int(reached))  # fmt: skip
    return msg


class Bosses:
    """As janelas abertas, por campanha (só no processo; o estado de verdade está no banco)."""

    def __init__(self) -> None:
        self.pools: dict[int, Pool] = {}
        self._lock = asyncio.Lock()
        self.checked_at: datetime | None = None  # última busca de janelas sem fim pago no banco

    async def pool(
        self, world: World, templates: GameTemplates, characters: CharacterService, campaign_id: int, now: datetime
    ) -> Pool | None:
        """A janela aberta agora do chefe (cria e grava a primeira vez), ou None fora da janela."""
        row, boss = worldboss.boss(templates, campaign_id), world.world_bosses.get(campaign_id)
        if row is None or boss is None or worldboss.state(row, now) != worldboss.OPEN:
            return None
        opened, _ = worldboss.window(row, now)
        async with self._lock:
            pool = self.pools.get(campaign_id)
            if pool is not None and pool.fight.opened_at == opened:
                return pool
            pool = await characters.write(lambda uow: _load(uow, boss, opened))
            self.pools[campaign_id] = pool
            return pool


async def _load(uow: UnitOfWork, boss: WorldBoss, opened: datetime) -> Pool:
    fight = await uow.world_boss.fight(boss.campaign_id, opened)
    if fight is None:
        last = await uow.world_boss.last(boss.campaign_id)
        fight = WorldBossFight(boss.campaign_id, opened, last.next_hp if last and last.next_hp else boss.base_hp)
        await uow.save(fight)
        await uow.flush()
    wounds = await uow.world_boss.wounds(fight.id or 0)
    return Pool(boss, fight, {w.character_id: w for w in wounds})
