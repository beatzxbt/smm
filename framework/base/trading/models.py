import os
from typing import Literal, Optional, Self

import dotenv
from msgspec import Struct

from framework.base.common import Instrument
from framework.base.stream.models import (
    CoreSchema,
    Execution,
    Order,
    OrderbookLevel,
    OrderTimeInForce,
    Trade,
)


class Secret(Struct, frozen=True):
    name: str
    value: str

    @classmethod
    def load(cls, var_name: str) -> Self:
        dotenv.load_dotenv()
        if not (var_value := os.environ.get(var_name)):
            raise RuntimeError(f"Failed to load {var_name} from '.env';")
        return cls(name=var_name, value=var_value)

    @classmethod
    def set(cls, var_name: str, var_value: str) -> Self:
        """Used if generating new secrets through API"""
        os.environ[var_name] = var_value
        return cls(name=var_name, value=var_value)

    @classmethod
    def blank(cls) -> Self:
        return cls(name="", value="")


class CreateOrder(Struct):
    """Represents a create order action."""

    instrument: Instrument

    size: float
    is_buy: bool
    is_maker: bool
    tif: OrderTimeInForce
    reduce_only: bool
    price: Optional[float] = None
    client_order_id: Optional[str] = None

    def __post_init__(self):
        if self.size <= 0.0:
            raise ValueError("Size must be greater than 0")
        if self.price is not None and self.price <= 0.0:
            raise ValueError("Price must be greater than 0")
        if self.is_maker and self.price is None:
            raise ValueError("Maker orders must have a price")
        if not self.is_maker and self.tif == OrderTimeInForce.PO:
            raise ValueError("Taker orders cannot be PostOnly")


class AmendOrder(Struct):
    """Represents an amend order action."""

    instrument: Instrument

    size: float
    price: Optional[float] = None
    order_id: Optional[str] = None
    client_order_id: Optional[str] = None

    def __post_init__(self):
        if self.size <= 0.0:
            raise ValueError("Size must be greater than 0")
        if self.price is not None and self.price <= 0.0:
            raise ValueError("Price must be greater than 0")
        if self.order_id is None and self.client_order_id is None:
            raise ValueError(
                "Missing id; order_id or client_order_id must be provided but found neither"
            )


class CancelOrder(Struct):
    """Represents a cancel order action."""

    instrument: Instrument

    order_id: Optional[str] = None
    client_order_id: Optional[str] = None

    def __post_init__(self):
        if self.order_id is None and self.client_order_id is None:
            raise ValueError("Either order_id or client_order_id must be provided")


class CancelAllOrders(Struct):
    """Represents a cancel all orders action."""

    instrument: Instrument

    order_ids: Optional[list[str]] = None
    client_order_ids: Optional[list[str]] = None


type OrderAction = CreateOrder | AmendOrder | CancelOrder | CancelAllOrders


class CreateOrderResponse(CoreSchema):
    """Represents the response from the create order action."""

    trigger: CreateOrder
    order_id: Optional[str] = None
    client_order_id: Optional[str] = None


class AmendOrderResponse(CoreSchema):
    """Represents the response from the amend order action."""

    trigger: AmendOrder
    order_id: Optional[str] = None
    client_order_id: Optional[str] = None


class CancelOrderResponse(CoreSchema):
    """Represents the response from the cancel order action."""

    trigger: CancelOrder
    order_id: Optional[str] = None
    client_order_id: Optional[str] = None


class CancelAllOrdersResponse(CoreSchema):
    """Represents the response from the cancel all orders action."""

    # Some exchanges annoyingly do not return which orders were
    # cancelled, merely confirm that they were ALL cancelled. You can
    # check this success with 'response.is_successful'
    trigger: CancelAllOrders
    order_ids: Optional[list[str]] = None
    client_order_ids: Optional[list[str]] = None


class TradesResponse(CoreSchema):
    """Represents a list of trades.

    Trades are guaranteed to be in ascending order of time.
    """

    trades: list[Trade]

    def __post_init__(self):
        self.trades.sort(key=lambda x: x.time_ms)


class OrderbookResponse(CoreSchema):
    """Represents the current state of the orderbook.

    Orderbook levels are guaranteed to be in ascending order of price.
    """

    bids: list[OrderbookLevel]
    asks: list[OrderbookLevel]
    is_bbo: bool = False
    is_snapshot: bool = True

    def __post_init__(self):
        if not self.is_bbo:
            self.bids.sort(key=lambda x: x.price)
            self.asks.sort(key=lambda x: x.price)


class TickerResponse(CoreSchema):
    """Represents the current ticker information for a symbol."""

    mark_price: float
    index_price: float
    funding_rate: float
    next_funding_time_ms: float
    open_interest: Optional[float]
    avg_volume_24h: Optional[float]
    price_chg_24h: Optional[float]


class InstrumentInfoResponse(CoreSchema):
    """Represents the instrument information for a symbol."""

    tick_size: float
    lot_size: float
    max_taker_size: float
    max_maker_size: float


class OrdersResponse(CoreSchema):
    """Represents a list of orders."""

    orders: list[Order]


class PositionResponse(CoreSchema):
    """Represents a trading position."""

    price: float
    is_long: bool
    size: float

    @property
    def value(self) -> float:
        """Returns the value of the position."""
        return self.price * self.size


class ExecutionResponse(CoreSchema):
    """Represents an execution (fill) of an order."""

    executions: list[Execution]


class AccountResponse(CoreSchema):
    """Represents account information."""

    balance: float
    initial_margin: float
    maintenance_margin: float
    unrealized_pnl: float


class ClientResponseSuccess[T](Struct):
    """Represents a successful response from a client."""

    data: T
    is_successful: Literal[True] = True
    err_no: int = 0
    err_msg: str = ""


class ClientResponseFailure[T](Struct):
    """Represents a failed response from a client."""

    is_successful: Literal[False] = False
    err_no: int = 0
    err_msg: str = ""
    data: Optional[T] = None


# Union type helps with type inference for the ClientResponse[T] type
# for both is_successful result values.
type ClientResponse[T] = ClientResponseSuccess[T] | ClientResponseFailure[T]


type AnyOrderActionResponse = (
    CreateOrderResponse
    | AmendOrderResponse
    | CancelOrderResponse
    | CancelAllOrdersResponse
)
type AnyClientResponse = (
    AnyOrderActionResponse
    | TradesResponse
    | OrderbookResponse
    | TickerResponse
    | InstrumentInfoResponse
    | OrdersResponse
    | PositionResponse
    | ExecutionResponse
    | AccountResponse
)
