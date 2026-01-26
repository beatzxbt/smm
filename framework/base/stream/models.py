"""
Base stream data models and message types for exchange data.

Provides:
- Stream type enums (MarketDataStreamType, PrivateDataStreamType)
- Core message schemas (trades, orderbook, ticker, positions, orders, executions)
- Timing metadata (Moments) for message latency tracking
"""

from __future__ import annotations

from enum import StrEnum

from msgspec import Struct, field

from framework.base.common import Instrument, Venue
from mm_toolbox.time import time_ns


class MarketDataStreamType(StrEnum):
    """Types of market data streams available for subscription."""

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
    """Types of private data streams available for subscription."""

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
    """Lifecycle event types emitted by data streams."""

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


class Moments(Struct, frozen=True):
    """Timing information for a message.

    Args:
        exch_time_ms: The timestamp the message was sent from the exchange.
        recv_time_ms: The timestamp the message was received by the client.

    """

    exch_time_ns: int = field(default_factory=time_ns)
    recv_time_ns: int = field(default_factory=time_ns)

    def elapsed_since_exch_ns(self) -> int:
        """Returns the elapsed time in nanoseconds since the exchange sent the message."""
        return time_ns() - self.exch_time_ns

    def elapsed_since_recv_ns(self) -> int:
        """Returns the elapsed time in nanoseconds since the message was received by the client."""
        return time_ns() - self.recv_time_ns


class CoreSchema(Struct, frozen=True):
    """Base class for all schema classes."""

    moments: Moments
    venue: Venue
    instrument: Instrument


class Trade(Struct, frozen=True):
    """Represents a trade that occurred on the exchange."""

    time_ms: int
    price: float
    is_buy: bool
    size: float

    def __post_init__(self):
        if self.time_ms <= 0:
            raise ValueError(f"Invalid time_ms; expected >0 but got {self.time_ms}")
        if self.price <= 0.0:
            raise ValueError(f"Invalid price; expected >0 but got {self.price}")
        if self.size < 0.0:
            raise ValueError(f"Invalid size; expected >=0 but got {self.size}")

    @property
    def value(self) -> float:
        """Returns the value of the trade."""
        return self.price * self.size


class TradeMsg(CoreSchema, frozen=True, tag=True):
    """Represents a trade that occurred on the exchange."""

    trades: list[Trade]

    def __post_init__(self):
        """Validates and orders trade messages.

        Raises:
            ValueError: If trades is empty.
        """
        if not self.trades:
            raise ValueError("Invalid trades; expected non-empty list")
        self.trades.sort(key=lambda x: x.time_ms)


class OrderbookLevel(Struct, frozen=True):
    """Represents a single level in the orderbook."""

    price: float
    size: float
    num_orders: int = 1

    def __post_init__(self):
        if self.price <= 0.0:
            raise ValueError(f"Invalid price; expected >0 but got {self.price}")
        if self.size < 0.0:
            raise ValueError(f"Invalid size; expected >=0 but got {self.size}")
        if self.num_orders < 0:
            raise ValueError(
                f"Invalid num_orders; expected >=0 but got {self.num_orders}"
            )

    @property
    def value(self) -> float:
        """Returns the value of the orderbook level."""
        return self.price * self.size


class OrderbookMsg(CoreSchema, frozen=True, tag=True):
    """Represents the current state of the orderbook."""

    bids: list[OrderbookLevel]
    asks: list[OrderbookLevel]
    is_bbo: bool
    is_snapshot: bool

    def __post_init__(self):
        """Validates and orders orderbook messages.

        Raises:
            ValueError: If bids and asks are both empty.
        """
        if not self.bids and not self.asks:
            raise ValueError("Invalid orderbook; expected bids or asks")
        self.bids.sort(key=lambda x: x.price)
        self.asks.sort(key=lambda x: x.price)


class TickerMsg(CoreSchema, frozen=True, tag=True):
    """Represents the current ticker information for a symbol."""

    mark_price: float
    index_price: float
    funding_rate: float
    next_funding_time_ms: float
    open_interest: float
    avg_volume_24h: float
    price_chg_24h_pct: float

    def __post_init__(self):
        if self.mark_price < 0.0:
            raise ValueError(
                f"Invalid mark_price; expected >=0 but got {self.mark_price}"
            )
        if self.index_price < 0.0:
            raise ValueError(
                f"Invalid index_price; expected >=0 but got {self.index_price}"
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


class PositionMsg(CoreSchema, frozen=True, tag=True):
    """Represents a trading position."""

    price: float
    is_long: bool
    size: float

    @property
    def value(self) -> float:
        """Returns the value of the position."""
        return self.price * self.size


class OrderTimeInForce(StrEnum):
    """Represents the time in force of an order."""

    GTC = "GoodTillCanceled"
    IOC = "ImmediateOrCancel"
    PO = "PostOnly"
    FOK = "FillOrKill"


class Order(Struct):
    """Represents a last known state of a private (our own) order."""

    create_time_ms: float
    order_id: str
    price: float
    is_buy: bool
    size: float
    size_remaining: float
    tif: OrderTimeInForce
    is_cancelled: bool
    is_reduce_only: bool
    client_order_id: str | None = None

    @property
    def value(self) -> float:
        """Returns the value of the order."""
        return self.price * self.size


class OrderMsg(CoreSchema, frozen=True, tag=True):
    """Represents the current status of an order."""

    orders: list[Order]

    def __post_init__(self):
        """Validates order messages.

        Raises:
            ValueError: If orders is empty.
        """
        if not self.orders:
            raise ValueError("Invalid orders; expected non-empty list")


class Execution(Struct):
    """Represents an execution (fill) of an order."""

    exec_time_ms: float
    order_id: str
    price: float
    is_buy: bool
    size: float
    is_maker: bool
    fee_paid: float = 0.0
    client_order_id: str | None = None

    @property
    def value(self) -> float:
        """Returns the value of the execution."""
        return self.price * self.size


class ExecutionMsg(CoreSchema, frozen=True, tag=True):
    """Represents an execution (fill) of an order."""

    executions: list[Execution]

    def __post_init__(self):
        """Validates execution messages.

        Raises:
            ValueError: If executions is empty.
        """
        if not self.executions:
            raise ValueError("Invalid executions; expected non-empty list")


class AccountMsg(CoreSchema, frozen=True, tag=True):
    """Represents account information."""

    balance: float
    initial_margin: float
    maintenance_margin: float
    unrealized_pnl: float


type MarketDataMsg = TradeMsg | OrderbookMsg | TickerMsg
type PrivateDataMsg = PositionMsg | OrderMsg | ExecutionMsg | AccountMsg
type DataMsg = MarketDataMsg | PrivateDataMsg
type Msg = DataMsg | DataStreamEventMsg
