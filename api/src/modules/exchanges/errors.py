from core.errors import DomainError, LostCryptoError


class ExchangeError(LostCryptoError):
    """Base class for errors raised by exchange adapters."""


class TransientExchangeError(ExchangeError):
    """Network/rate-limit problem; retrying later may succeed."""


class UnknownSymbolError(ExchangeError):
    """The exchange does not list the requested symbol."""


class ExchangeRejected(ExchangeError):
    """The exchange refused the order (permanent: do not retry as-is)."""


class UnknownOrder(ExchangeError):
    """No order with that client order id exists on the exchange."""


class TradingNotEnabled(ExchangeError):
    """Placing real orders is not enabled for this integration yet."""


class ExchangeConfigurationError(LostCryptoError):
    """The exchange setup is wrong (misconfigured class or unknown name in ENABLED_EXCHANGES)."""


class UnknownExchangeError(DomainError):
    """The requested exchange is not registered."""


class UnsupportedTimeframeError(DomainError):
    """The exchange does not offer candles for the requested timeframe."""
