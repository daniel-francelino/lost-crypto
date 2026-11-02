from collections.abc import Mapping
from typing import Any

from modules.bots.domain.models import BotConfig
from modules.risk_management.domain.models import limits_to_dict


def config_changes(old: BotConfig, new: BotConfig) -> dict[str, dict[str, Any]]:
    """Return safe, JSON-compatible configuration differences (never credentials)."""
    fields = (
        "name",
        "exchange",
        "symbol",
        "product",
        "leverage",
        "margin_mode",
        "allow_short",
        "timeframe",
        "strategy_type",
        "strategy_params",
        "initial_capital",
        "fee_rate",
        "slippage_bps",
        "mode",
        "connection_id",
    )
    result: dict[str, dict[str, Any]] = {}
    for name in fields:
        before, after = getattr(old, name), getattr(new, name)
        before = before.value if hasattr(before, "value") else before
        after = after.value if hasattr(after, "value") else after
        if name == "connection_id":
            before = None if before is None else str(before)
            after = None if after is None else str(after)
        elif isinstance(before, Mapping):
            before, after = dict(before), dict(after)
        elif hasattr(before, "as_tuple"):
            before, after = str(before), str(after)
        if before != after:
            result[name] = {"from": before, "to": after}
    old_risk, new_risk = limits_to_dict(old.risk), limits_to_dict(new.risk)
    for key, after in new_risk.items():
        before = old_risk[key]
        if before != after:
            result[f"risk.{key}"] = {"from": before, "to": after}
    return result
