"""Guerra de guildas (mapa 4501): o par de guildas, a janela, as torres, o placar e o fim.

Estado só em memória (como o chefe do mundo e o campo de batalha); o prêmio é gravado no personagem. Fonte principal:
a sessão 20261026-225632-1 #2464-#6452 (uma guerra inteira, vista do lado vermelho), citada em cada constante.

- O par: as 8 guildas de maior poder; a ``i``-ª (0-7) tem ``group1`` = ``i % 4 + 1`` e enfrenta a do mesmo grupo
  (visto #6451: 1ª x 5ª, 2ª x 6ª...); a de cima é a vermelha (lado 1), a outra a azul (lado 2).
- Cada lado tem uma Ward Tower (masterType 141, ``param1`` = lado) de 60 milhões de vida; o placar de um lado é o dano
  que ele fez na torre inimiga dividido por 10.000, contado no tique de 33 s.
- As 4 Mystery Towers (masterType 61) mudam o dano que a torre inimiga recebe: x0,5 com 1, x1 com 2, x1,5 com 3, x2
  com 4 (os textos 111 de #2705-#2758).
- Quem perde a luta na torre fica morto (4175 state 1) até o tique seguinte; quem defende uma Mystery Tower ganha 5.000
  de "ferida" (``castleWound`` do 4460) por tique.
- Vence quem abre 4.000 pontos de vantagem (#6249), derruba a torre inimiga (dedução) ou lidera às 21:00.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any

WAR_MAP = 4501  # (visto #2467) 125 campaignId
RED, BLUE = 1, 2  # lado = ``param1`` dos nós; o vermelho entra no 450101 (20,100), o azul no 450103 (373,102, #3868)
ENTRY, GATE, CAMP, WARD, MYSTERY, CHARIOT = 40, 53, 121, 141, 61, 151  # masterType dos nós do 127 (#2470)
GROUPS = 4  # (visto #6451) group1 1-4, duas guildas por grupo
TOWER_HP = 60_000_000  # (visto #2475) 4450 totalHp das duas Ward Towers
POINT_DAMAGE = 10_000  # (visto) placar = dano // 10000: 397.884 -> 39 (#2799), 5.041.588 -> 504 (#3041)
WIN_LEAD = 4000  # (visto #6249) "having earned 4,000 more points"
TICK = 33  # (visto) 4439 a cada 33 s (#2799, #2829 ... #6250)
DEFEND_WOUND = 5000  # (visto #5978 -> #6037) quem só defende ganha 5.000 de ferida por tique
# (cliente) language gvg.view.ready.ApplyForBattleView.time03/time04: a fase da guerra vai das 20:00 às 21:00
OPEN_HOUR, END_HOUR = 20, 21
# (dedução) o mapa abre às 20:00 e a barreira cai 5 min depois: a entrada com 108 s de espera (#2476) e o aviso dos
# 20 min (#4884) 1.008 s depois dela batem com a abertura 192 s antes da entrada
PREP = timedelta(minutes=5)
LATE = timedelta(minutes=20)  # (visto #4884) "The Guild Battle has lasted for 20 mins..."
WARN_LEFT = 10  # (visto #2546) o 2º 4457 sai com 10 s
# torres -> fator do dano na torre inimiga (visto #2705-#2758); TODO(inventado): sem torre, o mesmo x0,5 de 1 torre
FACTOR = {0: 0.5, 1: 0.5, 2: 1.0, 3: 1.5, 4: 2.0}
EFFECT = {1: "decreased 50%", 2: "is normal", 3: "increased 50%", 4: "increased 100%"}
ALIVE, DEAD, DEFENDING = 0, 1, 4  # 4175 PlayerStateMsg.state (visto #2779, #2988, #3038)
OWNED = {RED: 16, BLUE: 17}  # 128 nodeState da Mystery Tower tomada (visto #2706 e #4067), ``param1`` = lado
INSPIRATION, CALL_TO_ARMS, INVINCIBLE, BLESSING = 1, 2, 3, 4  # templateId dos buffs do 4440 (#2472)
BLESSING_HEAL = 0.3  # (visto #2472) "Restore 30% HP of the Ward Tower's Max HP."
NO_DATE = "1969-12-31 16:00:00"  # (visto #2472) param1 do buff nunca usado


def pairs(top: list[int]) -> dict[int, tuple[int, int, int]]:
    """Guilda -> (adversária, lado, grupo) das 8 de maior poder (``top`` em ordem). Sem par, a guilda fica de fora."""
    found: dict[int, tuple[int, int, int]] = {}
    for i in range(min(len(top), 2 * GROUPS) - GROUPS):
        red, blue = top[i], top[i + GROUPS]
        found[red], found[blue] = (blue, RED, i + 1), (red, BLUE, i + 1)
    return found


def group_of(top: list[int], guild_id: int) -> int:
    """``group1`` do 4441 (visto #6451): a posição no grupo, mesmo sem adversária."""
    return top.index(guild_id) % GROUPS + 1 if guild_id in top else 0


def window(now: datetime) -> tuple[datetime, datetime]:
    """(abertura, fim) da guerra de hoje. TODO(inventado): todo dia (a captura foi numa segunda-feira)."""
    day = now.replace(hour=0, minute=0, second=0, microsecond=0)
    return day + timedelta(hours=OPEN_HOUR), day + timedelta(hours=END_HOUR)


@dataclass
class Side:
    guild_id: int
    name: str
    side: int
    dealt: int = 0  # dano na Ward Tower inimiga
    score: int = 0  # o do último tique (4439)
    hp: int = TOWER_HP  # a própria Ward Tower
    inspired_at: datetime | None = None  # buff 1: a próxima luta de cada membro depois disso começa com fúria
    buffs: dict[int, tuple[int, datetime]] = field(default_factory=dict)  # templateId -> (usos, último uso)


@dataclass
class Wound:
    nickname: str
    job: int
    wound: int = 0


@dataclass
class War:
    """Uma partida entre duas guildas. ``owner``: Mystery Tower (campDataId) -> lado (0 = de ninguém)."""

    red: Side
    blue: Side
    opened: datetime
    owner: dict[int, int] = field(default_factory=dict)
    defenders: dict[int, set[int]] = field(default_factory=dict)  # Mystery Tower -> jogadores
    wounds: dict[int, Wound] = field(default_factory=dict)
    dead: set[int] = field(default_factory=set)
    raged: dict[int, datetime] = field(default_factory=dict)  # jogador -> o ``inspired_at`` já usado
    last_tick: datetime | None = None
    late: bool = False  # o aviso dos 20 min já saiu
    warned: bool = False  # o 4457 dos 10 s já saiu
    gates_open: bool = False
    winner: int = 0  # lado vencedor; 0 = em curso
    settled: bool = False
    wounds_sent: Any = None  # o último 4460/4450 mandado (só manda de novo se mudou)
    wounds_at: datetime | None = None
    ticker: Any = None  # asyncio.Task do relógio da partida

    @property
    def gates_at(self) -> datetime:
        return self.opened + PREP

    @property
    def ends_at(self) -> datetime:
        return self.opened + timedelta(hours=END_HOUR - OPEN_HOUR)

    def sides(self) -> tuple[Side, Side]:
        return self.red, self.blue

    def side(self, n: int) -> Side:
        return self.red if n == RED else self.blue

    def of(self, guild_id: int) -> Side | None:
        return next((x for x in self.sides() if x.guild_id == guild_id), None)

    def enemy(self, me: Side) -> Side:
        return self.blue if me is self.red else self.red

    def towers(self, n: int) -> int:
        return sum(1 for o in self.owner.values() if o == n)

    def factor(self, n: int) -> float:
        return FACTOR[min(self.towers(n), 4)]

    def wound_of(self, player_id: int, nickname: str, job: int) -> Wound:
        return self.wounds.setdefault(player_id, Wound(nickname, job))

    def hit(self, me: Side, player_id: int, nickname: str, job: int, value: int) -> int:
        """Golpe de ``me`` na Ward Tower inimiga: o fator das Mystery Towers, a vida que resta; devolve o tirado."""
        enemy = self.enemy(me)
        taken = min(enemy.hp, max(0, int(value * self.factor(me.side))))
        enemy.hp -= taken
        me.dealt += taken
        self.wound_of(player_id, nickname, job).wound += taken
        if enemy.hp <= 0 and not self.winner:
            self.winner = me.side  # (dedução) a torre caída acaba a guerra
        return taken

    def defending(self, player_id: int) -> int:
        """A Mystery Tower que o jogador defende (0 = nenhuma)."""
        return next((camp for camp, who in self.defenders.items() if player_id in who), 0)

    def stop_defending(self, player_id: int) -> int:
        camp = self.defending(player_id)
        if camp:
            self.defenders[camp].discard(player_id)
        return camp

    def defend(self, camp: int, player_id: int, me: Side, enemies: set[int], cap: int) -> str:
        """Entra na defesa: ``full`` (lotada), ``contested`` (TODO(inventado): com inimigo defendendo a torre não muda
        de dono), ``taken`` (passou a ser de ``me``) ou ``ok``."""
        who = self.defenders.setdefault(camp, set())
        if player_id not in who and len(who) >= cap:
            return "full"
        self.stop_defending(player_id)
        who.add(player_id)
        if self.owner.get(camp, 0) == me.side:
            return "ok"
        if who & enemies:
            return "contested"
        self.owner[camp] = me.side
        return "taken"

    def tick(self, now: datetime) -> list[int]:
        """Placar, ferida de quem defende e o fim por vantagem; devolve quem reviveu."""
        self.last_tick = now
        for x in self.sides():
            x.score = x.dealt // POINT_DAMAGE
        for who in self.defenders.values():
            for pid in who:
                if pid in self.wounds:
                    self.wounds[pid].wound += DEFEND_WOUND
        lead = self.red.score - self.blue.score
        if not self.winner and abs(lead) >= WIN_LEAD:
            self.winner = RED if lead > 0 else BLUE
        revived = sorted(self.dead)
        self.dead.clear()
        return revived

    def time_over(self) -> None:
        """21:00: vence quem tem mais pontos. TODO(inventado): empate fica com a vermelha (a de mais poder)."""
        if not self.winner:
            self.winner = RED if self.red.score >= self.blue.score else BLUE

    def can_buff(self, me: Side, template: int, uses: int, cd: int, now: datetime) -> bool:
        used, at = me.buffs.get(template, (0, None))
        return used < uses and (at is None or (now - at).total_seconds() >= cd)

    def use_buff(self, me: Side, template: int, now: datetime) -> None:
        used, _ = me.buffs.get(template, (0, None))
        me.buffs[template] = (used + 1, now)
        if template == INSPIRATION:
            me.inspired_at = now
        elif template == BLESSING:
            me.hp = min(TOWER_HP, me.hp + int(TOWER_HP * BLESSING_HEAL))

    def rage(self, me: Side, player_id: int) -> bool:
        """Buff 1: a primeira luta do jogador depois da compra começa com a fúria; uma vez por compra."""
        if me.inspired_at is None or self.raged.get(player_id) == me.inspired_at:
            return False
        self.raged[player_id] = me.inspired_at
        return True
