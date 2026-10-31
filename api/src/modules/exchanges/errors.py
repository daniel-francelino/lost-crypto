from core.errors import DomainError, LostCryptoError


class ExchangeError(LostCryptoError):
    """Base class for errors raised by exchange adapters."""


class TransientExchangeError(ExchangeError):
    """Network/rate-limit problem; retrying later may succeed."""


class RateLimited(TransientExchangeError):
    """The exchange answered 429/418. Nothing may be sent before ``retry_after_seconds``
    (when the exchange said how long); insisting after a 429 gets the IP banned."""

    def __init__(self, message: str, retry_after_seconds: float | None = None) -> None:
        super().__init__(message)
        self.retry_after_seconds = retry_after_seconds


class UnknownSymbolError(ExchangeError):
    """The exchange does not list the requested symbol."""


class ExchangeRejected(ExchangeError):
    """The exchange refused the order (permanent: do not retry as-is)."""


class UnknownOrder(ExchangeError):
    """No order with that client order id exists on the exchange."""


class TradingNotEnabled(ExchangeError):
    """Placing real orders is not enabled for this integration yet."""


class NotAuthenticated(TradingNotEnabled):
    """The integration was created without credentials: only public data is available."""


class AuthenticationFailed(ExchangeError):
    """The exchange rejected the credentials (invalid, expired or missing permissions)."""


class UnknownOutcome(ExchangeError):
    """A write may or may not have reached the exchange (timeout, dropped connection).

    The only safe reaction is to look the order up by its client id (reconciliation); never to
    send it again blindly.
    """


class UnsupportedFeeAsset(ExchangeError):
    """A fill was charged in an asset the portfolio cannot value (e.g. BNB)."""


class ExchangeConfigurationError(LostCryptoError):
    """The exchange setup is wrong (misconfigured class or unknown name in ENABLED_EXCHANGES)."""


class UnknownExchangeError(DomainError):
    """The requested exchange is not registered."""


class UnsupportedTimeframeError(DomainError):
    """The exchange does not offer candles for the requested timeframe."""
