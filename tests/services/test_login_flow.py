from __future__ import annotations

from urllib.parse import quote_from_bytes

import pytest

from wartune_server.domain.errors import AuthenticationError, ConflictError, ValidationError
from wartune_server.security.rsa_keys import LoginKeyPair
from wartune_server.services.characters import CharacterService, GridCastlePlacement, RegistrationRequest
from wartune_server.services.clock import FakeClock
from wartune_server.services.login import LoginPayload, LoginService
from wartune_server.services.sessions import InMemoryLoginSessionStore
from wartune_server.templates.repository import GameTemplates

TEMPLATES = GameTemplates.parse(b"""<root><GameHeroTemp>
<GameHeroTempInfo TemplateId="6" Job="3" Sexs="0" Power="1" Agility="1" Intellect="5" Captain="100"
 Physique="5" Live="90" ForceHit="10" Parry="10" SkillScript="30711,30811"/>
<GameHeroTempInfo TemplateId="1" Job="1" Sexs="1" Power="5" Agility="1" Intellect="1" Captain="100"
 Physique="5" Live="90" ForceHit="10" Parry="10" SkillScript="10711,10811"/>
</GameHeroTemp><BuildingTempInfos>
<BuildingTempInfo TemplateId="90101" SonType="901"/><BuildingTempInfo TemplateId="10101" SonType="101"/>
<BuildingTempInfo TemplateId="30101" SonType="301"/><BuildingTempInfo TemplateId="40201" SonType="402"/>
<BuildingTempInfo TemplateId="50101" SonType="501"/><BuildingTempInfo TemplateId="120101" SonType="1201"/>
</BuildingTempInfos></root>""")


@pytest.fixture(scope="module")
def keys() -> LoginKeyPair:
    return LoginKeyPair.generate()


class PortalOnClock:
    """O portal (PHP) cria contas e tickets; aqui no relógio falso do teste."""

    def __init__(self, portal, clock) -> None:  # type: ignore[no-untyped-def]
        self._portal, self._clock = portal, clock

    async def register(self, username: str, _password: str):  # type: ignore[no-untyped-def]
        return await self._portal.account(username)

    async def issue_ticket(self, account_id: int, server_id: int):  # type: ignore[no-untyped-def]
        return Ticket(await self._portal.ticket(account_id, server_id, now=self._clock.now()))


class Ticket:
    def __init__(self, token: str) -> None:
        self.token = token


@pytest.fixture
def env(uow_factory, keys, portal):  # type: ignore[no-untyped-def]
    clock = FakeClock()
    sessions = InMemoryLoginSessionStore(clock, ttl_seconds=60)
    return (
        clock,
        PortalOnClock(portal, clock),
        LoginService(uow_factory, keys, sessions, clock, server_id=1),
        CharacterService(uow_factory, TEMPLATES, GridCastlePlacement()),
    )


def client_payload(keys: LoginKeyPair, user: str, ticket: str, temp: str = "1234567", uid: int = 0) -> str:
    """Igual ao Loading.as: user escapado byte a byte + RSA + Base64."""
    escaped = quote_from_bytes(user.encode("utf-8"), safe="")
    return keys.encrypt_b64(f"{escaped}|{ticket}|{temp}|{uid}".encode())


async def test_full_login_and_registration(env, keys) -> None:  # type: ignore[no-untyped-def]
    _clock, accounts, login, chars = env
    acc = await accounts.register("joão_1".replace("ã", "a"), "segredo1")
    ticket = await accounts.issue_ticket(acc.id, 1)

    assert await login.select_list("joao_1") == []  # nunca entrou neste servidor

    result = await login.http_login(client_payload(keys, "joao_1", ticket.token))
    assert result.user_id > 0
    assert result.session_key == LoginPayload("joao_1", ticket.token, "1234567", 0).session_key

    entries = await login.select_list("joao_1")
    assert [(e.character_id, e.active) for e in entries] == [(result.user_id, False)]

    with pytest.raises(AuthenticationError, match="ainda não foi criado"):
        await login.claim_socket(result.session_key)

    session = login.session_for_character(result.session_key, result.user_id)
    char = await chars.register(RegistrationRequest(session.character_id, "  Maga  ", sex=1, camp=1, icon=6))
    assert (char.nickname, char.job, char.sex, char.active) == ("Maga", 6, 0, True)

    snap = await chars.snapshot(result.user_id)
    assert snap.leader is not None and snap.leader.intellect == 5 and snap.castle is not None
    assert sorted(b.template_id for b in snap.buildings) == [10101, 30101, 40201, 50101, 90101, 120101]

    claimed = await login.claim_socket(result.session_key)
    assert claimed.id == result.user_id

    # segundo login no mesmo servidor reaproveita o personagem
    again = await login.http_login(client_payload(keys, "joao_1", ticket.token, temp="999"))
    assert again.user_id == result.user_id


async def test_ticket_rules(env, keys) -> None:  # type: ignore[no-untyped-def]
    clock, accounts, login, _ = env
    alice = await accounts.register("alice", "segredo1")
    await accounts.register("bob", "segredo1")
    ticket = await accounts.issue_ticket(alice.id, 1)

    with pytest.raises(AuthenticationError, match="não pertence"):
        await login.http_login(client_payload(keys, "bob", ticket.token))
    with pytest.raises(AuthenticationError, match="inválido"):
        await login.http_login(client_payload(keys, "alice", "ticket-falso"))
    clock.advance(301)
    with pytest.raises(AuthenticationError, match="expirado"):
        await login.http_login(client_payload(keys, "alice", ticket.token))
    with pytest.raises(AuthenticationError):
        await login.http_login("lixo")


async def test_session_ttl_is_sliding(env, keys) -> None:  # type: ignore[no-untyped-def]
    """Login -> tela de criação -> carga do cliente: cada passo renova a sessão (TTL 60s)."""
    clock, accounts, login, chars = env
    acc = await accounts.register("gina", "segredo1")
    ticket = await accounts.issue_ticket(acc.id, 1)
    result = await login.http_login(client_payload(keys, "gina", ticket.token))
    clock.advance(50)
    login.session_for_character(result.session_key, result.user_id)  # visualizeregister
    await chars.register(RegistrationRequest(result.user_id, "Gina", 1, 1, 1))
    clock.advance(50)  # 100s desde o login HTTP
    assert (await login.claim_socket(result.session_key)).id == result.user_id


async def test_session_expires(env, keys) -> None:  # type: ignore[no-untyped-def]
    clock, accounts, login, _ = env
    acc = await accounts.register("carol", "segredo1")
    ticket = await accounts.issue_ticket(acc.id, 1)
    result = await login.http_login(client_payload(keys, "carol", ticket.token))
    clock.advance(61)
    with pytest.raises(AuthenticationError, match="expirada"):
        login.session(result.session_key)


async def test_registration_rules(env, keys) -> None:  # type: ignore[no-untyped-def]
    _clock, accounts, login, chars = env
    ids = []
    for name in ("dave", "erin"):
        acc = await accounts.register(name, "segredo1")
        ticket = await accounts.issue_ticket(acc.id, 1)
        ids.append((await login.http_login(client_payload(keys, name, ticket.token))).user_id)

    await chars.register(RegistrationRequest(ids[0], "Nome", 1, 1, 1))
    with pytest.raises(ConflictError, match="em uso"):
        await chars.register(RegistrationRequest(ids[1], "Nome", 1, 1, 1))
    with pytest.raises(ConflictError, match="já criado"):
        await chars.register(RegistrationRequest(ids[0], "Outro", 1, 1, 1))
    for bad in ("x", "a" * 15, "<b>oi", "com espaço"):
        with pytest.raises(ValidationError):
            await chars.register(RegistrationRequest(ids[1], bad, 1, 1, 1))
    with pytest.raises(ValidationError, match="classe"):
        await chars.register(RegistrationRequest(ids[1], "Valido", 1, 1, 9))

