import msgspec
from typing import Optional, Union, Literal

class Trade(msgspec.Struct):
    """Represents a trade that occurred on the exchange.
    
    Args:
        time: The timestamp when the trade occurred.
        px: The price at which the trade occurred.
        is_buy: Whether the trade was a buy (True) or sell (False).
        sz: The quantity that was traded.
        is_maker: Whether the trade was as a maker (True) or taker (False).
    """
    time: float
    px: float
    is_buy: bool
    sz: float

class TradeMsg(msgspec.Struct, kw_only=True, tag="Trade"):
    """Represents a trade that occurred on the exchange.
    
    Args:
        id: Unique identifier for the trade.
        symbol: The trading pair symbol.
        time: The timestamp when the trade occurred.
        trades: List of individual trade objects.
    """
    id: Optional[str]=""
    symbol: str
    time: float

    trades: list[Trade]

class OrderbookMsg(msgspec.Struct, kw_only=True, tag="Orderbook"):
    """Represents the current state of the orderbook.
    
    Args:
        id: Unique identifier for the orderbook update.
        symbol: The trading pair symbol.
        time: The timestamp of this orderbook snapshot.
        bids: List of bid entries as [price, quantity] pairs, sorted by price in descending order.
        asks: List of ask entries as [price, quantity] pairs, sorted by price in ascending order.
        is_bbo: Whether this update contains only the best bid and offer.
        is_snapshot: Whether this is a complete orderbook snapshot.
    """
    id: Optional[str]=""
    symbol: str
    time: float

    bids: list[list[float, float]]
    asks: list[list[float, float]]
    is_bbo: bool
    is_snapshot: bool

class TickerMsg(msgspec.Struct, kw_only=True, tag="Ticker"):
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
    id: Optional[str]=""
    symbol: str
    time: float

    mark_px: float
    index_px: float
    funding_rate: float
    funding_time: float
    adv: float
    px_chg_24h: Optional[float] = None
    oi: Optional[float] = None


class PositionMsg(msgspec.Struct, kw_only=True, tag="Position"):
    """Represents a trading position.
    
    Args:
        id: Unique identifier for the position update.
        symbol: The trading pair symbol.
        time: The timestamp of this position information.
        px: The average entry price of the position.
        is_long: Whether the position is long (True) or short (False).
        sz: The position size.
        age: The age of the position in seconds.
    """
    id: Optional[str]=""
    symbol: str
    time: float

    px: float
    is_long: bool
    sz: float
    age: Optional[float] = None

class OrderMsg(msgspec.Struct, kw_only=True, tag="OrderStatus"):
    """Represents the current status of an order.
    
    Args:
        id: Unique identifier for the order update.
        symbol: The trading pair symbol.
        time: The timestamp of this order information.
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
    id: Optional[str]=""
    symbol: str
    time: float

    create_time_ms: float
    oid: str
    cloid: Optional[str] = None
    px: float
    is_buy: bool
    sz: float
    sz_rem: Optional[float] = None
    tif: Union[Literal["GTC"], Literal["IOC"], Literal["PO"], Literal["FOK"]]
    is_cancelled: bool
    is_reduce_only: bool

class ExecutionMsg(msgspec.Struct, kw_only=True, tag="Execution"):
    """Represents an execution (fill) of an order.
    
    Args:
        id: Unique identifier for the execution.
        symbol: The trading pair symbol.
        time: The timestamp when this execution occurred.
        px: The price at which the execution occurred.
        is_buy: Whether the execution was a buy (True) or sell (False).
        sz: The quantity that was executed.
        is_maker: Whether the execution was as a maker (True) or taker (False).
        fee_paid: The fee paid for this execution.
    """
    id: Optional[str]=""
    symbol: str
    time: float

    px: float
    is_buy: bool
    sz: float
    is_maker: bool
    fee_paid: Optional[float] = None

class AccountMsg(msgspec.Struct, kw_only=True, tag="Account"):
    """Represents account information.
    
    Args:
        id: Unique identifier for the account update.
        time: The timestamp of this account information.
        bal: The total balance of the account.
        im: Initial margin requirement.
        mm: Maintenance margin requirement.
        uPnl: Unrealized profit and loss.
    """
    id: Optional[str]=""
    time: float
    
    bal: float
    im: float
    mm: float
    uPnl: float

class HealthCheckMsg(msgspec.Struct, kw_only=True, tag="HealthCheck"):
    """Represents a health check message.
    
    Args:
        id: Unique identifier for the health check.
        time: The timestamp of this health check.
        next_check: The timestamp of the next health check.
    """
    id: Optional[str]=""
    time: float
    next_check: float

MarketDataEvent = Union[TradeMsg, OrderbookMsg, TickerMsg]
PrivateDataEvent = Union[PositionMsg, OrderMsg, ExecutionMsg, AccountMsg]
Event = Union[TradeMsg, OrderbookMsg, TickerMsg, PositionMsg, OrderMsg, ExecutionMsg, AccountMsg, HealthCheckMsg]