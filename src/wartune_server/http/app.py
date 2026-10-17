"""HTTP do jogo (endpoints que o ``Loading.swf`` chama) + portal mínimo + arquivos estáticos.

Formatos conferidos no cliente decompilado:

* ``loginselectlist`` - URLLoader texto; lê ``..Item[0]@ID`` e ``@Active``.
* ``login``/``login2`` - ``LoginQueue``: exige ``@message`` presente, ``@userId != 0`` e
  ``@value != "false"``; ``@message`` com ``|`` é fila de espera.
* ``visualizeregister`` - LoaderManagerII tipo 7 (XML cru): ``@value == "true"`` e ``@type`` 0|3.
* ``updateplayernovice`` - corpo é um inteiro (o ``noviceProcess`` atual).
"""

from __future__ import annotations

from dataclasses import dataclass
from importlib import resources
from pathlib import Path
from urllib.parse import quote, urlencode
from xml.sax.saxutils import quoteattr

import structlog
from aiohttp import web

from ..config import Settings
from ..domain.errors import DomainError, ValidationError
from ..services.accounts import AccountService
from ..services.characters import CharacterService, RegistrationRequest
from ..services.login import LoginService

log = structlog.get_logger(__name__)

TUTORIAL_DONE = 19000  # BaseManager: noviceProcess >= 19000 entra direto no castelo


def xml_result(value: bool, message: str = "", **attrs: object) -> web.Response:
    extra = "".join(f" {k}={quoteattr(str(v))}" for k, v in attrs.items())
    result = f'<Result value="{str(value).lower()}" message={quoteattr(message)}{extra}/>'
    body = f'<?xml version="1.0" encoding="UTF-8"?>{result}'
    return web.Response(text=body, content_type="text/xml", charset="utf-8")


def _int(params: dict[str, str], name: str) -> int:
    try:
        return int(params.get(name, ""))
    except ValueError:
        raise ValidationError(f"parâmetro {name} inválido") from None


async def _params(request: web.Request) -> dict[str, str]:
    params = dict(request.query)
    if request.method == "POST":
        params.update({k: v for k, v in (await request.post()).items() if isinstance(v, str)})
    return params


@dataclass(frozen=True, slots=True)
class HttpDeps:
    settings: Settings
    accounts: AccountService
    login: LoginService
    characters: CharacterService
    client_config: str  # config.xml já renderizado


class GameHttpApi:
    def __init__(self, deps: HttpDeps) -> None:
        self._d = deps
        self._skip_tutorial = deps.settings.skip_tutorial

    def routes(self, app: web.Application) -> None:
        r = app.router
        r.add_get("/client/config.xml", self.config_xml)
        r.add_get("/config.xml", self.config_xml)
        r.add_route("*", "/loginselectlist", self.select_list)
        r.add_post("/login", self.http_login)
        r.add_post("/login2", self.http_login)
        r.add_route("*", "/visualizeregister", self.register)
        r.add_post("/updateplayernovice", self.novice)
        r.add_route("*", "/flashversionservlet", self.plain_true)
        r.add_post("/api/register", self.portal_register)
        r.add_post("/api/login", self.portal_login)
        r.add_get("/", self.launcher)
        r.add_get("/play", self.launcher)

    # -- jogo --------------------------------------------------------------------------
    async def config_xml(self, _: web.Request) -> web.Response:
        return web.Response(text=self._d.client_config, content_type="text/xml", charset="utf-8")

    async def select_list(self, request: web.Request) -> web.Response:
        params = await _params(request)
        entries = await self._d.login.select_list(params.get("username", ""))
        items = "".join(
            f'<Item ID="{e.character_id}" Active="{str(e.active).lower()}" NickName={quoteattr(e.nickname or "")}/>'
            for e in entries
        )
        body = f'<?xml version="1.0" encoding="UTF-8"?><Result value="true" message="">{items}</Result>'
        return web.Response(text=body, content_type="text/xml", charset="utf-8")

    async def http_login(self, request: web.Request) -> web.Response:
        params = await _params(request)
        try:
            result = await self._d.login.http_login(params.get("p", ""))
        except DomainError as exc:
            log.info("login HTTP recusado", erro=str(exc), peer=request.remote)
            return xml_result(False, str(exc), userId=0)
        s = self._d.settings
        log.info("login HTTP ok", player=result.user_id, peer=request.remote)
        return xml_result(True, "Login Succeed", userId=result.user_id, Address=s.public_host, Port=s.socket_port)

    async def register(self, request: web.Request) -> web.Response:
        params = await _params(request)
        try:
            character_id = _int(params, "userid")
            self._d.login.session_for_character(params.get("key", ""), character_id)
            req = RegistrationRequest(
                character_id,
                params.get("nickname", ""),
                sex=_int(params, "sex"),
                camp=_int(params, "camp") if params.get("camp") else 1,
                icon=_int(params, "icon"),
            )
            character = await self._d.characters.register(req)
        except DomainError as exc:
            return xml_result(False, str(exc), type=1)
        log.info("personagem criado", player=character.id, nick=character.nickname, job=character.job)
        return xml_result(True, "ok", type=0)

    async def novice(self, request: web.Request) -> web.Response:
        params = await _params(request)
        try:
            character_id = _int(params, "userid")
            self._d.login.session_for_character(params.get("key", ""), character_id)
            if params.get("op") == "1":
                value = _int(params, "noviceprocess")
                if self._skip_tutorial:
                    value = max(value, TUTORIAL_DONE)
                await self._d.characters.set_novice_process(character_id, value)
            snap = await self._d.characters.snapshot(character_id)
        except DomainError as exc:
            log.info("updateplayernovice recusado", erro=str(exc))
            return web.Response(text="0")
        return web.Response(text=str(snap.character.novice_process))

    async def plain_true(self, _: web.Request) -> web.Response:
        return web.Response(text="true")

    # -- portal (no lugar do site oficial) ---------------------------------------------
    async def portal_register(self, request: web.Request) -> web.Response:
        params = await _params(request)
        try:
            account = await self._d.accounts.register(params.get("username", ""), params.get("password", ""))
        except DomainError as exc:
            return web.json_response({"ok": False, "error": str(exc)}, status=400)
        return web.json_response({"ok": True, "username": account.username})

    async def portal_login(self, request: web.Request) -> web.Response:
        """Autentica e emite um ticket para ESTE servidor; devolve as flashvars do Loading.swf."""
        params = await _params(request)
        try:
            account = await self._d.accounts.authenticate(params.get("username", ""), params.get("password", ""))
            assert account.id is not None
            ticket = await self._d.accounts.issue_ticket(account.id, self._d.settings.server_id)
        except DomainError as exc:
            return web.json_response({"ok": False, "error": str(exc)}, status=401)
        s = self._d.settings
        flashvars = {"user": account.username, "key": ticket.token, "site": s.site,
                     "config": f"{s.public_http_url}client/config.xml", "playfb": "0"}
        query = urlencode(flashvars, quote_via=quote)
        return web.json_response({
            "ok": True,
            "flashvars": flashvars,
            "swf_url": f"{s.public_http_url}Loading.swf?{query}",  # para o Flash Player projector
            "websocket_port": s.websocket_port,
            "socket_port": s.socket_port,
        })

    async def launcher(self, _: web.Request) -> web.Response:
        html = resources.files(__package__).joinpath("launcher.html").read_text(encoding="utf-8")
        return web.Response(text=html, content_type="text/html", charset="utf-8")


class StaticFiles:
    """Procura o arquivo em cada pasta, na ordem (``data/overlay`` antes dos assets do relay)."""

    def __init__(self, roots: list[Path]) -> None:
        self._roots = [r.resolve() for r in roots if r.is_dir()]

    async def handle(self, request: web.Request) -> web.StreamResponse:
        rel = request.match_info["path"]
        for root in self._roots:
            candidate = (root / rel).resolve()
            if candidate.is_relative_to(root) and candidate.is_file():  # bloqueia ../
                return web.FileResponse(candidate)
        log.debug("estático não encontrado", path=rel)
        raise web.HTTPNotFound()


def build_http_app(deps: HttpDeps) -> web.Application:
    app = web.Application(client_max_size=1 << 20)
    GameHttpApi(deps).routes(app)
    app.router.add_get("/{path:.+}", StaticFiles(deps.settings.asset_dirs).handle)
    return app
