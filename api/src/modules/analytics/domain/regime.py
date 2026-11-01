"""Descriptive volatility and trend-efficiency regimes for historical backtests."""

from collections.abc import Sequence
from decimal import Decimal, localcontext
from typing import Any, cast

from modules.backtesting.domain.models import EquityPoint
from modules.market_data.domain.models import Candle

_PRECISION = 40
_PCT = Decimal(100)


def rolling_volatility(returns: Sequence[Decimal], window: int) -> list[Decimal | None]:
    if window < 2:
        raise ValueError("window must be at least 2")
    output: list[Decimal | None] = [None] * len(returns)
    with localcontext() as ctx:
        ctx.prec = _PRECISION
        total = Decimal(0)
        squares = Decimal(0)
        for index, value in enumerate(returns):
            total += value
            squares += value * value
            if index >= window:
                old = returns[index - window]
                total -= old
                squares -= old * old
            if index >= window - 1:
                mean = total / window
                variance = max(Decimal(0), squares / window - mean * mean)
                output[index] = variance.sqrt()
    return output


def terciles(values: Sequence[Decimal]) -> tuple[Decimal | None, Decimal | None]:
    if not values:
        return None, None
    ordered = sorted(values)
    return ordered[(len(ordered) - 1) // 3], ordered[(2 * (len(ordered) - 1)) // 3]


def efficiency_ratio(closes: Sequence[Decimal], window: int) -> list[Decimal | None]:
    if window < 1:
        raise ValueError("window must be positive")
    output: list[Decimal | None] = [None] * len(closes)
    with localcontext() as ctx:
        ctx.prec = _PRECISION
        for index in range(window, len(closes)):
            changes = [abs(closes[i] - closes[i - 1]) for i in range(index - window + 1, index + 1)]
            denominator = sum(changes, Decimal(0))
            output[index] = (
                abs(closes[index] - closes[index - window]) / denominator
                if denominator > 0
                else Decimal(0)
            )
    return output


def _bands(
    features: Sequence[Decimal | None],
    strategy_returns: Sequence[Decimal | None],
    asset_returns: Sequence[Decimal | None],
    in_market: Sequence[bool],
) -> dict[str, Any]:
    valid_features = [
        feature
        for feature, strategy_return, asset_return in zip(
            features, strategy_returns, asset_returns, strict=True
        )
        if feature is not None and strategy_return is not None and asset_return is not None
    ]
    cut_low, cut_high = terciles(valid_features)
    groups: dict[str, list[int]] = {"low": [], "medium": [], "high": []}
    total_valid = len(valid_features)
    for index, feature in enumerate(features):
        if (
            feature is None
            or strategy_returns[index] is None
            or asset_returns[index] is None
            or cut_low is None
            or cut_high is None
        ):
            continue
        label = "low" if feature <= cut_low else "medium" if feature <= cut_high else "high"
        groups[label].append(index)

    result = []
    for label, indexes in groups.items():
        strategy_total = Decimal(1)
        asset_total = Decimal(1)
        strategy_count = 0
        asset_count = 0
        for index in indexes:
            strategy_return = strategy_returns[index]
            asset_return = asset_returns[index]
            if strategy_return is not None:
                strategy_total *= Decimal(1) + strategy_return
                strategy_count += 1
            if asset_return is not None:
                asset_total *= Decimal(1) + asset_return
                asset_count += 1
        result.append(
            {
                "label": label,
                "bars": len(indexes),
                "share_pct": Decimal(len(indexes)) * _PCT / total_valid
                if total_valid
                else Decimal(0),
                "strategy_return_pct": (strategy_total - 1) * _PCT if strategy_count else None,
                "asset_return_pct": (asset_total - 1) * _PCT if asset_count else None,
                "in_market_pct": (
                    Decimal(sum(in_market[index] for index in indexes)) * _PCT / len(indexes)
                    if indexes
                    else None
                ),
            }
        )
    return {"cut_low": cut_low, "cut_high": cut_high, "bands": result}


def _json_values(value: Any) -> Any:
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, dict):
        return {key: _json_values(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_json_values(item) for item in value]
    return value


def regime_report(
    candles: Sequence[Candle],
    equity_curve: Sequence[EquityPoint],
    in_market: Sequence[bool],
    window: int = 30,
) -> dict[str, Any] | None:
    """Group returns by lagged volatility and efficiency features (descriptive terciles)."""
    if len(candles) < 2 * window or len(equity_curve) != len(candles):
        return None
    closes = [c.close for c in candles]
    asset_returns: list[Decimal | None] = [None]
    strategy_returns: list[Decimal | None] = [None]
    with localcontext() as ctx:
        ctx.prec = _PRECISION
        for index in range(1, len(candles)):
            gap_ok = (candles[index].open_time - candles[index - 1].open_time) <= (
                candles[index].timeframe.delta * 3 // 2
            )
            if not gap_ok:
                asset_returns.append(None)
                strategy_returns.append(None)
            else:
                previous_close = closes[index - 1]
                previous_equity = equity_curve[index - 1].equity
                asset_returns.append(
                    closes[index] / previous_close - 1 if previous_close > 0 else None
                )
                strategy_returns.append(
                    equity_curve[index].equity / previous_equity - 1
                    if previous_equity > 0
                    else None
                )
    vol_returns = [value for value in asset_returns[1:] if value is not None]
    vol = rolling_volatility(vol_returns, window)
    vol_features: list[Decimal | None] = []
    valid_before = 0
    for index, value in enumerate(asset_returns):
        vol_features.append(vol[valid_before - 1] if valid_before >= window else None)
        if index > 0 and value is not None:
            valid_before += 1
    efficiency = efficiency_ratio(closes, window)
    lagged_efficiency = [None, *efficiency[:-1]]
    with localcontext() as ctx:
        ctx.prec = _PRECISION
        return cast(
            dict[str, Any],
            _json_values(
                {
                    "window": window,
                    "method": "full_sample_terciles_descriptive",
                    "volatility": _bands(vol_features, strategy_returns, asset_returns, in_market),
                    "efficiency": _bands(
                        lagged_efficiency, strategy_returns, asset_returns, in_market
                    ),
                }
            ),
        )
