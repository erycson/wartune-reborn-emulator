from pathlib import Path

from aiohttp.test_utils import TestClient, TestServer

from tests.game.harness import logged_in
from wartune_server.http.app import HttpDeps, build_http_app


async def test_gm_kick_waits_for_the_session_to_end(tmp_path: Path) -> None:
    async with logged_in(tmp_path, novice=19000) as g:
        s = g.server
        settings = s.settings.model_copy(update={"gm_secret": "segredo"})
        http = TestClient(
            TestServer(build_http_app(HttpDeps(settings, s.services.login, s.services.characters, s.online)))
        )
        await http.start_server()
        try:
            form = {"character_id": g.user_id}
            denied = await http.post("/gm/kick", data=form, headers={"X-GM-Secret": "errado"})
            assert denied.status == 403 and s.online.get(g.user_id) is not None

            ok = await http.post("/gm/kick", data=form, headers={"X-GM-Secret": "segredo"})
            assert ok.status == 200 and s.online.get(g.user_id) is None  # já saiu quando o 200 chega
            again = await http.post("/gm/kick", data=form, headers={"X-GM-Secret": "segredo"})
            assert again.status == 200  # offline: nada a fazer
        finally:
            await http.close()


async def test_gm_route_off_without_secret(tmp_path: Path) -> None:
    async with logged_in(tmp_path, novice=19000) as g:
        http = TestClient(TestServer(g.server.http_app))
        await http.start_server()
        try:
            assert (await http.post("/gm/kick", data={"character_id": g.user_id})).status == 404
        finally:
            await http.close()
