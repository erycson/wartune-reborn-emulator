"""Chefes do mapa (9525 -> 4938, painel "Current map BOSS info" da cidade externa). Os pontos de cada mapa
vêm do catálogo do mundo (``map_boss_spawns``).

Relógio (visto): transfer #8/#10 (mapa 2, 4828 s às 17:39:31 UTC) e cevre #3/#9/#43/#44 (instância do
castelo, 5775 s às 17:23:44 UTC) caem no mesmo instante, 2026-05-21 19:00:00 UTC (22:00 no fuso do jogo),
em mapas diferentes. (dedução) é um relógio do mundo de 2 h nas horas pares do fuso do jogo: RefreshTime
7200 nos chefes (MapPhysicsTempInfos MasterType 21). As duas capturas são da mesma conta.

Lista (visto): o bosslist do mapa 2 na transfer; x e y em tiles (o radar do cliente faz x * 20). A instância
do castelo vem vazia (cevre). ponytail: mapas 1, 3, 4 e 5 sem pontos (precisa de captura); a lista não muda
no refresh (sem captura de dois ciclos). O 4129 do mapa 2 (transfer #14) traz outro chefe (210127, bossType
2) fora do bosslist: o painel não é a lista inteira dos chefes do mapa.
"""

from __future__ import annotations

from datetime import datetime

from ..domain import gameday
from ..domain.world import World
from ..protocol.messages import wartune_pb2 as pb
from ..templates.repository import GameTemplates

BOSS_PERIOD = 7200
BOSS_ALIVE = 1  # BossMsg.type visto; 0 o cliente pinta como morto e esconde o radar


def boss_left(now: datetime) -> int:
    """Segundos até o próximo refresh dos chefes. Nunca 0: com 0 o cliente (``coolDownBossUpdate``) pede
    o 9525 de novo, e a cada segundo se a resposta voltar 0."""
    local = gameday.local(now)
    into = (local - local.replace(hour=0, minute=0, second=0, microsecond=0)).total_seconds() % BOSS_PERIOD
    return max(1, int(BOSS_PERIOD - into))


def boss_msg(world: World, templates: GameTemplates, map_id: int, now: datetime) -> pb.MapBossMsg:
    """4938. ``count1`` a ``count3`` (monstros, elites e chefe do dia) ficam 0: não há monstro do mapa
    nem luta contra chefe que conte. Névoa (``leftFogTime``) sem captura: 0, como nas duas."""
    bosses = []
    for spawn in world.bosses_on(map_id):
        row = templates.get("MapPhysicsTempInfos", spawn.template_id) or {}
        name, grade = row.get("MapPhysicsTempName", ""), int(row.get("Grades", 0))
        bosses.append(pb.BossMsg(bossName=name, grade=grade, type=BOSS_ALIVE, x=spawn.x, y=spawn.y))
    return pb.MapBossMsg(count1=0, count2=0, count3=0, bosslist=bosses, leftBossTime=boss_left(now), leftFogTime=0)
