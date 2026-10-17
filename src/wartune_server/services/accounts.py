"""Contas globais e tickets de entrada em servidores (papel do portal/launcher)."""

from __future__ import annotations

import re
import secrets
from datetime import timedelta

from ..domain.errors import AuthenticationError, ConflictError, NotFoundError, ValidationError
from ..domain.models import Account, PlayTicket
from ..domain.repositories import UnitOfWorkFactory
from ..security.passwords import hash_password, verify_password
from .clock import Clock

USERNAME_RE = re.compile(r"^[A-Za-z0-9_.-]{3,32}$")


class AccountService:
    def __init__(self, uow: UnitOfWorkFactory, clock: Clock, ticket_ttl_seconds: int) -> None:
        self._uow = uow
        self._clock = clock
        self._ticket_ttl = timedelta(seconds=ticket_ttl_seconds)

    async def register(self, username: str, password: str) -> Account:
        if not USERNAME_RE.match(username):
            raise ValidationError("usuário deve ter 3-32 caracteres: letras, números, _ . -")
        if len(password) < 6:
            raise ValidationError("senha deve ter pelo menos 6 caracteres")
        async with self._uow() as uow:
            if await uow.accounts.by_username(username):
                raise ConflictError("usuário já existe")
            account = await uow.accounts.add(Account(username, hash_password(password), self._clock.now()))
            await uow.commit()
            return account

    async def authenticate(self, username: str, password: str) -> Account:
        async with self._uow() as uow:
            account = await uow.accounts.by_username(username)
            if account is None or not verify_password(password, account.password_hash):
                raise AuthenticationError("usuário ou senha inválidos")
            if account.banned:
                raise AuthenticationError("conta bloqueada")
            account.last_login_at = self._clock.now()
            await uow.commit()
            return account

    async def issue_ticket(self, account_id: int, server_id: int) -> PlayTicket:
        now = self._clock.now()
        async with self._uow() as uow:
            if await uow.servers.get(server_id) is None:
                raise NotFoundError(f"servidor {server_id} não existe")
            ticket = await uow.tickets.add(
                PlayTicket(secrets.token_urlsafe(24), account_id, server_id, now, now + self._ticket_ttl)
            )
            await uow.commit()
            return ticket
