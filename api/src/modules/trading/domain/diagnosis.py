"""Execution quality and the divergence checklist (book 1 ch. 5, C3 and C5).

Chan's order for "why does live differ from the backtest?": (1) bugs, (2) do the trades match,
(3) execution costs above the assumption, (4) illiquidity, (5) data-snooping, (6) regime change.
Bad luck can never be proven, so the checklist never concludes it.
"""

import statistics
from collections.abc import Sequence
from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum
from typing import Any

from modules.execution.domain.orders import Order, OrderStatus, latency_ms, realized_slippage_bps

_Q = Decimal("0.01")
COST_TOLERANCE_BPS = Decimal(1)  # realized slippage this much above the assumption is noise
VOLUME_MARKER = "average volume"


class StepState(StrEnum):
    OK = "ok"
    ATTENTION = "attention"
    NO_DATA = "no_data"


@dataclass(frozen=True, slots=True)
class Step:
    key: str
    state: StepState
    detail: str


def _stats(values: Sequence[Decimal]) -> dict[str, str | None]:
    if not values:
        return {"mean": None, "median": None, "worst": None}
    return {
        "mean": str((sum(values, Decimal(0)) / len(values)).quantize(_Q)),
        "median": str(Decimal(statistics.median(values)).quantize(_Q)),
        "worst": str(max(values).quantize(_Q)),
    }


def execution_quality(orders: Sequence[Order], configured_bps: Decimal) -> dict[str, Any]:
    """Realized slippage (bps, adverse positive) and latency of the filled orders, by type."""
    by_type: dict[str, dict[str, Any]] = {}
    for kind in sorted({o.order_type for o in orders}):
        filled = [
            o
            for o in orders
            if o.order_type == kind and o.status is OrderStatus.FILLED and o.reference_price
        ]
        slippage = [s for o in filled if (s := realized_slippage_bps(o)) is not None]
        latency = [ms for o in filled if (ms := latency_ms(o)) is not None]
        by_type[kind] = {
            "orders": len(filled),
            "slippage_bps": _stats(slippage),
            "latency_ms": {
                "mean": int(statistics.mean(latency)) if latency else None,
                "max": max(latency) if latency else None,
            },
        }
    market = by_type.get("market", {})
    mean = (market.get("slippage_bps") or {}).get("mean")
    return {
        "configured_slippage_bps": str(configured_bps),
        "by_type": by_type,
        "above_configured": mean is not None
        and Decimal(mean) > configured_bps + COST_TOLERANCE_BPS,
    }


def checklist(
    parity: dict[str, Any] | None,
    quality: dict[str, Any],
    volume_refusals: int,
    regime: tuple[Decimal, Decimal] | None,
) -> list[Step]:
    """``regime``: (bot return %, worst period return % of a comparable backtest)."""
    steps: list[Step] = []
    counts = (parity or {}).get("counts") or {}
    if parity is None:
        steps.append(Step("bugs", StepState.NO_DATA, "Run the parity check first."))
        steps.append(Step("trades", StepState.NO_DATA, "Run the parity check first."))
    else:
        unexplained = int(counts.get("unexplained", 0))
        steps.append(
            Step(
                "bugs",
                StepState.OK if unexplained == 0 else StepState.ATTENTION,
                f"{unexplained} unexplained difference(s) with the replay",
            )
        )
        other = sum(int(counts.get(k, 0)) for k in ("cost", "risk", "operational", "data"))
        steps.append(
            Step(
                "trades",
                StepState.OK if other == 0 else StepState.ATTENTION,
                f"{counts.get('match', 0)} identical, {other} explained difference(s)",
            )
        )
    market = (quality.get("by_type") or {}).get("market") or {}
    mean = (market.get("slippage_bps") or {}).get("mean")
    if mean is None:
        steps.append(Step("costs", StepState.NO_DATA, "No filled order with a reference price."))
    else:
        steps.append(
            Step(
                "costs",
                StepState.ATTENTION if quality.get("above_configured") else StepState.OK,
                f"realized {mean} bps vs {quality['configured_slippage_bps']} bps assumed",
            )
        )
    steps.append(
        Step(
            "liquidity",
            StepState.ATTENTION if volume_refusals > 0 else StepState.OK,
            f"{volume_refusals} entry(ies) limited or refused by the volume cap",
        )
    )
    simplified = (parity or {}).get("simplified_return_pct")
    replay = (parity or {}).get("replay_return_pct")
    if simplified is None or replay is None:
        steps.append(
            Step("snooping", StepState.NO_DATA, "No simplified replay (default parameters).")
        )
    else:
        collapses = Decimal(replay) > 0 >= Decimal(simplified)
        steps.append(
            Step(
                "snooping",
                StepState.ATTENTION if collapses else StepState.OK,
                f"tuned {replay}% vs default parameters {simplified}% on the same candles",
            )
        )
    if regime is None:
        steps.append(
            Step("regime", StepState.NO_DATA, "No comparable backtest with periods to compare.")
        )
    else:
        bot_return, worst = regime
        steps.append(
            Step(
                "regime",
                StepState.ATTENTION if bot_return < worst else StepState.OK,
                f"bot {bot_return}% vs worst backtest period {worst}%",
            )
        )
    return steps
