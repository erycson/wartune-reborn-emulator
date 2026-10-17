from pathlib import Path

from tests.game.harness import logged_in
from wartune_server.game.handlers.login import player_info
from wartune_server.protocol import Packet
from wartune_server.protocol.messages import wartune_pb2 as pb


def _vp(got: list[Packet], op: int) -> int:
    [reply] = [pb.VicePasswordMsg.FromString(p.body) for p in got if p.code == 4696]
    assert reply.opType == op
    return reply.result


async def test_vice_password_set_check_change_and_reset(tmp_path: Path) -> None:
    async with logged_in(tmp_path, novice=19000) as g:
        c = g.client
        c.send(8806, pb.VicePasswordMsg(opType=2, inputPass="123456", newPass="123456"))  # sequência: recusa
        assert _vp(await g.idle(), 2) == 0
        c.send(8806, pb.VicePasswordMsg(opType=2, inputPass="246810", newPass="246811"))  # confirmação errada
        assert _vp(await g.idle(), 2) == 0
        c.send(8806, pb.VicePasswordMsg(opType=2, inputPass="246810", newPass="246810"))
        assert _vp(await g.idle(), 2) == 1
        c.send(8806, pb.VicePasswordMsg(opType=2, inputPass="135790", newPass="135790"))  # já tem senha
        assert _vp(await g.idle(), 2) == 0

        c.send(8806, pb.VicePasswordMsg(opType=1, inputPass="000000"))
        assert _vp(await g.idle(), 1) == 0
        c.send(8806, pb.VicePasswordMsg(opType=1, inputPass="246810"))
        assert _vp(await g.idle(), 1) == 1

        c.send(8806, pb.VicePasswordMsg(opType=3, prePass="999999", inputPass="135790", newPass="135790"))
        assert _vp(await g.idle(), 3) == 0
        c.send(8806, pb.VicePasswordMsg(opType=3, prePass="246810", inputPass="135790", newPass="135790"))
        assert _vp(await g.idle(), 3) == 1

        c.send(8806, pb.VicePasswordMsg(opType=4))
        assert _vp(await g.idle(), 4) == 1
        saved = await g.server.services.characters.snapshot(g.user_id)
        assert saved.character.vice_password and "135790" not in saved.character.vice_password  # hash
        assert saved.character.vice_reset_at is not None

        g2 = await g.connect()  # o PlayerMsg do login leva o estado
        session = g2.server.online.get(g.user_id)
        assert session is not None and session.snapshot is not None
        player = player_info(session, session.snapshot)
        assert (player.hasVicePassword, player.isDuringToResetTime) == (1, 1)


async def test_qte_guide_check_send_and_heartbeats(tmp_path: Path) -> None:
    async with logged_in(tmp_path, novice=19000) as g:
        c = g.client
        c.send(8302)
        c.send(20010)  # batida do acelerador: o oficial não responde
        c.send(8516)  # sem captcha: sem resposta
        c.send(8524)
        got = await g.idle()
        assert [p.code for p in got] == [4420]
        assert pb.CheckSend.FromString(got[0].body).canSend == -1
        saved = await g.server.services.characters.snapshot(g.user_id)
        assert saved.character.qte_guide == 1

        c.send(8260, pb.PlayerAASReqMsg(cardName="Li Lei", cardId="11010519900307123X"))
        [aas] = [pb.PlayerAASRspMsg.FromString(p.body) for p in await g.idle() if p.code == 4172]
        assert aas.result and aas.age >= 18
        c.send(8260, pb.PlayerAASReqMsg(cardName="Li Lei", cardId="123"))
        [aas] = [pb.PlayerAASRspMsg.FromString(p.body) for p in await g.idle() if p.code == 4172]
        assert not aas.result
