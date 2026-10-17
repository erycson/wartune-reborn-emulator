class DomainError(Exception):
    """Erro de regra de negócio; a mensagem pode ser mostrada ao jogador."""


class AuthenticationError(DomainError):
    pass


class NotFoundError(DomainError):
    pass


class ValidationError(DomainError):
    pass


class ConflictError(DomainError):
    pass
