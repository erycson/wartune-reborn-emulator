"""Fluxo de login do cliente Flash.

1. ``GET  loginselectlist?username=``  -> personagem deste servidor (``ID``, ``Active``)
2. ``POST login`` ``p=RSA(user|ticket|tempPassword|userId)`` -> valida o ticket do
   portal, cria o personagem inativo se for a primeira vez, guarda a sessão
   pendente com ``key = md5(tempPassword)`` e devolve ``userId``/``Address``/``Port``
3. TCP ``20001 LoginReqMsg{key, ekeys}`` -> ``claim_socket(key)`` liga a conexão ao personagem
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from urllib.parse import unquote_to_bytes

from ..domain.errors import AuthenticationError, NotFoundError
from ..domain.models import Character, LoginHistory
from ..domain.repositories import UnitOfWorkFactory
from ..security.rsa_keys import LoginKeyPair, RSAError
from .clock import Clock
from .sessions import LoginSessionStore, PendingLogin


@dataclass(frozen=True, slots=True)
class LoginPayload:
    username: str
    ticket: str
    temp_password: str
    user_id: int

    @property
    def session_key(self) -> str:
        """O cliente calcula ``MD5.hash(tempPassword)`` e manda no 20001."""
        return hashlib.md5(self.temp_password.encode()).hexdigest()

    @classmethod
    def parse(cls, plain: bytes) -> LoginPayload:
        try:
            text = plain.decode("utf-8")
            user, ticket, temp, user_id = text.split("|")
            # usuário vem "escapado" byte a byte (myUrlEncode do Loading.as)
            username = unquote_to_bytes(user).decode("utf-8")
            return cls(username, ticket, temp, int(user_id or 0))
        except (UnicodeDecodeError, ValueError) as exc:
            raise AuthenticationError("payload de login inválido") from exc


@dataclass(frozen=True, slots=True)
class LoginResult:
    user_id: int
    session_key: str


@dataclass(frozen=True, slots=True)
class SelectEntry:
    character_id: int
    active: bool
    nickname: str | None


class LoginService:
    def __init__(
        self,
        uow: UnitOfWorkFactory,
        keys: LoginKeyPair,
        sessions: LoginSessionStore,
        clock: Clock,
        server_id: int,
    ) -> None:
        self._uow = uow
        self._keys = keys
        self._sessions = sessions
        self._clock = clock
        self._server_id = server_id

    async def select_list(self, username: str) -> list[SelectEntry]:
        async with self._uow() as uow:
            account = await uow.accounts.by_username(username)
            if account is None or account.id is None:
                return []
            character = await uow.characters.by_account(account.id, self._server_id)
        if character is None or character.id is None:
            return []
        return [SelectEntry(character.id, character.active, character.nickname)]

    async def http_login(self, encrypted_payload: str, ip: str = "") -> LoginResult:
        try:
            payload = LoginPayload.parse(self._keys.decrypt_b64(encrypted_payload))
        except RSAError as exc:
            raise AuthenticationError("payload de login inválido") from exc

        now = self._clock.now()
        async with self._uow() as uow:
            ticket = await uow.tickets.get(payload.ticket)
            if ticket is None or not ticket.valid_for(self._server_id, now):
                raise AuthenticationError("ticket inválido ou expirado")
            account = await uow.accounts.get(ticket.account_id)
            if account is None or account.id is None or account.username.casefold() != payload.username.casefold():
                raise AuthenticationError("ticket não pertence a este usuário")
            if account.banned:
                raise AuthenticationError("conta bloqueada")

            character = await uow.characters.by_account(account.id, self._server_id)
            if character is None:
                character = await uow.characters.add(Character(account.id, self._server_id, now))
            character.last_login_at = now
            await uow.save(LoginHistory(account.id, "game", ip, now, character.id))
            await uow.commit()

        assert character.id is not None
        self._sessions.put(
            PendingLogin(payload.session_key, account.id, account.username, self._server_id, character.id, now)
        )
        return LoginResult(character.id, payload.session_key)

    def session(self, key: str) -> PendingLogin:
        session = self._sessions.get(key)
        if session is None:
            raise AuthenticationError("sessão de login expirada; entre novamente")
        return session

    def session_for_character(self, key: str, character_id: int) -> PendingLogin:
        session = self.session(key)
        if session.character_id != character_id:
            raise AuthenticationError("sessão não corresponde ao personagem")
        return session

    async def claim_socket(self, key: str, ip: str = "") -> Character:
        """Valida o 20001. A sessão continua válida até expirar (reconexão do socket)."""
        session = self.session(key)
        async with self._uow() as uow:
            character = await uow.characters.get(session.character_id or 0)
            account = await uow.accounts.get(session.account_id)
            if account is None or account.banned:  # banido depois do /login
                raise AuthenticationError("conta bloqueada")
            if character is None:
                raise NotFoundError("personagem não encontrado")
            if not character.active:
                raise AuthenticationError("personagem ainda não foi criado")
            await uow.save(LoginHistory(session.account_id, "game", ip, self._clock.now(), character.id))
            await uow.commit()
        return character

    async def set_banned(self, account_id: int, banned: bool) -> list[int]:
        """Marca a conta e, se banida, invalida as sessões HTTP; devolve o personagem a derrubar
        (um por conta neste servidor)."""
        async with self._uow() as uow:
            account = await uow.accounts.get(account_id)
            if account is None:
                raise NotFoundError("conta não encontrada")
            account.banned = banned
            await uow.commit()
            character = await uow.characters.by_account(account_id, self._server_id)
        if banned:
            self._sessions.drop_account(account_id)
        return [character.id] if character is not None and character.id is not None else []
