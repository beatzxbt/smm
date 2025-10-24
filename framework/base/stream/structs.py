from enum import StrEnum
from typing import Optional

from msgspec import Struct, field

from framework.base.common import Instrument, Venue
from framework.base.tools.time import time_ns


class Moments(Struct):
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


class CoreSchema(Struct):
    """Base class for all schema classes."""

    moments: Moments
    venue: Venue
    instrument: Instrument


class Trade(Struct):
    """Represents a trade that occurred on the exchange."""

    time_ms: int
    price: float
    is_buy: bool
    size: float

    @property
    def value(self) -> float:
        """Returns the value of the trade."""
        return self.price * self.size


class TradeMsg(CoreSchema, tag=True):
    """Represents a trade that occurred on the exchange."""

    trades: list[Trade]

    def __post_init__(self):
        self.trades.sort(key=lambda x: x.time_ms)


class OrderbookLevel(Struct):
    """Represents a single level in the orderbook."""

    price: float
    size: float
    num_orders: int = 1

    @property
    def value(self) -> float:
        """Returns the value of the orderbook level."""
        return self.price * self.size


class OrderbookMsg(CoreSchema, tag=True):
    """Represents the current state of the orderbook."""

    bids: list[OrderbookLevel]
    asks: list[OrderbookLevel]
    is_bbo: bool
    is_snapshot: bool

    def __post_init__(self):
        self.bids.sort(key=lambda x: x.price)
        self.asks.sort(key=lambda x: x.price)


class TickerMsg(CoreSchema, tag=True):
    """Represents the current ticker information for a symbol."""

    mark_price: float
    index_price: float
    funding_rate: float
    next_funding_time_ms: float
    open_interest: float
    avg_volume_24h: float
    price_chg_24h_pct: float


class PositionMsg(CoreSchema, tag=True):
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


class OrderMsg(CoreSchema, tag=True):
    """Represents the current status of an order."""

    orders: list[Order]


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


class ExecutionMsg(CoreSchema, tag=True):
    """Represents an execution (fill) of an order."""

    executions: list[Execution]


class AccountMsg(CoreSchema, tag=True):
    """Represents account information."""

    balance: float
    initial_margin: float
    maintenance_margin: float
    unrealized_pnl: float


class HeartbeatMsg(Struct, tag=True):
    """Represents a heartbeat message."""

    venue: Venue
    time_now_ms: int
    time_next_check_ms: int


type MarketDataMsg = TradeMsg | OrderbookMsg | TickerMsg
type PrivateDataMsg = PositionMsg | OrderMsg | ExecutionMsg | AccountMsg
type DataMsg = MarketDataMsg | PrivateDataMsg | HeartbeatMsg
