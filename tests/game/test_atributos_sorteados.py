"""randomSkill dos equipamentos novos (bag.roll_random_skills): as amostras das capturas."""

from __future__ import annotations

import random
from pathlib import Path

import pytest

from tests.game.harness import logged_in
from tests.test_end_to_end import TEMPLATES
from wartune_server.game import bag

pytestmark = pytest.mark.skipif(not TEMPLATES.exists(), reason="precisa de data/templates")


async def test_padrao_faixa_do_nivel_e_tipos_distintos(tmp_path: Path) -> None:
    async with logged_in(tmp_path, novice=22500) as g:
        t = g.server.services.templates
        assert bag.roll_random_skills(t, 1013103) == [70306, 70406, 70506, 0, 0]  # DefaultSkill (visto)
        assert bag.roll_random_skills(t, 1013002) == [70302, 0, 0, 0, 0]
        bands = bag._bands(t)
        assert bands[702][:2] == [[70201, 70202, 70203], [70204, 70205, 70206]]
        assert bands[706][:2] == [[70604, 70605, 70606], [70607, 70608, 70609, 70610, 70611, 70612]]
        # os vistos caem na faixa do nível: 1080012 (nível 8) 70905/71004; 1030103 (12) 70611, 70304, 70505
        assert {70905, 71004, 70705} <= {s for k, b in bands.items() for s in b[0]}
        assert {70709, 70611, 70908} <= {s for b in bands.values() for s in b[1]}
        assert {70407, 71123, 70509, 70719, 70209} <= {s for b in bands.values() for s in b[2]}  # nível 20 (turco)
        rng = random.Random(7)
        for _ in range(200):
            three = bag.roll_random_skills(t, 1030103, rng)  # RandomSkillCount 3, nível 12
            assert three[3:] == [0, 0] and len({k // 100 for k in three[:3]}) == 3
            assert all(k in bands[k // 100][1] for k in three[:3])
            one = bag.roll_random_skills(t, 1080012, rng)  # RandomSkillCount 1, nível 8
            assert one[1:] == [0] * 4 and one[0] in bands[one[0] // 100][0]
