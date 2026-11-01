"""The pairs the platform works with: liquid spot coins quoted in USDT.

The quote is always USDT so that results read in dollars (the operator invests up to 1,000 USDT)
and are comparable across pairs. The list feeds the symbol selectors; it is not a promise that
candles are stored.
"""

from dataclasses import dataclass

QUOTE = "USDT"


@dataclass(frozen=True, slots=True)
class SupportedPair:
    base: str
    name: str

    @property
    def symbol(self) -> str:
        return f"{self.base}/{QUOTE}"


SUPPORTED_PAIRS: tuple[SupportedPair, ...] = (
    SupportedPair("BTC", "Bitcoin"),
    SupportedPair("ETH", "Ethereum"),
    SupportedPair("BNB", "BNB"),
    SupportedPair("SOL", "Solana"),
    SupportedPair("XRP", "XRP"),
    SupportedPair("ADA", "Cardano"),
    SupportedPair("DOGE", "Dogecoin"),
    SupportedPair("AVAX", "Avalanche"),
    SupportedPair("DOT", "Polkadot"),
    SupportedPair("LINK", "Chainlink"),
    SupportedPair("LTC", "Litecoin"),
    SupportedPair("TRX", "TRON"),
    SupportedPair("ATOM", "Cosmos"),
    SupportedPair("ETC", "Ethereum Classic"),
)
