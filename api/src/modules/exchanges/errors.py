from core.errors import LostCryptoError


class ExchangeError(LostCryptoError):
    """Base class for errors raised by exchange adapters."""


class TransientExchangeError(ExchangeError):
    """Network/rate-limit problem; retrying later may succeed."""


class UnknownSymbolError(ExchangeError):
    """The exchange does not list the requested symbol."""
