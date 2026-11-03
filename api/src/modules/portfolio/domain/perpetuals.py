"""Pure accounting primitives for linear, quote-margined perpetual positions.

These value objects are deliberately separate from the existing spot portfolio. A futures
position has margin and signed directional PnL; it must never be represented as owned base-asset
quantity or treated as spot cash.
"""

from dataclasses import dataclass, replace
from datetime import datetime
from decimal import Decimal
from uuid import UUID

from core.errors import DomainError
from modules.exchanges.domain.models import MAX_PERPETUAL_LEVERAGE, PositionSide


class InvalidPerpetualPosition(DomainError):
    pass


@dataclass(frozen=True, slots=True)
class LinearPerpetualPosition:
    side: PositionSide
    quantity: Decimal
    entry_price: Decimal
    leverage: int
    isolated_margin: Decimal
    stop_price: Decimal | None = None
    take_profit_price: Decimal | None = None

    def __post_init__(self) -> None:
        if self.quantity <= 0 or self.entry_price <= 0 or self.isolated_margin <= 0:
            raise InvalidPerpetualPosition("quantity, entry price and margin must be positive")
        if not 1 <= self.leverage <= MAX_PERPETUAL_LEVERAGE:
            raise InvalidPerpetualPosition(
                f"leverage must be between 1x and {MAX_PERPETUAL_LEVERAGE}x"
            )
        if self.stop_price is not None:
            valid_stop = (
                0 < self.stop_price < self.entry_price
                if self.side is PositionSide.LONG
                else self.stop_price > self.entry_price
            )
            if not valid_stop:
                raise InvalidPerpetualPosition("stop price is on the wrong side of the entry")
        if self.take_profit_price is not None:
            valid_target = (
                self.take_profit_price > self.entry_price
                if self.side is PositionSide.LONG
                else 0 < self.take_profit_price < self.entry_price
            )
            if not valid_target:
                raise InvalidPerpetualPosition("take profit is on the wrong side of the entry")

    @property
    def notional(self) -> Decimal:
        return self.quantity * self.entry_price

    @property
    def initial_margin(self) -> Decimal:
        return self.notional / self.leverage

    def unrealized_pnl(self, mark_price: Decimal) -> Decimal:
        if mark_price <= 0:
            raise InvalidPerpetualPosition("mark price must be positive")
        move = mark_price - self.entry_price
        return move * self.quantity * (1 if self.side is PositionSide.LONG else -1)

    def funding_pnl(self, mark_price: Decimal, funding_rate: Decimal) -> Decimal:
        """Net account change at a funding event; positive rate means longs pay shorts."""
        if mark_price <= 0:
            raise InvalidPerpetualPosition("mark price must be positive")
        payment = mark_price * self.quantity * funding_rate
        return -payment if self.side is PositionSide.LONG else payment

    def estimated_liquidation_price(
        self,
        maintenance_margin_rate: Decimal,
        cumulative_maintenance_amount: Decimal = Decimal(0),
    ) -> Decimal:
        """Isolated estimate using the venue tier's rate and cumulative maintenance amount."""
        if not 0 <= maintenance_margin_rate < 1:
            raise InvalidPerpetualPosition("maintenance margin rate must be in [0, 1)")
        if cumulative_maintenance_amount < 0:
            raise InvalidPerpetualPosition("cumulative maintenance amount cannot be negative")
        margin_per_unit = self.isolated_margin / self.quantity
        if self.side is PositionSide.LONG:
            return (
                self.entry_price - margin_per_unit - cumulative_maintenance_amount / self.quantity
            ) / (1 - maintenance_margin_rate)
        return (
            self.entry_price + margin_per_unit + cumulative_maintenance_amount / self.quantity
        ) / (1 + maintenance_margin_rate)


@dataclass(slots=True)
class PerpetualLedger:
    """Single-position isolated-margin ledger, kept separate from the spot portfolio."""

    bot_id: UUID
    wallet_balance: Decimal
    position: LinearPerpetualPosition | None = None
    reserved_margin: Decimal = Decimal(0)
    realized_pnl: Decimal = Decimal(0)
    fees_paid: Decimal = Decimal(0)
    funding_paid: Decimal = Decimal(0)
    funding_received: Decimal = Decimal(0)
    mark_price: Decimal | None = None
    marked_at: datetime | None = None
    mark_source: str = "exchange_mark_price"
    maintenance_margin_rate: Decimal = Decimal(0)
    stop_order_client_id: str | None = None
    exchange_position_id: str | None = None
    exchange_liquidation_price: Decimal | None = None
    reconciled_at: datetime | None = None

    def __post_init__(self) -> None:
        if (
            self.wallet_balance < 0
            or self.reserved_margin < 0
            or self.reserved_margin > self.wallet_balance
            or self.fees_paid < 0
            or self.funding_paid < 0
            or self.funding_received < 0
            or (self.mark_price is not None and self.mark_price <= 0)
            or not 0 <= self.maintenance_margin_rate < 1
            or (
                self.exchange_liquidation_price is not None and self.exchange_liquidation_price <= 0
            )
            or (self.marked_at is not None and self.marked_at.tzinfo is None)
            or (self.reconciled_at is not None and self.reconciled_at.tzinfo is None)
        ):
            raise InvalidPerpetualPosition("perpetual ledger balances and charges are invalid")

    @property
    def available_balance(self) -> Decimal:
        return self.wallet_balance - self.reserved_margin

    @classmethod
    def new(cls, bot_id: UUID, initial_capital: Decimal) -> "PerpetualLedger":
        if initial_capital <= 0:
            raise InvalidPerpetualPosition("initial collateral must be positive")
        return cls(bot_id=bot_id, wallet_balance=initial_capital)

    def reserve(self, amount: Decimal) -> None:
        if amount <= 0 or amount > self.available_balance:
            raise InvalidPerpetualPosition("insufficient available collateral")
        self.reserved_margin += amount

    def release(self, amount: Decimal) -> None:
        if amount < 0 or amount > self.reserved_margin:
            raise InvalidPerpetualPosition("released collateral exceeds reserved margin")
        self.reserved_margin -= amount

    def open_position(
        self,
        side: PositionSide,
        quantity: Decimal,
        entry_price: Decimal,
        leverage: int,
        fee: Decimal = Decimal(0),
        stop_price: Decimal | None = None,
        take_profit_price: Decimal | None = None,
    ) -> LinearPerpetualPosition:
        if self.position is not None:
            raise InvalidPerpetualPosition("close the current position before opening another")
        if not 1 <= leverage <= MAX_PERPETUAL_LEVERAGE:
            raise InvalidPerpetualPosition(
                f"leverage must be between 1x and {MAX_PERPETUAL_LEVERAGE}x"
            )
        notional = quantity * entry_price
        margin = notional / leverage
        if fee < 0 or margin + fee > self.available_balance:
            raise InvalidPerpetualPosition("insufficient collateral for margin and entry fee")
        position = LinearPerpetualPosition(
            side,
            quantity,
            entry_price,
            leverage,
            margin,
            stop_price,
            take_profit_price,
        )
        self.wallet_balance -= margin + fee
        self.fees_paid += fee
        self.position = position
        self.exchange_position_id = None
        self.exchange_liquidation_price = None
        self.reconciled_at = None
        return position

    def increase_position(
        self,
        side: PositionSide,
        quantity: Decimal,
        entry_price: Decimal,
        leverage: int,
        fee: Decimal = Decimal(0),
    ) -> LinearPerpetualPosition:
        """Add to an existing same-side position, preserving its leverage."""
        current = self.position
        if current is None:
            return self.open_position(side, quantity, entry_price, leverage, fee)
        if current.side is not side or current.leverage != leverage:
            raise InvalidPerpetualPosition(
                "cannot increase position with different side or leverage"
            )
        if quantity <= 0 or entry_price <= 0 or fee < 0:
            raise InvalidPerpetualPosition("increase quantity, price, or fee is invalid")
        added_margin = quantity * entry_price / leverage
        if added_margin + fee > self.available_balance:
            raise InvalidPerpetualPosition("insufficient collateral for added margin and fee")
        total_quantity = current.quantity + quantity
        average_entry = (
            current.quantity * current.entry_price + quantity * entry_price
        ) / total_quantity
        self.wallet_balance -= added_margin + fee
        self.fees_paid += fee
        self.position = LinearPerpetualPosition(
            side,
            total_quantity,
            average_entry,
            leverage,
            current.isolated_margin + added_margin,
            current.stop_price,
            current.take_profit_price,
        )
        return self.position

    def close_position(
        self, quantity: Decimal, exit_price: Decimal, fee: Decimal = Decimal(0)
    ) -> Decimal:
        position = self.position
        if position is None or quantity <= 0 or quantity > position.quantity:
            raise InvalidPerpetualPosition("close quantity must be within the open position")
        if exit_price <= 0 or fee < 0:
            raise InvalidPerpetualPosition("exit price must be positive and fee non-negative")
        fraction = quantity / position.quantity
        released_margin = position.isolated_margin * fraction
        realized = position.unrealized_pnl(exit_price) * fraction - fee
        realized = max(realized, -released_margin)
        self.wallet_balance += released_margin + realized
        self.realized_pnl += realized
        self.fees_paid += fee
        remaining = position.quantity - quantity
        self.position = (
            None
            if remaining == 0
            else LinearPerpetualPosition(
                position.side,
                remaining,
                position.entry_price,
                position.leverage,
                position.isolated_margin - released_margin,
                position.stop_price,
                position.take_profit_price,
            )
        )
        if self.position is None:
            self.stop_order_client_id = None
            self.exchange_position_id = None
            self.exchange_liquidation_price = None
            self.reconciled_at = None
        return realized

    def apply_funding(
        self,
        mark_price: Decimal,
        funding_rate: Decimal,
        *,
        liquidation_fee_rate: Decimal = Decimal(0),
        cumulative_maintenance_amount: Decimal = Decimal(0),
        check_maintenance_margin: bool = False,
    ) -> Decimal:
        if self.position is None:
            return Decimal(0)
        if not 0 <= liquidation_fee_rate < 1 or cumulative_maintenance_amount < 0:
            raise InvalidPerpetualPosition("funding liquidation parameters are invalid")
        position = self.position
        payment = position.funding_pnl(mark_price, funding_rate)
        updated_margin = position.isolated_margin
        if payment < 0:
            # Binance charges funding to available Futures wallet balance first, then uses
            # position margin if that balance cannot cover the full settlement. Pending order
            # reservations are not available wallet balance and cannot be consumed here.
            charge = -payment
            from_wallet = min(charge, self.available_balance)
            self.wallet_balance -= from_wallet
            remaining_charge = charge - from_wallet
            from_margin = min(remaining_charge, position.isolated_margin)
            updated_margin -= from_margin
            settled_payment = -(from_wallet + from_margin)
        else:
            # Funding received is credited to the Futures wallet, not added to isolated margin.
            self.wallet_balance += payment
            settled_payment = payment
        liquidation_fee = position.quantity * mark_price * liquidation_fee_rate
        if settled_payment < 0:
            self.funding_paid -= settled_payment
        else:
            self.funding_received += settled_payment
        if updated_margin <= 0:
            # Any amount beyond available wallet balance and isolated margin is not charged to
            # another bot or allowed to create a negative account balance.
            payout = max(
                Decimal(0), updated_margin + position.unrealized_pnl(mark_price) - liquidation_fee
            )
            self.wallet_balance += payout
            self.realized_pnl += payout - position.isolated_margin
            self.fees_paid += liquidation_fee
            self.position = None
            self.stop_order_client_id = None
        else:
            self.position = replace(position, isolated_margin=updated_margin)
            if check_maintenance_margin and self.liquidation_breached(
                mark_price,
                self.maintenance_margin_rate,
                cumulative_maintenance_amount,
            ):
                self.liquidate(mark_price, liquidation_fee)
        return settled_payment

    def equity(self, mark_price: Decimal) -> Decimal:
        if self.position is None:
            # Reserved collateral is still part of wallet_balance; it is only unavailable
            # for new orders and must not be counted as a second asset.
            return self.wallet_balance
        return (
            self.wallet_balance
            + self.position.isolated_margin
            + self.position.unrealized_pnl(mark_price)
        )

    def mark(
        self,
        mark_price: Decimal,
        at: datetime,
        maintenance_margin_rate: Decimal,
        source: str = "exchange_mark_price",
    ) -> None:
        if at.tzinfo is None or not 0 <= maintenance_margin_rate < 1:
            raise InvalidPerpetualPosition("mark timestamp or maintenance rate is invalid")
        if mark_price <= 0:
            raise InvalidPerpetualPosition("mark price must be positive")
        self.mark_price = mark_price
        self.marked_at = at
        self.mark_source = source
        self.maintenance_margin_rate = maintenance_margin_rate

    @property
    def marked_equity(self) -> Decimal | None:
        return None if self.mark_price is None else self.equity(self.mark_price)

    def liquidation_estimate(
        self,
        maintenance_margin_rate: Decimal,
        cumulative_maintenance_amount: Decimal = Decimal(0),
    ) -> Decimal | None:
        if self.position is None:
            return None
        return self.position.estimated_liquidation_price(
            maintenance_margin_rate, cumulative_maintenance_amount
        )

    def liquidation_breached(
        self,
        mark_price: Decimal,
        maintenance_margin_rate: Decimal,
        cumulative_maintenance_amount: Decimal = Decimal(0),
    ) -> bool:
        if self.position is None:
            return False
        if not 0 <= maintenance_margin_rate < 1:
            raise InvalidPerpetualPosition("maintenance margin rate must be in [0, 1)")
        margin_equity = self.position.isolated_margin + self.position.unrealized_pnl(mark_price)
        if cumulative_maintenance_amount < 0:
            raise InvalidPerpetualPosition("cumulative maintenance amount cannot be negative")
        maintenance = max(
            Decimal(0),
            mark_price * self.position.quantity * maintenance_margin_rate
            - cumulative_maintenance_amount,
        )
        return margin_equity <= maintenance

    def liquidate(self, mark_price: Decimal, close_fee: Decimal = Decimal(0)) -> Decimal:
        if self.position is None:
            raise InvalidPerpetualPosition("there is no position to liquidate")
        return self.close_position(self.position.quantity, mark_price, close_fee)
