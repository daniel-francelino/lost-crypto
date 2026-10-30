class LostCryptoError(Exception):
    """Base class for all domain and application errors."""


class DomainError(LostCryptoError):
    """A business rule was violated."""


class InvalidAmountError(DomainError):
    """A monetary value or quantity is invalid (e.g. float input, NaN)."""
