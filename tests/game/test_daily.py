"""Virada do dia do jogo às 5h (game/daily.py): energia de teleporte cheia, +100 de stamina por dia e poções
do dia zeradas, no login e no 20008 de quem está online."""

from datetime import UTC, datetime
from pathlib import Path

from tests.game.harness import logged_in
from tests.game.test_pvp import body, codes
from tests.game.test_shop import me
from wartune_server.game.castle import energy_max
from wartune_server.protocol.messages import wartune_pb2 as pb
from wartune_server.services.clock import FakeClock

HOUR = 3600


async def test_virada_das_5h_online_enche_energia_e_da_stamina(tmp_path: Path) -> None:
    clock = FakeClock(datetime(2026, 1, 1, 12, tzinfo=UTC))
    async with logged_in(tmp_path, novice=19000, clock=clock) as g:
        snap = me(g)
        c, castle = snap.character, snap.castle
        assert castle is not None and c.reset_day == "2026-01-01"  # o login já virou o dia
        top = energy_max(g.server.services.templates)
        c.weary, c.weary_potions, castle.energy = 50, 120, 100

        g.client.send(20008)
        assert codes(await g.idle()) == [4234]  # mesmo dia: só o relógio

        clock.advance(13 * HOUR + 59 * 60)  # 01:59 UTC = 04:59 em UTC+3: ainda o dia 1
        g.client.send(20008)
        assert codes(await g.idle()) == [4234]

        clock.advance(60)  # 05:00 em UTC+3
        g.client.send(20008)
        got = await g.until(3)
        reset = body(got, 4202, pb.DataResetMsg)
        assert (reset.weary, reset.transEnergy) == (150, top)
        assert body(got, 3, pb.PlayerMsg).wearyLimit == 0

        saved = await g.server.services.characters.snapshot(g.user_id)
        assert saved.castle is not None
        assert (saved.character.weary, saved.character.weary_potions, saved.castle.energy) == (150, 0, top)
        assert saved.character.reset_day == "2026-01-02"


async def test_dias_fora_somam_stamina_ate_o_maximo_e_nao_cortam_o_excesso(tmp_path: Path) -> None:
    clock = FakeClock(datetime(2026, 1, 1, 12, tzinfo=UTC))
    async with logged_in(tmp_path, novice=19000, clock=clock) as g:
        c = me(g).character
        c.weary = 10
        clock.advance(3 * 24 * HOUR)  # três viradas: +300, mas o teto é 200
        g.client.send(20008)
        assert body(await g.until(3), 4202, pb.DataResetMsg).weary == c.weary_limit

        c.weary = c.weary_limit + 50  # acima do máximo: a virada só soma até o teto, nunca tira
        clock.advance(24 * HOUR)
        g.client.send(20008)
        assert body(await g.until(3), 4202, pb.DataResetMsg).weary == c.weary_limit + 50
