import msgspec
from enum import IntEnum
from typing import Optional, Union

from framework.tools.time import time_ns

class Exchange(IntEnum):
    """Represents an exchange.
    
    Args:
        BINANCE: Binance.
        BYBIT: Bybit.
        OKX: OKX.
        HYPERLIQUID: Hyperliquid.
    """
    BINANCE = 0
    BYBIT = 1
    OKX = 2
    HYPERLIQUID = 3
    EXTENDED = 4
    DYDX = 5
    PARADEX = 6

class Symbol(str):
    """Represents a symbol.
    
    Args:
        symbol: The symbol.
    """
    pass

class InternalMsg(msgspec.Struct):
    """Represents a message that is internal to the framework.
    
    Args:
        local_time_ns: The timestamp when the message was created.
        exchange: The exchange that the message is from.
        symbol: The symbol that the message is for.
    """
    exchange: Exchange
    symbol: Symbol = msgspec.field(default=Symbol(""))
    local_time_ns: int = msgspec.field(default=time_ns())
    extern_latency_us: Optional[int] = msgspec.field(default=0)

class Trade(msgspec.Struct, array_like=True, kw_only=True):
    """Represents a trade that occurred on the exchange.
    
    Args:
        time: The timestamp when the trade occurred.
        px: The price at which the trade occurred.
        is_buy: Whether the trade was a buy (True) or sell (False).
        sz: The quantity that was traded.
    """
    time: float
    px: float
    is_buy: bool
    sz: float

class TradeMsg(InternalMsg, array_like=True, kw_only=True, tag=True):
    """Represents a trade that occurred on the exchange.
    
    Args:
        id: Unique identifier for the trade.
        symbol: The trading pair symbol.
        time: The timestamp when the trade occurred.
        trades: List of individual trade objects.
    """
    trades: list[Trade]

# There is no difference between a dataclass and a msgspec.Struct, though
# there is a ~4x speed increment when creating these Structs.
class OrderbookLevel(msgspec.Struct, array_like=True, kw_only=True):
    """Represents a single level in the orderbook.
    
    Args:
        px: Price level.
        sz: Total size at this price level.
        num_orders: Number of orders at this price level.
    """
    px: float
    sz: float
    num_orders: Optional[int] = 1

class OrderbookMsg(InternalMsg, array_like=True, kw_only=True, tag=True):
    """Represents the current state of the orderbook.
    
    Args:
        bids: List of bid entries.
        asks: List of ask entries.
        is_bbo: Whether this update contains only the best bid and offer.
        is_snapshot: Whether this is a complete orderbook snapshot.
    """
    bids: list[OrderbookLevel]
    asks: list[OrderbookLevel]
    is_bbo: bool
    is_snapshot: bool

class TickerMsg(InternalMsg, array_like=True, kw_only=True, tag=True):
    """Represents the current ticker information for a symbol.
    
    Args:
        id: Unique identifier for the ticker update.
        symbol: The trading pair symbol.
        time: The timestamp of this ticker information.
        mark_px: The mark price.
        index_px: The index price.
        funding_rate: The current funding rate.
        funding_time: The timestamp of the next funding.
        adv: Average daily volume.
        px_chg_24h: Price change in the last 24 hours.
        oi: Open interest.
    """
    mark_px: float
    index_px: float
    funding_rate: float
    funding_time: float
    adv: float
    px_chg_24h: Optional[float] = None
    oi: Optional[float] = None


class PositionMsg(InternalMsg, array_like=True, kw_only=True, tag=True):
    """Represents a trading position.
    
    Args:
        px: The average entry price of the position.
        is_long: Whether the position is long (True) or short (False).
        sz: The position size.
        age: The age of the position in seconds.
    """
    px: float
    is_long: bool
    sz: float
    age: Optional[float] = None

class OrderTimeInForce(IntEnum):
    """Represents the time in force policy of an order.
    
    Args:
        GTC: Good till canceled.
        IOC: Immediate or cancel.
        PO: Post only.
        FOK: Fill or kill.
    """
    GTC = 0
    IOC = 1
    PO = 2
    FOK = 3

class OrderMsg(InternalMsg, array_like=True, kw_only=True, tag=True):
    """Represents the current status of an order.
    
    Args:
        create_time_ms: The timestamp when the order was created.
        oid: The exchange order ID.
        cloid: The client order ID.
        px: The price specified in the order.
        is_buy: Whether the order is a buy (True) or sell (False).
        sz: The quantity specified in the order.
        sz_rem: The remaining quantity to be filled.
        tif: The time in force policy of the order.
        is_reduce_only: Whether the order is reduce-only.
    """
    create_time_ms: float
    oid: str
    cloid: Optional[str] = None
    px: float
    is_buy: bool
    sz: float
    sz_rem: Optional[float] = None
    tif: OrderTimeInForce
    is_cancelled: bool
    is_reduce_only: bool

class ExecutionMsg(InternalMsg, array_like=True, kw_only=True, tag=True):
    """Represents an execution (fill) of an order.
    
    Args:
        px: The price at which the execution occurred.
        is_buy: Whether the execution was a buy (True) or sell (False).
        sz: The quantity that was executed.
        is_maker: Whether the execution was as a maker (True) or taker (False).
        fee_paid: The fee paid for this execution.
    """
    px: float
    is_buy: bool
    sz: float
    is_maker: bool
    fee_paid: Optional[float] = None

class AccountMsg(InternalMsg, array_like=True, kw_only=True, tag=True):
    """Represents account information.
    
    Args:
        bal: The total balance of the account.
        im: Initial margin requirement.
        mm: Maintenance margin requirement.
        upnl: Unrealized profit and loss.
    """
    bal: float
    im: float
    mm: float
    upnl: float

class HeartbeatMsg(InternalMsg, array_like=True, kw_only=True, tag=True):
    """Represents a heartbeat message.
    
    Args:
        time: The timestamp of this heartbeat in seconds.
        next_check: The timestamp of the next heartbeat in seconds.
    """
    time: float
    next_check: float

MarketDataEvent = Union[TradeMsg, OrderbookMsg, TickerMsg]
PrivateDataEvent = Union[PositionMsg, OrderMsg, ExecutionMsg, AccountMsg]
Event = Union[TradeMsg, OrderbookMsg, TickerMsg, PositionMsg, OrderMsg, ExecutionMsg, AccountMsg, HeartbeatMsg]