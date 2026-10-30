class LostCryptoError(Exception):
    """Base class for all domain and application errors."""


class DomainError(LostCryptoError):
    """A business rule was violated."""


class InvalidAmountError(DomainError):
    """A monetary value or quantity is invalid (e.g. float input, NaN)."""


class NotFoundError(DomainError):
    """A referenced entity does not exist."""


class ConflictError(DomainError):
    """The operation conflicts with the current state (e.g. duplicate name, invalid transition)."""
