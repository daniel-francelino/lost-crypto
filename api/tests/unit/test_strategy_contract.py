"""Strategy contract, registry and catalog.

The contract tests run against EVERY strategy in ``AVAILABLE_STRATEGIES``: a new strategy file
is accepted only if it behaves like the others (valid params, resumable state, no repainting,
well-formed signals).
"""

import json
from decimal import Decimal
from typing import Any

import pytest

from core.config import Settings
from factories import make_candles
from modules.market_data.domain.models import Candle
from modules.strategies.catalog import AVAILABLE_STRATEGIES, build_strategy_registry
from modules.strategies.domain.base import (
    InvalidStrategyParams,
    ParamSpec,
    Strategy,
    StrategyStyle,
)
from modules.strategies.domain.donchian_breakout import DonchianBreakoutStrategy, DonchianParams
from modules.strategies.domain.registry import (
    StrategyConfigurationError,
    StrategyRegistry,
    UnknownStrategy,
)
from modules.strategies.domain.types import Side, Signal, StrategyContext, StrategyResult

SYMBOL = "BTC/USDT"
# Strategies whose entries always carry a stop, because the stop is part of the design.
STOP_BY_DESIGN = frozenset({"trend_quality_breakout"})
DEFAULT_PRICE_CEILING = Decimal(10_000)


def _dips() -> list[Candle]:
    """Quiet around 100 with sharp two-candle drops that snap back: a mean-reverting market, where
    a mean-reversion strategy buys the drop and sells the recovery."""
    closes: list[int] = []
    for i in range(160):
        dipping = i % 25 in (24,) or (i % 25 == 0 and i > 0)
        closes.append(88 if dipping else 100 + (i % 2))
    return make_candles(closes)


def _trend() -> list[Candle]:
    """Flat, then a strong uptrend, then a strong downtrend: any trend follower should enter
    during the rise and exit during the fall."""
    closes = [100 + (i % 2) for i in range(40)]
    price = closes[-1]
    for _ in range(40):
        price += 2
        closes.append(price)
    for _ in range(50):
        price -= 3
        closes.append(price)
    return make_candles(closes)


def _run(
    strategy: Strategy[Any],
    candles: list[Candle],
    state: Any = None,
    position: Decimal = Decimal(0),
) -> tuple[list[tuple[int, Signal]], Any, Decimal]:
    """Feed candles, holding a 1-unit position after BUY and none after SELL.

    Returns the signals, the final state and the final position (what a bot persists)."""
    state = strategy.initial_state() if state is None else state
    emitted: list[tuple[int, Signal]] = []
    for i, candle in enumerate(candles):
        result = strategy.evaluate(StrategyContext(SYMBOL, candle, position), state)
        state = result.state
        for signal in result.signals:
            emitted.append((i, signal))
            position = Decimal(1) if signal.side is Side.BUY else Decimal(0)
    return emitted, state, position


def _series_for(strategy_cls: type[Strategy[Any]]) -> list[Candle]:
    return _dips() if strategy_cls.STYLE is StrategyStyle.MEAN_REVERSION else _trend()


@pytest.fixture(params=AVAILABLE_STRATEGIES, ids=lambda s: s.TYPE_KEY)
def strategy_cls(request: pytest.FixtureRequest) -> type[Strategy[Any]]:
    return request.param  # type: ignore[no-any-return]


# --- the contract, for every strategy --------------------------------------------------------


def test_metadata_is_complete_and_registrable(strategy_cls: type[Strategy[Any]]) -> None:
    registry = StrategyRegistry()
    registry.register(strategy_cls)  # validates TYPE_KEY / NAME / DESCRIPTION / PARAMETERS
    assert registry.get(strategy_cls.TYPE_KEY) is strategy_cls
    assert all(isinstance(p, ParamSpec) for p in strategy_cls.PARAMETERS)


def test_defaults_documented_in_parameters_are_accepted(strategy_cls: type[Strategy[Any]]) -> None:
    assert strategy_cls.from_params({}) is not None
    defaults = {p.name: p.default for p in strategy_cls.PARAMETERS if p.default is not None}
    assert strategy_cls.from_params(defaults) is not None


def test_params_are_validated(strategy_cls: type[Strategy[Any]]) -> None:
    with pytest.raises(InvalidStrategyParams, match="unknown"):
        strategy_cls.from_params({"definitely_not_a_param": 1})
    for spec in strategy_cls.PARAMETERS:
        with pytest.raises(InvalidStrategyParams):
            strategy_cls.from_params({spec.name: True})  # booleans are never numbers


def test_state_survives_json_serialisation_at_every_step(
    strategy_cls: type[Strategy[Any]],
) -> None:
    strategy = strategy_cls.from_params({})
    state = strategy.initial_state()
    position = Decimal(0)
    for candle in _series_for(strategy_cls):
        result = strategy.evaluate(StrategyContext(SYMBOL, candle, position), state)
        state = result.state
        raw = json.loads(json.dumps(strategy.serialize_state(state)))
        assert strategy.deserialize_state(raw) == state
        for signal in result.signals:
            position = Decimal(1) if signal.side is Side.BUY else Decimal(0)


def test_a_restarted_bot_continues_exactly_like_an_uninterrupted_one(
    strategy_cls: type[Strategy[Any]],
) -> None:
    candles = _series_for(strategy_cls)
    straight, _, _ = _run(strategy_cls.from_params({}), candles)
    entry = next(i for i, s in straight if s.side is Side.BUY)
    exit_ = next(i for i, s in straight if s.side is Side.SELL)

    for split in (entry - 2, (entry + exit_) // 2, exit_ + 2):  # before, during and after the trade
        first, state, position = _run(strategy_cls.from_params({}), candles[:split])
        saved = json.loads(json.dumps(strategy_cls.from_params({}).serialize_state(state)))
        reborn = strategy_cls.from_params({})  # a new process: only the saved state survives
        second, _, _ = _run(reborn, candles[split:], reborn.deserialize_state(saved), position)
        resumed = first + [(i + split, signal) for i, signal in second]
        assert [(i, s.side) for i, s in resumed] == [(i, s.side) for i, s in straight], split


def test_evaluate_is_deterministic_and_never_mutates_state(
    strategy_cls: type[Strategy[Any]],
) -> None:
    strategy = strategy_cls.from_params({})
    state = strategy.initial_state()
    for candle in _series_for(strategy_cls)[:50]:
        ctx = StrategyContext(SYMBOL, candle, Decimal(0))
        before = strategy.serialize_state(state)
        first = strategy.evaluate(ctx, state)
        assert strategy.evaluate(ctx, state) == first
        assert strategy.serialize_state(state) == before
        state = first.state


def test_signals_are_well_formed_and_the_strategy_trades_a_clear_trend(
    strategy_cls: type[Strategy[Any]],
) -> None:
    emitted, _, _ = _run(strategy_cls.from_params({}), _series_for(strategy_cls))
    sides = [s.side for _, s in emitted]
    assert sides[:2] == [Side.BUY, Side.SELL]  # enters the move it was built for, then exits
    assert all(s.symbol == SYMBOL and s.reason for _, s in emitted)
    assert all(s.take_profit is None for _, s in emitted)  # off by default
    entries = [s for _, s in emitted if s.side is Side.BUY]
    if strategy_cls.TYPE_KEY in STOP_BY_DESIGN:
        assert all(s.stop_loss is not None and s.stop_loss < DEFAULT_PRICE_CEILING for s in entries)
    else:
        assert all(s.stop_loss is None for _, s in emitted)  # off by default
    assert sides == [Side.BUY, Side.SELL] * (len(sides) // 2)  # alternating, never doubled


def test_no_signals_before_there_is_any_history(strategy_cls: type[Strategy[Any]]) -> None:
    strategy = strategy_cls.from_params({})
    first = strategy.evaluate(
        StrategyContext(SYMBOL, make_candles([100])[0], Decimal(0)), strategy.initial_state()
    )
    assert first.signals == ()


def test_entry_signals_carry_the_configured_protective_levels(
    strategy_cls: type[Strategy[Any]],
) -> None:
    names = {p.name for p in strategy_cls.PARAMETERS}
    if "stop_loss_pct" not in names:
        pytest.skip("strategy has no protective-level parameters")
    raw: dict[str, Any] = {"stop_loss_pct": 5}
    if "take_profit_pct" in names:
        raw["take_profit_pct"] = 10
    emitted, _, _ = _run(strategy_cls.from_params(raw), _series_for(strategy_cls))
    entry = next(s for _, s in emitted if s.side is Side.BUY)
    assert entry.stop_loss is not None
    price = entry.stop_loss / Decimal("0.95")  # the close the levels were derived from
    if "take_profit_pct" in names:
        assert entry.take_profit == price * Decimal("1.10")
    else:
        assert entry.take_profit is None


# --- Donchian specifics ----------------------------------------------------------------------


def test_donchian_waits_for_a_full_channel_before_signalling() -> None:
    strategy = DonchianBreakoutStrategy(DonchianParams(entry_period=5, exit_period=3))
    closes = [10, 11, 12, 13, 14, 15]  # rising from the first candle
    emitted, _, _ = _run(strategy, make_candles(closes))
    assert [i for i, _ in emitted] == [5]  # first candle with 5 previous highs to compare


def test_donchian_exits_on_the_shorter_channel() -> None:
    strategy = DonchianBreakoutStrategy(DonchianParams(entry_period=5, exit_period=2))
    closes = [10, 11, 12, 13, 14, 15, 16, 15, 12]
    emitted, _, _ = _run(strategy, make_candles(closes))
    assert [(i, s.side) for i, s in emitted] == [(5, Side.BUY), (8, Side.SELL)]


@pytest.mark.parametrize(
    "raw",
    [
        {"entry_period": 5, "exit_period": 10},  # exit channel longer than entry
        {"entry_period": 1},
        {"entry_period": "20"},
        {"stop_loss_pct": 0},
        {"take_profit_pct": 100},
    ],
)
def test_donchian_rejects_invalid_params(raw: dict[str, Any]) -> None:
    with pytest.raises(InvalidStrategyParams):
        DonchianBreakoutStrategy.from_params(raw)


# --- registry and catalog --------------------------------------------------------------------


def test_catalog_offers_every_strategy_with_unique_keys() -> None:
    registry = build_strategy_registry()
    keys = [s.TYPE_KEY for s in registry.list()]
    assert keys == [
        "ema_crossover",
        "donchian_breakout",
        "mean_reversion_zscore",
        "trend_quality_breakout",
    ]
    assert len(set(keys)) == len(keys)
    assert isinstance(registry.create("donchian_breakout", {}), DonchianBreakoutStrategy)


def test_catalog_can_restrict_a_deployment_to_some_strategies() -> None:
    registry = build_strategy_registry(["donchian_breakout"])
    assert [s.TYPE_KEY for s in registry.list()] == ["donchian_breakout"]
    with pytest.raises(UnknownStrategy, match="available: donchian_breakout"):
        registry.create("ema_crossover", {})
    with pytest.raises(StrategyConfigurationError, match="no implementation"):
        build_strategy_registry(["nope"])


def test_enabled_strategies_setting_parses_a_comma_separated_list() -> None:
    parsed = Settings(_env_file=None, enabled_strategies="ema_crossover, donchian_breakout")  # type: ignore[call-arg]
    assert parsed.enabled_strategy_ids == ["ema_crossover", "donchian_breakout"]
    assert Settings(_env_file=None).enabled_strategy_ids == []  # type: ignore[call-arg]


def test_a_strategy_that_leaves_methods_unimplemented_cannot_be_instantiated() -> None:
    class Incomplete(Strategy[None]):
        TYPE_KEY = "incomplete"
        NAME = "Incomplete"
        DESCRIPTION = "x"
        PARAMETERS = ()

        @classmethod
        def from_params(cls, params):  # type: ignore[no-untyped-def]
            return cls()

    with pytest.raises(TypeError, match="abstract"):
        Incomplete()  # type: ignore[abstract]


def _complete(**metadata: Any) -> type[Strategy[None]]:
    attrs: dict[str, Any] = {
        "TYPE_KEY": "ok_key",
        "NAME": "Name",
        "DESCRIPTION": "Description",
        "PARAMETERS": (),
        "STYLE": StrategyStyle.TREND,
        "from_params": classmethod(lambda cls, params: cls()),
        "initial_state": lambda self: None,
        "evaluate": lambda self, ctx, state: StrategyResult((), None),
        "serialize_state": lambda self, state: {},
        "deserialize_state": lambda self, raw: None,
        **metadata,
    }
    return type("Example", (Strategy,), attrs)  # type: ignore[return-value]


@pytest.mark.parametrize(
    "bad",
    [
        {"TYPE_KEY": "Not-Snake"},
        {"TYPE_KEY": ""},
        {"NAME": ""},
        {"DESCRIPTION": "  "},
        {"PARAMETERS": ["not", "a", "tuple"]},
        {"STYLE": "trend"},  # a plain string is not a StrategyStyle
        {"STYLE": None},
    ],
)
def test_registry_refuses_misdeclared_strategies(bad: dict[str, Any]) -> None:
    with pytest.raises(StrategyConfigurationError):
        StrategyRegistry().register(_complete(**bad))


def test_registry_refuses_duplicate_keys_and_accepts_a_complete_strategy() -> None:
    registry = StrategyRegistry()
    registry.register(_complete())
    assert registry.create("ok_key", {}) is not None
    with pytest.raises(StrategyConfigurationError, match="duplicate"):
        registry.register(_complete())
