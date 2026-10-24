"""Cliente falso fazendo o caminho do Loading.swf até o LoginState (marco 1)."""

from __future__ import annotations

import asyncio
import hashlib
import os
import re
import zlib
from pathlib import Path
from urllib.parse import quote_from_bytes

import pytest
from aiohttp.test_utils import TestClient, TestServer

from wartune_server.app import GameServerApp, build_services
from wartune_server.config import Settings
from wartune_server.net.servers import start_tcp
from wartune_server.persistence.repositories import SqlAlchemyUnitOfWork
from wartune_server.protocol import Packet, PacketDecoder, StreamCipher
from wartune_server.protocol.messages import wartune_pb2 as pb

TEMPLATES = Path("data/templates/tempinfos.xml")
# catálogo fixo das atividades (o Login Bonus e o presente online), longe do data/events.json do operador
EVENTS = Path(__file__).parent / "fixtures" / "events.json"
pytestmark = pytest.mark.skipif(not TEMPLATES.exists(), reason="precisa de data/templates/tempinfos.xml")

INIT_CODES = {4153, 4154, 4155, 4156, 4157, 4160, 4173, 4176, 4233, 4245}  # LoginInitDataAccept


class FakeFlashClient:
    def __init__(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        self.reader, self.writer = reader, writer
        self.out, self.decoder = StreamCipher(), PacketDecoder(StreamCipher())

    def send(self, code: int, msg: object | None = None, extend1: int = 0) -> None:
        body = msg.SerializeToString() if msg is not None else b""  # type: ignore[attr-defined]
        self.writer.write(self.out.encrypt(Packet(code, body, extend1=extend1).encode()))

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
    from tests.conftest import Portal

    settings = Settings(
        database_url=f"sqlite+aiosqlite:///{tmp_path / 'e2e.db'}",
        rsa_key_file=tmp_path / "rsa.pem",
        log_dir=tmp_path / "logs",
        skip_tutorial=True,
        events_file=EVENTS,
        _env_file=None,  # type: ignore[call-arg]
    )
    services = await build_services(settings)
    portal = Portal(lambda: SqlAlchemyUnitOfWork(services.database.sessions))
    server = GameServerApp(settings, services)
    tcp = await start_tcp(server.acceptor, "127.0.0.1", 0)
    port = tcp.sockets[0].getsockname()[1]
    http = TestClient(TestServer(server.http_app))
    await http.start_server()
    try:
        # portal (PHP): conta + ticket direto no banco; endereço e chave RSA vêm de game_servers
        account = await portal.account("maga")
        fv = {"key": await portal.ticket(account.id), "site": settings.site}
        async with SqlAlchemyUnitOfWork(services.database.sessions) as uow:
            row = await uow.servers.get(settings.server_id)
        assert row is not None and row.rsa_modulus == services.keys.modulus_b64 and row.websocket_port == 5001
        assert "allow-access-from" in await (await http.get("/crossdomain.xml")).text()
        # o cliente descomprime o corpo; o correio exige userId e a chave da sessão (tests/game/test_mail.py)
        for path, ok in (("/maillist", b"false"), ("/questionreplaylist", b"true")):
            body = zlib.decompress(await (await http.post(path, data={"user_id": "1"})).read())
            assert b'<Result value="' + ok + b'"' in body

        sel = await (await http.get("/loginselectlist", params={"username": "maga", "site": fv["site"]})).text()
        assert "<Item" not in sel

        temp = "7654321"
        plain = f"{quote_from_bytes(b'maga', safe='')}|{fv['key']}|{temp}|0".encode()
        login = await (
            await http.post("/login", data={"p": services.keys.encrypt_b64(plain), "site": fv["site"]})
        ).text()
        user_id = int(re.search(r'userId="(\d+)"', login).group(1))  # type: ignore[union-attr]
        assert user_id > 0 and 'value="true"' in login

        key = hashlib.md5(temp.encode()).hexdigest()
        reg = await (
            await http.post(
                "/visualizeregister",
                data={
                    "userid": user_id,
                    "username": "maga",
                    "nickname": "Maga",
                    "sex": 0,
                    "camp": 1,
                    "icon": 6,
                    "key": key,
                },
            )
        ).text()
        assert 'value="true"' in reg and 'type="0"' in reg, reg
        novice = await http.post(
            "/updateplayernovice", data={"op": 1, "userid": user_id, "noviceprocess": 0, "key": key}
        )
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
        got = await client.until(4173)  # o AAS fecha o 8224 na ordem do oficial (171155 #18-#63)
        assert {p.code for p in got} >= INIT_CODES | {100, 4544}  # 4544 vazio no nível 1 (tutorial_en #42)
        built = pb.BuildingInfoListMsg.FromString(next(p for p in got if p.code == 4154).body)
        assert {(b.templateId, b.sonType) for b in built.building} >= {(90101, 901), (40201, 402)}

        client.send(8224, pb.PlayerDataMsg(user=True))
        got = await client.until(6)
        # 4247 só dentro de um exp_rate_events (data); 4638 só depois da missão 130; 4640 só a partir do nível 6;
        # 4612 (fundo normal) e 4497/295 (árvore dourada) com as linhas da 0038, como o tutorial_en #71-#86;
        # 4616 antes do 4198 (tutorial_en #53-#54)
        codes = [p.code for p in got]
        # 4238: uma parte por 50 ofertas na janela (relógio real: o número muda com a data), antes do 4434
        assert codes.index(4238) < codes.index(4434)
        assert [c for c in codes if c not in (4247, 4238)] == [
            112, 4542, 4184, 4512, 4515, 4516, 4501, 4662, 4686,
            4434, 4410, 4360, 4616, 4198, 4152, 4475, 4476, 4484, 4461, 4612, 4497, 295, 363, 364, 190, 4590, 514, 414, 4598, 150, 6,
        ]  # fmt: skip
        assert pb.LoginStateMsg.FromString(got[-1].body).playerId == user_id
        assert [p.code for p in await client.until(4151)] == [4151]  # tutorial_en #94: libera o mapa de campanhas
        assert [p.code for p in await client.until(4725)] == [4392, 4471, 4900, 4725]  # 215937 #104-#110
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
