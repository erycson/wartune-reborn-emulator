"""Pacotes do login para sistemas que o servidor não tem (migração 0078), na ordem do oficial
(tutorial_en, oficial_20261023-215937-1)."""

from __future__ import annotations

from pathlib import Path

import pytest

from tests.game.harness import logged_in
from tests.test_end_to_end import TEMPLATES
from wartune_server.protocol.messages import wartune_pb2 as pb

pytestmark = pytest.mark.skipif(not TEMPLATES.exists(), reason="precisa de data/templates")


def _codes(got: list) -> list[int]:  # type: ignore[type-arg]
    return [p.code for p in got]


async def test_pacotes_do_login(tmp_path: Path) -> None:
    async with logged_in(tmp_path, novice=33000) as g:
        g.client.send(8224, pb.PlayerDataMsg(user=True))
        tail = await g.until(4725)  # o fim do 8224 user, depois do 4151 (215937 #104-#110)
        assert [c for c in _codes(tail) if c in (4392, 4471, 4900, 4725)] == [4392, 4471, 4900, 4725]
        honor = pb.SimplePropertyMsg.FromString(next(p.body for p in tail if p.code == 4471))
        assert (honor.param1, honor.param2, honor.HasField("param3")) == (0, 6000, False)

        g.client.send(8224, pb.PlayerDataMsg(army=True, tower=True, questionnarie=True))
        got = _codes(await g.idle())
        assert got.index(100) < got.index(4438) < got.index(4544)
        assert [c for c in got if c in (4912, 4373, 4428)] == [4912, 4373, 4428]

        g.client.send(8224, pb.PlayerDataMsg(active=True, switches=True))
        got = await g.idle()
        assert _codes(got) == [4251, 4393, 4422]
        assert len(pb.ActiveRspMsg.FromString(got[0].body).activeRspInfo) == 9
        switches = {x.switchType: x.isOpen for x in pb.SwitchInfoListMsg.FromString(got[2].body).switches}
        assert len(switches) == 67 and switches[3007] and switches[5]  # pet challenge e terra secreta abertos
        assert not switches[3006] and not switches[3031]  # mina e estrada dourada: fechadas aqui (closed_switches)

        g.client.send(8271)
        got = await g.idle()
        assert _codes(got) == [4182, 4451, 4637, 462, 4741, 4683, 4685]
        assert got[3].body == bytes.fromhex("3800")  # igual ao oficial (#121)
