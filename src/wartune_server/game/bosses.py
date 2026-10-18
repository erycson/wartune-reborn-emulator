"""Painel "Current map BOSS info" da cidade externa (9525 -> 4938).

Lista: os chefes (``bossType`` 3) vivos do mapa, de ``monsters.on_map``. (visto) o bosslist do mapa 2 na
transfer traz 5 monstros, todos de ``Property1`` 3, e o 210127 (``bossType`` 2) do 4129 da mesma sessão fica
de fora. x e y em tiles (o radar do cliente faz x * 20). A instância do castelo vem vazia (cevre): não está
em ``world_monster_counts``.
"""

from __future__ import annotations

from datetime import datetime

from ..domain.models import Character
from ..domain.world import World
from ..protocol.messages import wartune_pb2 as pb
from ..templates.repository import GameTemplates
from . import monsters

BOSS_ALIVE = 1  # BossMsg.type visto; 0 o cliente pinta como morto e esconde o radar


def boss_msg(world: World, templates: GameTemplates, c: Character, map_id: int, now: datetime) -> pb.MapBossMsg:
    """4938. ``count1`` a ``count3`` (monstros, elites e chefes abatidos hoje) ficam 0: não há luta com
    monstro que conte."""
    bosses = []
    for m in monsters.on_map(world, templates, map_id, now):
        if m.boss_type == monsters.CHIEF:
            row = templates.get("MapPhysicsTempInfos", m.template_id) or {}
            name, grade = row.get("MapPhysicsTempName", ""), int(row.get("Grades", 0))
            bosses.append(pb.BossMsg(bossName=name, grade=grade, type=BOSS_ALIVE, x=m.x, y=m.y))
    return pb.MapBossMsg(
        count1=0,
        count2=0,
        count3=0,
        bosslist=bosses,
        leftBossTime=monsters.refresh_left(templates, now),
        leftFogTime=monsters.fog_left(c, map_id, now),
    )
