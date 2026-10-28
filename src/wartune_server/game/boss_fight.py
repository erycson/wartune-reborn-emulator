"""Chefe do mundo: a vida compartilhada de uma janela, o ranking de dano, a moral e os prêmios do fim.

Todo o servidor bate no mesmo chefe. O dano entra no ``Pool`` dentro do golpe (``Battle._act``, sem await), então
dois golpes nunca levam a mesma vida e só um pode ser o último. O pool vive no processo (``Bosses``) e no banco: a
janela (``WorldBossFight``) e o dano de cada um (``WorldBossWound``), gravados no fim de cada luta; a vida atual é
a cheia menos a soma dos danos, então um restart só perde a luta em curso.

Fontes (docs/boss-eventos.md):
- (cliente) help ``worldboss.view.BaseHelpFrame.helpText``: ouro e Daru por golpe, "HP e tropas não se esgotam",
  e "Defeating the World Boss earns": Lucky Prize (último golpe), Ares Prize (top 10 do dano por classe) e Warrior
  Prize (0,3%/0,5%/0,8% do dano total).
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


# (visto) o 83 do fim por classe (#3236-#3239: job 1 Knight, 2 Archer, 3 Mage; o Dragonhuntr de job 6 é Mage)
CLASS_NAMES = {1: "Knight", 2: "Archer", 0: "Mage"}
CLASS_JOB = {1: 1, 2: 2, 0: 3}  # job_class -> o ``job`` do 83


@dataclass
class Pool:
    """Uma janela aberta de um chefe."""

    boss: WorldBoss
    fight: WorldBossFight
    wounds: dict[int, WorldBossWound] = field(default_factory=dict)  # personagem -> dano
    lock: asyncio.Lock = field(default_factory=asyncio.Lock)  # gravar e pagar o fim, um de cada vez
    dead: dict[int, datetime] = field(default_factory=dict)  # personagem -> quando revive
    timers: dict[int, asyncio.TimerHandle] = field(default_factory=dict)
    told_inspire: int = 0  # o último grau de moral anunciado
    ticker: asyncio.Task[None] | None = None  # o 4174 a cada 8 s para quem está no mapa

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

    def info(self, character_id: int, present: int, now: datetime) -> pb.WorldBossInfoMsg:
        """4174: vida, quantos estão no mapa (``present``; visto #1415 1 ao entrar, #1434 2), os 30 primeiros, o
        dano de quem recebe e a moral. (visto) sem ``grades``."""
        mine = self.wounds.get(character_id)
        msg = pb.WorldBossInfoMsg(
            curHp=self.hp, totalNum=present, campaignId=self.boss.campaign_id, totalHp=self.fight.total_hp,
            myWound=mine.wound if mine else 0, currentMillis=int(now.timestamp() * 1000), bufferGrade=self.inspire(),
        )  # fmt: skip
        for w in self.ranking()[:RANKED]:
            msg.woundInfo.add(userId=w.character_id, nickName=w.nickname, wound=w.wound, woundAddation=0, job=w.job)
        return msg


def next_hp(boss: WorldBoss, fight: WorldBossFight) -> int:
    """Vida cheia da próxima janela: cresce se morreu rápido, cai se não morreu (internet: a wiki; % dedução)."""
    if fight.killed_at is not None:
        # "under 10 minutes" conta do nascimento; ``opened_at`` é o mapa aberto, ``SPAWN_GAP`` antes
        fast = (fight.killed_at - fight.opened_at - worldboss.SPAWN_GAP).total_seconds() < boss.fast_seconds
        return fight.total_hp * (100 + boss.grow_pct) // 100 if fast else fight.total_hp
    return max(boss.min_hp, fight.total_hp * (100 - boss.shrink_pct) // 100)


@dataclass(frozen=True)
class Prize:
    """Um prêmio do fim, um correio cada (visto: #3260, Apollo e Warrior em correios separados)."""

    character_id: int
    kind: str  # "apollo" (top 10 da classe), "warrior" (fração do dano), "lucky" (último golpe)
    gold: int
    daru: int
    rank: int = 0  # apollo: a posição na classe
    cls: int = 0  # apollo: job_class


def end_prizes(world: World, pool: Pool) -> list[Prize]:
    """Os prêmios do fim: Apollo (top 10 da classe), Warrior (o maior degrau da fração do dano) e Lucky (o último
    golpe); somam (guia da Koram "Players can acquire Beating Reward as well as other rewards"). Só com o chefe
    morto ("Defeating the World Boss earns", help do cliente): a janela que fecha no ``StopTime`` fica só com o ouro
    e o Daru de cada golpe. (visto) #3260: 3º Mage = 240k/240k, 1,22% do dano = 180k/180k."""
    if not pool.fight.killer_id:
        return []
    out: list[Prize] = []
    total = sum(w.wound for w in pool.wounds.values())
    ranking = pool.ranking()
    for cls in sorted({job_class(w.job) for w in ranking}):
        for rank, w in enumerate((w for w in ranking if job_class(w.job) == cls), 1):
            for r in world.world_boss_rewards:
                if r.kind == "rank" and r.rank_from <= rank <= r.rank_to:
                    out.append(Prize(w.character_id, "apollo", r.gold, r.daru, rank, cls))
    shares = sorted((r for r in world.world_boss_rewards if r.kind == "share"), key=lambda r: r.share)
    for w in ranking:
        best = [r for r in shares if total and w.wound / total >= r.share]
        if best:
            out.append(Prize(w.character_id, "warrior", best[-1].gold, best[-1].daru))
    out.append(Prize(pool.fight.killer_id, "lucky", pool.boss.last_hit_gold, pool.boss.last_hit_daru))
    return out


def end_rewards(world: World, pool: Pool) -> dict[int, tuple[int, int]]:
    """Ouro e daru do fim somados por personagem."""
    out: dict[int, tuple[int, int]] = {}
    for p in end_prizes(world, pool):
        g, d = out.get(p.character_id, (0, 0))
        out[p.character_id] = (g + p.gold, d + p.daru)
    return out


class Bosses:
    """As janelas abertas, por campanha (só no processo; o estado de verdade está no banco)."""

    def __init__(self) -> None:
        self.pools: dict[int, Pool] = {}
        self._lock = asyncio.Lock()
        self.checked_at: datetime | None = None  # última busca de janelas sem fim pago no banco
        self.told_at: datetime | None = None  # última conferência dos avisos e do nascimento (``boss_clock``)

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

    def defeated(self, templates: GameTemplates, now: datetime) -> set[int]:
        """Chefes já mortos (fim pago) na janela de hoje: o 4182 os mostra encerrados."""
        out = set()
        for campaign_id, pool in self.pools.items():
            row = worldboss.boss(templates, campaign_id)
            if row is not None and pool.fight.settled and pool.fight.opened_at == worldboss.window(row, now)[0]:
                out.add(campaign_id)
        return out

    async def stale(self, world: World, characters: CharacterService) -> list[Pool]:
        """Janelas sem fim pago no banco que não estão em memória (o servidor reiniciou ou a janela virou)."""
        known = {p.fight.id for p in self.pools.values()}

        async def query(uow: UnitOfWork) -> list[Pool]:
            out = []
            for fight in await uow.world_boss.open_fights():
                boss = world.world_bosses.get(fight.campaign_id)
                if boss is not None and fight.id not in known:
                    wounds = await uow.world_boss.wounds(fight.id or 0)
                    out.append(Pool(boss, fight, {w.character_id: w for w in wounds}))
            return out

        return await characters.read(query)


async def _load(uow: UnitOfWork, boss: WorldBoss, opened: datetime) -> Pool:
    fight = await uow.world_boss.fight(boss.campaign_id, opened)
    if fight is None:
        last = await uow.world_boss.last(boss.campaign_id)
        fight = WorldBossFight(boss.campaign_id, opened, last.next_hp if last and last.next_hp else boss.base_hp)
        await uow.save(fight)
        await uow.flush()
    wounds = await uow.world_boss.wounds(fight.id or 0)
    return Pool(boss, fight, {w.character_id: w for w in wounds})
