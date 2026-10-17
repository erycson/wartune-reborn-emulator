"""Cliente falso fazendo o caminho do Loading.swf até o LoginState (marco 1)."""

from __future__ import annotations

import asyncio
import hashlib
import os
import re
from pathlib import Path
from urllib.parse import quote_from_bytes

import pytest
from aiohttp.test_utils import TestClient, TestServer

from wartune_server.app import GameServerApp, build_services
from wartune_server.config import Settings
from wartune_server.net.servers import start_tcp
from wartune_server.protocol import Packet, PacketDecoder, StreamCipher
from wartune_server.protocol.messages import wartune_pb2 as pb

DATA = Path("data/overlay")
pytestmark = pytest.mark.skipif(
    not (DATA / "xml/tempinfos.xml").exists(), reason="precisa de data/overlay (tools/export_captures.py)"
)

INIT_CODES = {4153, 4154, 4155, 4156, 4157, 4160, 4173, 4176, 4233, 4245}  # LoginInitDataAccept


class FakeFlashClient:
    def __init__(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        self.reader, self.writer = reader, writer
        self.out, self.decoder = StreamCipher(), PacketDecoder(StreamCipher())

    def send(self, code: int, msg: object | None = None) -> None:
        body = msg.SerializeToString() if msg is not None else b""  # type: ignore[attr-defined]
        self.writer.write(self.out.encrypt(Packet(code, body).encode()))

    def rekey(self, key: bytes) -> None:
        self.out.reset(key)
        self.decoder.cipher.reset(key)

    async def until(self, code: int) -> list[Packet]:
        got: list[Packet] = []
        while True:
            while (p := self.decoder.next_packet()) is not None:
                got.append(p)
                if p.code == code:
                    return got
            data = await asyncio.wait_for(self.reader.read(65536), 5)
            assert data, f"conexão fechada esperando {code}; recebidos {[g.code for g in got]}"
            self.decoder.feed(data)


async def test_new_account_reaches_login_state(tmp_path: Path) -> None:
    settings = Settings(
        database_url=f"sqlite+aiosqlite:///{tmp_path / 'e2e.db'}",
        rsa_key_file=tmp_path / "rsa.pem",
        log_dir=tmp_path / "logs",
        _env_file=None,  # type: ignore[call-arg]
    )
    services = await build_services(settings)
    server = GameServerApp(settings, services)
    tcp = await start_tcp(server.acceptor, "127.0.0.1", 0)
    port = tcp.sockets[0].getsockname()[1]
    http = TestClient(TestServer(server.http_app))
    await http.start_server()
    try:
        # portal
        assert (await (await http.post("/api/register", data={"username": "maga", "password": "segredo1"})).json())["ok"]
        portal = await (await http.post("/api/login", data={"username": "maga", "password": "segredo1"})).json()
        fv = portal["flashvars"]
        assert "Loading.swf?user=maga&key=" in portal["swf_url"]

        config = await (await http.get("/client/config.xml")).text()
        assert services.keys.modulus_b64 in config and f"<NODE site='{settings.site}'>" in config
        assert re.search(r'<SocktPath value="127\.0\.0\.1" SocketPort="5000"', config)

        sel = await (await http.get("/loginselectlist", params={"username": "maga", "site": fv["site"]})).text()
        assert "<Item" not in sel

        temp = "7654321"
        plain = f"{quote_from_bytes(b'maga', safe='')}|{fv['key']}|{temp}|0".encode()
        login = await (await http.post("/login", data={"p": services.keys.encrypt_b64(plain), "site": fv["site"]})).text()
        user_id = int(re.search(r'userId="(\d+)"', login).group(1))  # type: ignore[union-attr]
        assert user_id > 0 and 'value="true"' in login

        key = hashlib.md5(temp.encode()).hexdigest()
        reg = await (await http.post("/visualizeregister", data={
            "userid": user_id, "username": "maga", "nickname": "Maga", "sex": 0, "camp": 1, "icon": 6, "key": key,
        })).text()
        assert 'value="true"' in reg and 'type="0"' in reg, reg
        novice = await http.post("/updateplayernovice", data={"op": 1, "userid": user_id, "noviceprocess": 0, "key": key})
        assert await novice.text() == "19000"  # skip_tutorial

        sel = await (await http.get("/loginselectlist", params={"username": "maga"})).text()
        assert f'ID="{user_id}" Active="true"' in sel

        # socket
        client = FakeFlashClient(*await asyncio.open_connection("127.0.0.1", port))
        ekeys = os.urandom(8)
        client.send(20001, pb.LoginReqMsg(key=key, ekeys=list(ekeys)))
        client.rekey(ekeys)
        got = await client.until(150)
        assert [p.code for p in got] == [3841, 3, 150]
        player = pb.PlayerMsg.FromString(got[1].body)
        assert (player.playerId, player.nickName, player.job, player.noviceProcess) == (user_id, "Maga", 6, 19000)
        assert player.HasField("consortiaName")  # todos os campos presentes, como o oficial
        hero = pb.ArmyArmyMsg.FromString(got[2].body).simpleHeroInfo
        assert (hero.tempateId, hero.totalIntellect, hero.totalLive, player.fightingCapacity) == (6, 5, 200, 199)

        flags = {f: True for f in ("castle", "army", "build", "tree", "aas", "friend", "sys", "snsReq")}
        client.send(8224, pb.PlayerDataMsg(**flags))
        got = await client.until(150)
        assert {p.code for p in got} >= INIT_CODES

        client.send(8224, pb.PlayerDataMsg(user=True))
        got = await client.until(6)
        assert [p.code for p in got] == [4598, 150, 6]
        assert pb.LoginStateMsg.FromString(got[-1].body).playerId == user_id
        assert len(server.online) == 1

        # segundo login do mesmo personagem derruba o primeiro
        second = FakeFlashClient(*await asyncio.open_connection("127.0.0.1", port))
        second.send(20001, pb.LoginReqMsg(key=key, ekeys=list(ekeys)))
        second.rekey(ekeys)
        await second.until(150)
        assert await asyncio.wait_for(client.reader.read(), 5) == b""
        second.writer.close()
    finally:
        await http.close()
        tcp.close()
        server.acceptor.close_all()
        await services.database.dispose()
