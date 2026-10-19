"""Painel "Current map BOSS info" da cidade externa (9525 -> 4938).

Lista: os chefes (``bossType`` 3) vivos do mapa, de ``monsters.on_map``. (só turco: o bosslist do mapa
2 na transfer_kampi_sistemi traz 5 monstros, todos de ``Property1`` 3, e o 210127, ``bossType`` 2, do 4129 da
mesma sessão fica de fora). x e y em tiles (o radar do cliente faz x * 20). A instância do castelo vem vazia
(inglês #526: 4938 com count1..3 em 0): não está em ``world_monster_counts``.
"""

from __future__ import annotations

from datetime import datetime

from ..domain.models import Character
from ..domain.world import World
from ..protocol.messages import wartune_pb2 as pb
from ..templates.repository import GameTemplates
from . import monsters


def boss_msg(
    world: World,
    templates: GameTemplates,
    wilds: monsters.Wilds,
    c: Character,
    map_id: int,
    killed: set[int],
    now: datetime,
) -> pb.MapBossMsg:
    """4938. ``count1`` a ``count3``: abates do dia que contaram (o cliente mostra "{0}/{1}" com o
    ``WorldMapKill``). Os chefes abatidos ficam na lista com ``type`` 0 ("(Killed)") e os em luta com 4
    (language ``bossinfo.bossStatus0``/``bossStatus4``)."""
    bosses = []
    for m in monsters.on_map(world, templates, map_id, now):
        if m.boss_type == monsters.CHIEF:
            row = templates.get("MapPhysicsTempInfos", m.template_id) or {}
            name, grade = row.get("MapPhysicsTempName", ""), int(row.get("Grades", 0))
            bosses.append(pb.BossMsg(bossName=name, grade=grade, type=wilds.state(m, killed), x=m.x, y=m.y))
    n, e, k = monsters.kills(c)
    return pb.MapBossMsg(
        count1=n,
        count2=e,
        count3=k,
        bosslist=bosses,
        leftBossTime=monsters.refresh_left(templates, now),
        leftFogTime=wilds.fog_left(map_id, now),
    )
