"""HTTP do jogo: só os endpoints que o ``Loading.swf`` chama em ``REQUEST_PATH``.

Portal, config.xml e arquivos estáticos ficam no PHP/Apache (``D:/wartune/portal`` e ``cdn``).

Formatos conferidos no cliente decompilado:

* ``loginselectlist`` - URLLoader texto; lê ``..Item[0]@ID`` e ``@Active``.
* ``login``/``login2`` - ``LoginQueue``: exige ``@message`` presente, ``@userId != 0`` e
  ``@value != "false"``; ``@message`` com ``|`` é fila de espera.
* ``visualizeregister`` - LoaderManagerII tipo 7 (XML cru): ``@value == "true"`` e ``@type`` 0|3.
* ``updateplayernovice`` - corpo é um inteiro (o ``noviceProcess`` atual).
"""

from __future__ import annotations

import hmac
import zlib
from dataclasses import dataclass, field
from datetime import UTC, datetime
from xml.sax.saxutils import quoteattr

import structlog
from aiohttp import web
from aiohttp.typedefs import Handler

from ..config import Settings
from ..domain.errors import DomainError, NotFoundError, ValidationError
from ..domain.models import Mail, MailAnnex
from ..domain.repositories import UnitOfWork
from ..game import mail as mailbox
from ..game.session import OnlinePlayers
from ..services.characters import CharacterService, RegistrationRequest, normalize_nickname
from ..services.login import LoginService

log = structlog.get_logger(__name__)

CROSSDOMAIN = '<?xml version="1.0"?><cross-domain-policy><allow-access-from domain="*" /></cross-domain-policy>'

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
    login: LoginService
    characters: CharacterService
    online: OnlinePlayers = field(default_factory=OnlinePlayers)


class GameHttpApi:
    def __init__(self, deps: HttpDeps) -> None:
        self._d = deps
        self._skip_tutorial = deps.settings.skip_tutorial

    def routes(self, app: web.Application) -> None:
        r = app.router
        r.add_get("/crossdomain.xml", self.crossdomain)
        r.add_route("*", "/loginselectlist", self.select_list)
        r.add_post("/login", self.http_login)
        r.add_post("/login2", self.http_login)
        r.add_route("*", "/visualizeregister", self.register)
        r.add_post("/updateplayernovice", self.novice)
        r.add_route("*", "/flashversionservlet", self.plain_true)
        r.add_post("/maillist", self.mail_list)  # EmailManager.getMailList
        r.add_route("*", "/nicknamecheck", self.nickname_check)  # RenameView, antes do 8345
        r.add_post("/questionreplaylist", self.empty_list)  # CustomerServiceManager: respostas do suporte
        if self._d.settings.gm_secret:  # sem segredo a rota nem existe (a porta é pública)
            r.add_post("/gm/kick", self.gm_kick)
            r.add_post("/gm/ban", self.gm_ban)

    # -- jogo --------------------------------------------------------------------------
    async def crossdomain(self, _: web.Request) -> web.Response:
        # o SWF vem do Apache (outra porta = outra origem para o Flash)
        return web.Response(text=CROSSDOMAIN, content_type="text/xml")

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
            result = await self._d.login.http_login(params.get("p", ""), request.remote or "")
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
                # a sessão online grava o personagem inteiro (5015, saída...): sem isto, desfaria o valor
                online = self._d.online.get(character_id)
                if online is not None and online.snapshot is not None:
                    online.snapshot.character.novice_process = max(0, value)
            snap = await self._d.characters.snapshot(character_id)
        except DomainError as exc:
            log.info("updateplayernovice recusado", erro=str(exc))
            return web.Response(text="0")
        return web.Response(text=str(snap.character.novice_process))

    def _gm_allowed(self, request: web.Request) -> bool:
        secret = self._d.settings.gm_secret or ""
        if hmac.compare_digest(request.headers.get("X-GM-Secret", "").encode(), secret.encode()):
            return True
        log.warning("rota GM com segredo errado", caminho=request.path, peer=request.remote)
        return False

    async def gm_kick(self, request: web.Request) -> web.Response:
        """Portal (painel GM): derruba o personagem antes de editar o banco; 200 = já pode gravar."""
        if not self._gm_allowed(request):
            return web.json_response({"ok": False, "error": "segredo inválido"}, status=403)
        try:
            character_id = _int(await _params(request), "character_id")
            await self._d.online.kick(character_id)
        except ValidationError as exc:
            return web.json_response({"ok": False, "error": str(exc)}, status=400)
        except TimeoutError:
            return web.json_response({"ok": False, "error": "a sessão não terminou a tempo"}, status=503)
        return web.json_response({"ok": True})

    async def gm_ban(self, request: web.Request) -> web.Response:
        """Portal: ``account_id`` e ``banned`` 0/1. Banir invalida as sessões de login e derruba o
        personagem; o próximo /login e 20001 da conta são recusados."""
        if not self._gm_allowed(request):
            return web.json_response({"ok": False, "error": "segredo inválido"}, status=403)
        try:
            params = await _params(request)
            account_id, banned = _int(params, "account_id"), _int(params, "banned")
            if banned not in (0, 1):
                raise ValidationError("parâmetro banned inválido")
            for character_id in await self._d.login.set_banned(account_id, bool(banned)):
                if banned:
                    await self._d.online.kick(character_id)
        except ValidationError as exc:
            return web.json_response({"ok": False, "error": str(exc)}, status=400)
        except NotFoundError as exc:
            return web.json_response({"ok": False, "error": str(exc)}, status=404)
        except TimeoutError:
            return web.json_response({"ok": False, "error": "a sessão não terminou a tempo"}, status=503)
        log.info("conta banida" if banned else "conta desbanida", conta=account_id)
        return web.json_response({"ok": True})

    async def plain_true(self, _: web.Request) -> web.Response:
        return web.Response(text="true")

    async def mail_list(self, request: web.Request) -> web.Response:
        """Correio do jogador. ``mailId`` "0" = todos, senão ids separados por vírgula (148 novo,
        ``reqType=1`` ao abrir um correio: marca como lido)."""
        params = await _params(request)
        try:
            character_id = _int(params, "userId")
            self._d.login.session_for_character(params.get("key", ""), character_id)
            ids = [int(i) for i in params.get("mailId", "0").split(",") if i.strip()]
        except (DomainError, ValueError) as exc:
            log.info("maillist recusado", erro=str(exc))
            return _zlib('<?xml version="1.0" encoding="UTF-8"?><Result value="false" message=""/>')
        wanted = None if ids in ([], [0]) else ids

        async def load(uow: UnitOfWork) -> tuple[list[Mail], list[MailAnnex], str]:
            mails = await uow.mails.by_receiver(character_id, wanted)
            annexes = await uow.mails.annexes([m.id or 0 for m in mails])
            c = await uow.characters.get(character_id)
            return mails, annexes, (c.nickname or "") if c else ""

        mails, annexes, nick = await self._d.characters.read(load)
        if params.get("reqType") == "1":
            unread = [m for m in mails if m.read_at is None]
            for m in unread:
                m.read_at = datetime.now(UTC)
            await self._d.characters.save(*unread)
        return _zlib(mailbox.list_xml(mails, annexes, nick))

    async def nickname_check(self, request: web.Request) -> web.Response:
        """``@value`` true = nome livre; senão ``@message`` vai para a tela de troca de nome."""
        params = await _params(request)
        try:
            nick = normalize_nickname(params.get("nickname", ""))
        except ValidationError as exc:
            return xml_result(False, str(exc))
        taken = await self._d.characters.read(
            lambda uow: uow.characters.nickname_taken(self._d.settings.server_id, nick)
        )
        return xml_result(not taken, "este nome já está em uso" if taken else "")

    async def empty_list(self, _: web.Request) -> web.Response:
        # o cliente faz ByteArray.uncompress() no corpo: o XML vai em zlib
        # ponytail: respostas do suporte sempre vazias até existir o atendimento
        return _zlib('<?xml version="1.0" encoding="UTF-8"?><Result value="true" message="Success"/>')


def _zlib(xml: str) -> web.Response:
    return web.Response(body=zlib.compress(xml.encode()), content_type="application/octet-stream")


@web.middleware
async def allow_any_origin(request: web.Request, handler: Handler) -> web.StreamResponse:
    """O Ruffle faz fetch de outra origem (página no Apache); o Flash usa o crossdomain.xml."""
    try:
        response = await handler(request)
    except web.HTTPNotFound:
        log.warning("rota HTTP inexistente", metodo=request.method, caminho=request.path)
        raise
    response.headers["Access-Control-Allow-Origin"] = "*"
    return response


def build_http_app(deps: HttpDeps) -> web.Application:
    app = web.Application(middlewares=[allow_any_origin], client_max_size=1 << 20)
    GameHttpApi(deps).routes(app)
    return app
