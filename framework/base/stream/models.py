"""Base stream data models and message types for exchange data.

Provides:
- Stream type enums for market and private subscriptions
- Immutable normalized payload structs for public and private stream data
- Envelope-backed message schemas shared across stream consumers
"""

from __future__ import annotations

from enum import StrEnum

from msgspec import Struct

from framework.base.common import ClientOrderId, Instrument, OrderId, Venue
from framework.base.schema import EnvelopeSchema


class MarketDataStreamType(StrEnum):
    """Enumeration of market data streams available for subscription.

    Attributes:
        TICKER: Ticker snapshot or delta updates.
        TRADES: Public trade events.
        TOP_OF_ORDERBOOK: Best bid and offer updates.
        FULL_ORDERBOOK: Full depth orderbook updates.
    """

    TICKER = "Ticker"
    TRADES = "Trades"
    TOP_OF_ORDERBOOK = "TopOfOrderBook"
    FULL_ORDERBOOK = "FullOrderBook"


ALL_MARKET_DATA_STREAM_TYPES: set[MarketDataStreamType] = {
    MarketDataStreamType.TICKER,
    MarketDataStreamType.TRADES,
    MarketDataStreamType.TOP_OF_ORDERBOOK,
    MarketDataStreamType.FULL_ORDERBOOK,
}


class PrivateDataStreamType(StrEnum):
    """Enumeration of private data streams available for subscription.

    Attributes:
        ORDER: Order lifecycle updates.
        POSITION: Position state updates.
        EXECUTION: Fill and execution updates.
        ACCOUNT: Account balance and margin updates.
    """

    ORDER = "Order"
    POSITION = "Position"
    EXECUTION = "Execution"
    ACCOUNT = "Account"


ALL_PRIVATE_DATA_STREAM_TYPES: set[PrivateDataStreamType] = {
    PrivateDataStreamType.ORDER,
    PrivateDataStreamType.POSITION,
    PrivateDataStreamType.EXECUTION,
    PrivateDataStreamType.ACCOUNT,
}


type StreamType = MarketDataStreamType | PrivateDataStreamType


class DataStreamEvent(StrEnum):
    """Enumeration of lifecycle events emitted by data streams.

    Attributes:
        START: Stream startup event.
        STOP: Stream shutdown event.
        SUBSCRIBE: Subscription change event.
        UNSUBSCRIBE: Unsubscription change event.
        HEARTBEAT: Health or heartbeat event.
    """

    START = "START"
    STOP = "STOP"
    SUBSCRIBE = "SUBSCRIBE"
    UNSUBSCRIBE = "UNSUBSCRIBE"
    HEARTBEAT = "HEARTBEAT"


class DataStreamEventMsg(Struct, frozen=True, tag=True):
    """Represents a lifecycle event emitted by a data stream.

    Args:
        time_ms (int): Event timestamp in milliseconds.
        venue (Venue): The exchange venue this event applies to.
        event (DataStreamEvent): The lifecycle event type.
        changes (dict[StreamType, Instrument]): Stream changes for the event.
        state (dict[StreamType, Instrument]): Current subscription state snapshot.
        time_next_check_ms (int | None): Next heartbeat check timestamp in milliseconds.
    """

    time_ms: int
    venue: Venue
    event: DataStreamEvent
    changes: dict[StreamType, Instrument]
    state: dict[StreamType, Instrument]
    time_next_check_ms: int | None = None


class StreamSchema(EnvelopeSchema, frozen=True):
    """Base class for all normalized stream messages.

    Shared fields capture timing, instrument scope, correlation metadata, and
    whether the payload represents a stream snapshot/reset boundary instead of
    an incremental update.

    Attributes:
        is_snapshot: Whether this message represents a stream reset boundary.
    """

    is_snapshot: bool

    def __post_init__(self) -> None:
        """Validate stream envelope correlation invariants.

        Raises:
            ValueError: If the message id is not anchored to message receive time.
        """
        if __debug__ and self.id.recv_time_ns != self.moments.recv_time_ns:
            raise ValueError(
                "Invalid id.recv_time_ns; expected to match moments.recv_time_ns"
            )


class Trade(Struct, frozen=True):
    """Represents a trade that occurred on the exchange.

    Attributes:
        time_ms: Exchange trade timestamp in milliseconds.
        price: Executed trade price.
        is_buy: Whether the aggressing side was a buyer.
        size: Executed trade quantity. Must be greater than zero.
    """

    time_ms: int
    price: float
    is_buy: bool
    size: float

    def __post_init__(self) -> None:
        """Validate trade fields.

        Raises:
            ValueError: If the trade time, price, or size is invalid.
        """
        if self.time_ms <= 0:
            raise ValueError(f"Invalid time_ms; expected >0 but got {self.time_ms}")
        if self.price <= 0.0:
            raise ValueError(f"Invalid price; expected >0 but got {self.price}")
        if self.size <= 0.0:
            raise ValueError(f"Invalid size; expected >0 but got {self.size}")

    @property
    def notional_size(self) -> float:
        """Return the notional size of the trade.

        Returns:
            float: Product of the trade price and size.
        """
        return self.price * self.size

    def as_tuple(self) -> tuple[int, float, bool, float]:
        """Return the trade encoded as a tuple.

        Returns:
            tuple[int, float, bool, float]: Tuple of trade fields in wire order.
        """
        return (self.time_ms, self.price, self.is_buy, self.size)


class TradeMsg(StreamSchema, frozen=True, tag=True):
    """Represents a batch of normalized trade events.

    Attributes:
        trades: Trades in increasing timestamp order.
    """

    trades: tuple[Trade, ...]

    def __post_init__(self) -> None:
        """Validate trade message ordering.

        Raises:
            ValueError: If trades is empty or out of chronological order.
        """
        super().__post_init__()

        num_trades = len(self.trades)
        match num_trades:
            case 0:
                raise ValueError("Invalid trades; expected non-empty collection")
            case 1:
                return None
            case _:
                prev_trade_time_ms = self.trades[0].time_ms
                for trade in self.trades[1:]:
                    curr_trade_time_ms = trade.time_ms
                    if curr_trade_time_ms < prev_trade_time_ms:
                        raise ValueError(
                            "Invalid trades; expected time_ms in increasing order"
                        )
                    prev_trade_time_ms = curr_trade_time_ms


class OrderbookLevel(Struct, frozen=True):
    """Represents a single level in the orderbook.

    Attributes:
        price: Price for the level.
        size: Aggregated quantity resting at the level.
        num_orders: Number of orders aggregated into the level.
    """

    price: float
    size: float
    num_orders: int = 1

    def __post_init__(self) -> None:
        """Validate orderbook level fields.

        Raises:
            ValueError: If the level price, size, or order count is invalid.
        """
        if self.price <= 0.0:
            raise ValueError(f"Invalid price; expected >0 but got {self.price}")
        if self.size < 0.0:
            raise ValueError(f"Invalid size; expected >=0 but got {self.size}")
        if self.num_orders < 0:
            raise ValueError(
                f"Invalid num_orders; expected >=0 but got {self.num_orders}"
            )

    @property
    def notional_size(self) -> float:
        """Return the notional size of the orderbook level.

        Returns:
            float: Product of the level price and size.
        """
        return self.price * self.size

    def as_tuple(self) -> tuple[float, float, int]:
        """Return the orderbook level encoded as a tuple.

        Returns:
            tuple[float, float, int]: Tuple of level fields in wire order.
        """
        return (self.price, self.size, self.num_orders)


class OrderbookMsg(StreamSchema, frozen=True, tag=True):
    """Represents the current state of the orderbook.

    Attributes:
        bids: Bid levels in strictly increasing price order.
        asks: Ask levels in strictly increasing price order.
        is_bbo: Whether the payload contains only best bid/offer data.
    """

    bids: tuple[OrderbookLevel, ...]
    asks: tuple[OrderbookLevel, ...]
    is_bbo: bool

    def __post_init__(self) -> None:
        """Validate orderbook message structure and ordering.

        Raises:
            ValueError: If the BBO cardinality or side ordering is invalid.
        """
        super().__post_init__()
        len_bids = len(self.bids)
        len_asks = len(self.asks)
        if self.is_bbo and (len_bids > 1 or len_asks > 1):
            raise ValueError(
                "Invalid orderbook; expected at most one level per side for BBO"
            )

        if len_bids > 1:
            prev_bid_price = self.bids[0].price
            for level in self.bids[1:]:
                if level.price <= prev_bid_price:
                    raise ValueError(
                        "Invalid bids; expected strictly increasing prices"
                    )
                prev_bid_price = level.price

        if len_asks > 1:
            prev_ask_price = self.asks[0].price
            for level in self.asks[1:]:
                if level.price <= prev_ask_price:
                    raise ValueError(
                        "Invalid asks; expected strictly increasing prices"
                    )
                prev_ask_price = level.price


class TickerMsg(StreamSchema, frozen=True, tag=True):
    """Represents current ticker information for an instrument.

    Attributes:
        mark_price: Current mark price.
        index_price: Current index price.
        funding_rate: Current funding rate.
        funding_period_min: Funding interval in minutes.
        next_funding_time_ms: Next funding timestamp in milliseconds.
        open_interest: Current open interest.
        avg_volume_24h: Rolling 24-hour average traded volume.
        price_chg_24h_pct: Rolling 24-hour percent price change.
    """

    mark_price: float
    index_price: float
    funding_rate: float
    funding_period_min: int
    next_funding_time_ms: float
    open_interest: float
    avg_volume_24h: float
    price_chg_24h_pct: float

    def __post_init__(self) -> None:
        """Validate ticker fields.

        Raises:
            ValueError: If any ticker field violates its expected range.
        """
        super().__post_init__()
        if self.mark_price < 0.0:
            raise ValueError(
                f"Invalid mark_price; expected >=0 but got {self.mark_price}"
            )
        if self.index_price < 0.0:
            raise ValueError(
                f"Invalid index_price; expected >=0 but got {self.index_price}"
            )
        if self.funding_period_min <= 0:
            raise ValueError(
                f"Invalid funding_period_min; expected >0 but got {self.funding_period_min}"
            )
        if self.next_funding_time_ms < 0:
            raise ValueError(
                f"Invalid next_funding_time_ms; expected >=0 but got {self.next_funding_time_ms}"
            )
        if self.open_interest < 0.0:
            raise ValueError(
                f"Invalid open_interest; expected >=0 but got {self.open_interest}"
            )
        if self.avg_volume_24h < 0.0:
            raise ValueError(
                f"Invalid avg_volume_24h; expected >=0 but got {self.avg_volume_24h}"
            )
        if self.price_chg_24h_pct < -100.0:
            raise ValueError(
                f"Invalid price_chg_24h_pct; expected >=-100.0 but got {self.price_chg_24h_pct}"
            )


class PositionMsg(StreamSchema, frozen=True, tag=True):
    """Represents a trading position.

    Attributes:
        price: Average entry or mark price for the position.
        is_long: Whether the position is long.
        size: Position size in instrument units.
    """

    price: float
    is_long: bool
    size: float

    def __post_init__(self) -> None:
        """Validate position fields.

        Raises:
            ValueError: If the position price or size is invalid.
        """
        super().__post_init__()
        if self.price <= 0.0:
            raise ValueError(f"Invalid price; expected >0 but got {self.price}")
        if self.size < 0.0:
            raise ValueError(f"Invalid size; expected >=0 but got {self.size}")

    @property
    def notional_size(self) -> float:
        """Return the notional size of the position.

        Returns:
            float: Product of the position price and size.
        """
        return self.price * self.size


class OrderTimeInForce(StrEnum):
    """Enumeration of supported order time-in-force policies.

    Attributes:
        GTC: Good-till-cancelled order.
        IOC: Immediate-or-cancel order.
        PO: Post-only order.
        FOK: Fill-or-kill order.
    """

    GTC = "GoodTillCanceled"
    IOC = "ImmediateOrCancel"
    PO = "PostOnly"
    FOK = "FillOrKill"


class Order(Struct, frozen=True):
    """Represents the last known state of a private order.

    Attributes:
        create_time_ms: Order creation timestamp in milliseconds.
        order_id: Exchange-assigned order identifier.
        price: Order price.
        is_buy: Whether the order is a buy order.
        size: Original order size.
        size_remaining: Remaining unfilled order size.
        tif: Time-in-force policy.
        is_cancelled: Whether the order has been cancelled.
        is_reduce_only: Whether the order may only reduce exposure.
        client_order_id: Optional client-assigned order identifier.
    """

    create_time_ms: float
    order_id: OrderId
    price: float
    is_buy: bool
    size: float
    size_remaining: float
    tif: OrderTimeInForce
    is_cancelled: bool
    is_reduce_only: bool
    client_order_id: ClientOrderId | None = None

    def __post_init__(self) -> None:
        """Validate order fields.

        Raises:
            ValueError: If the order timestamps or sizes are invalid.
        """
        if self.create_time_ms <= 0.0:
            raise ValueError(
                f"Invalid create_time_ms; expected >0 but got {self.create_time_ms}"
            )
        if not self.order_id:
            raise ValueError("Invalid order_id; expected non-empty string")
        if self.price <= 0.0:
            raise ValueError(f"Invalid price; expected >0 but got {self.price}")
        if self.size < 0.0:
            raise ValueError(f"Invalid size; expected >=0 but got {self.size}")
        if self.size_remaining < 0.0:
            raise ValueError(
                f"Invalid size_remaining; expected >=0 but got {self.size_remaining}"
            )
        if self.size_remaining > self.size:
            raise ValueError(
                "Invalid size_remaining; expected <= size but got "
                f"{self.size_remaining} > {self.size}"
            )

    @property
    def notional_size(self) -> float:
        """Return the notional size of the order.

        Returns:
            float: Product of the order price and size.
        """
        return self.price * self.size


class OrderMsg(StreamSchema, frozen=True, tag=True):
    """Represents a batch of normalized order updates.

    Attributes:
        orders: Non-empty collection of order states.
    """

    orders: tuple[Order, ...]

    def __post_init__(self) -> None:
        """Validate order message contents.

        Raises:
            ValueError: If the order collection is empty.
        """
        super().__post_init__()
        if not self.orders:
            raise ValueError("Invalid orders; expected non-empty collection")


class Execution(Struct, frozen=True):
    """Represents an execution fill for an order.

    Attributes:
        exec_time_ms: Execution timestamp in milliseconds.
        order_id: Exchange-assigned order identifier.
        price: Execution price.
        is_buy: Whether the fill was on the buy side.
        size: Executed quantity.
        is_maker: Whether the fill provided liquidity.
        fee_paid: Fee paid for the execution.
        client_order_id: Optional client-assigned order identifier.
    """

    exec_time_ms: float
    order_id: OrderId
    price: float
    is_buy: bool
    size: float
    is_maker: bool
    fee_paid: float = 0.0
    client_order_id: ClientOrderId | None = None

    def __post_init__(self) -> None:
        """Validate execution fields.

        Raises:
            ValueError: If the execution timestamps or sizes are invalid.
        """
        if self.exec_time_ms <= 0.0:
            raise ValueError(
                f"Invalid exec_time_ms; expected >0 but got {self.exec_time_ms}"
            )
        if not self.order_id:
            raise ValueError("Invalid order_id; expected non-empty string")
        if self.price <= 0.0:
            raise ValueError(f"Invalid price; expected >0 but got {self.price}")
        if self.size < 0.0:
            raise ValueError(f"Invalid size; expected >=0 but got {self.size}")

    @property
    def notional_size(self) -> float:
        """Return the notional size of the execution.

        Returns:
            float: Product of the execution price and size.
        """
        return self.price * self.size


class ExecutionMsg(StreamSchema, frozen=True, tag=True):
    """Represents a batch of normalized execution updates.

    Attributes:
        executions: Executions in increasing timestamp order.
    """

    executions: tuple[Execution, ...]

    def __post_init__(self) -> None:
        """Validate execution message ordering.

        Raises:
            ValueError: If executions is empty or out of chronological order.
        """
        super().__post_init__()
        if not self.executions:
            raise ValueError("Invalid executions; expected non-empty collection")

        prev_exec_time_ms = self.executions[0].exec_time_ms
        for execution in self.executions[1:]:
            if execution.exec_time_ms < prev_exec_time_ms:
                raise ValueError(
                    "Invalid executions; expected exec_time_ms in increasing order"
                )
            prev_exec_time_ms = execution.exec_time_ms


class Balance(Struct, frozen=True):
    """Represents a currency balance snapshot for an account.

    Attributes:
        currency: Asset or settlement currency code.
        amount: Total balance amount for the currency.
    """

    currency: str
    amount: float


class AccountMsg(StreamSchema, frozen=True, tag=True):
    """Represents account balance and margin information.

    Attributes:
        balances: Currency balances keyed by instrument scope.
        initial_margin: Initial margin currently reserved.
        maintenance_margin: Maintenance margin currently required.
        unrealized_pnl: Unrealized profit and loss.
    """

    balances: dict[Instrument, Balance]
    initial_margin: float
    maintenance_margin: float
    unrealized_pnl: float


type MarketDataMsg = TradeMsg | OrderbookMsg | TickerMsg
type PrivateDataMsg = PositionMsg | OrderMsg | ExecutionMsg | AccountMsg
type DataMsg = MarketDataMsg | PrivateDataMsg
type Msg = DataMsg | DataStreamEventMsg
