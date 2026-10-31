from core.errors import ConflictError, DomainError, NotFoundError


class BotNotFound(NotFoundError):
    pass


class BotNameTaken(ConflictError):
    pass


class InvalidBotConnection(DomainError):
    pass
