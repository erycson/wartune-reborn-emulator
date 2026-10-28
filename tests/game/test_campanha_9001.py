"""Campanha em grupo 9001 (Claristun, mapa 2011): o Start da sala, a entrada do dia, o 5038 e o baú VIP."""

from __future__ import annotations

from pathlib import Path

from tests.game.harness import Game, logged_in
from wartune_server.protocol.messages import wartune_pb2 as pb

READY = 19000


async def _room(g: Game) -> pb.RoomMsg:
    g.client.send(5023, pb.RoomReqMsg(capacity=4))
    room = pb.RoomMsg.FromString(next(p.body for p in await g.idle() if p.code == 12))
    g.client.send(5034, pb.RoomReqMsg(roomId=room.roomId, campaignId=9001))
    await g.idle()
    return room


async def test_start_da_sala_entra_e_gasta_a_entrada(tmp_path: Path) -> None:
    """(só turco: exp_kitabi #24-#40) 24, 125 com a sala inteira, 140, 21, 3, 150, 4903, 3, 4165, 150, 150, 127,
    130, 143 e o 83 das entradas; sem estamina."""
    async with logged_in(tmp_path, novice=READY) as g:
        room = await _room(g)
        session = g.server.online.get(g.user_id)
        assert session is not None and session.snapshot is not None
        weary = session.snapshot.character.weary
        g.client.send(5039, pb.CampaignReqMsg(paraInt2=9001, paraBool1=False))
        got = await g.until(83)
        codes = [p.code for p in got]
        # 4902 e 4903 só saem com cartas (o personagem novo não tem)
        assert codes == [24, 125, 140, 21, 3, 150, 3, 4165, 150, 150, 127, 130, 143, 83]
        ready = pb.PlayerReadyRspMsg.FromString(got[0].body).readyState[0]
        assert (ready.playerId, ready.readyState) == (g.user_id, 2)
        created = pb.RoomCreatedMsg.FromString(got[1].body).room
        assert (created.roomId, created.campaignId, created.name, created.roomState) == (
            room.roomId,
            2011,
            "Claristun",
            3,
        )
        me = pb.RoomEnterMsg.FromString(got[3].body).player[0]
        assert (me.roomId, me.count, me.playerState) == (room.roomId, 1, 2)
        text = pb.ChatChannelMsg.FromString(got[-1].body).encodeMsg
        assert text == "Entered [Claristun]. You still have 0/1 multi-player dungeon attempts available."
        c = session.snapshot.character
        assert (c.weary, c.multi_copy_count) == (weary, 0)
        assert session.campaign is not None and session.campaign.run is not None and session.campaign.run.rewarded
        g.client.send(5038, pb.CampaignReqMsg(paraInt1=2011))
        army = pb.SystemArmyMsg.FromString((await g.until(20))[-1].body)
        assert (list(army.heroTemplated), list(army.soldierTemplated)) == ([3011], [4012, 4011])


async def test_sem_entrada_do_dia_entra_sem_premio(tmp_path: Path) -> None:
    """(cliente) ``paraBool1`` = ``isNoGet``: a entrada não gasta e a campanha não dá prêmio (``RoomRightView.incomePrompt``)."""
    async with logged_in(tmp_path, novice=READY) as g:
        await _room(g)
        g.client.send(5039, pb.CampaignReqMsg(paraInt2=9001, paraBool1=True))
        got = await g.until(83)
        assert pb.ChatChannelMsg.FromString(got[-1].body).encodeMsg.endswith(
            " 1/1 multi-player dungeon attempts available."
        )
        session = g.server.online.get(g.user_id)
        assert session is not None and session.campaign is not None and session.campaign.run is not None
        assert not session.campaign.run.rewarded


async def test_bau_vip_gasta_kyanite(tmp_path: Path) -> None:
    """Baú VIP (201110): o 29 em inglês, e o 5033 gasta 2000 Kyanite (o texto turco) e dá as chaves."""
    async with logged_in(tmp_path, novice=READY) as g:
        await _room(g)
        g.client.send(5039, pb.CampaignReqMsg(paraInt2=9001, paraBool1=False))
        await g.until(83)
        session = g.server.online.get(g.user_id)
        assert session is not None and session.snapshot is not None
        session.snapshot.character.crystals = 5000
        g.client.send(5125, pb.CampaignReqMsg(paraInt1=201110, paraBool1=True))
        confirm = pb.CampaignConfirmMsg.FromString((await g.until(29))[-1].body)
        assert confirm.body == "Are you sure you want to spend 2000 Kyanite to open this VIP Treasure Chest?"
        g.client.send(5033, pb.CampaignReqMsg(paraInt1=confirm.mapId, paraInt2=201110, paraBool1=True))
        got = await g.until(83)
        assert pb.ChatChannelMsg.FromString(got[-1].body).encodeMsg == "Received: Skeleton Key x2"
        assert session.snapshot.character.crystals == 3000
