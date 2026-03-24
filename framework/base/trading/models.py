"""Trading model primitives and response schemas.

Usage: defines Secret helpers, order actions, and response data models used by
clients/exchanges. Components: Secret, order actions, response schemas, and
response unions.
"""

from __future__ import annotations

import os
from enum import Enum
from typing import Literal, Optional, Self, TypeGuard

import dotenv
from msgspec import Struct, field

from framework.base.common import ClientOrderId, Instrument, OrderId, Venue
from framework.base.schema import EnvelopeSchema, MessageId
from framework.base.stream.models import (
    Execution,
    Order,
    OrderbookLevel,
    OrderTimeInForce,
    Trade,
)
from mm_toolbox.time import time_ns


class Secret(Struct, frozen=True):
    """Stores credential name/value pairs loaded from environment.

    Attributes:
        name (str): Environment variable name for the secret.
        value (str): Secret value or empty string for blank secrets.
    """

    name: str
    value: str

    @classmethod
    def load(cls, var_name: str) -> Self:
        """Load a secret from the environment.

        Args:
            var_name (str): Environment variable name to load.

        Returns:
            Secret: Loaded secret with the provided name and value.

        Raises:
            RuntimeError: If the environment variable is missing or empty.
        """
        dotenv.load_dotenv()
        if not (var_value := os.environ.get(var_name)):
            raise RuntimeError(f"Failed to load {var_name} from '.env';")
        return cls(name=var_name, value=var_value)

    @classmethod
    def maybe_load(cls, var_name: str) -> Self:
        """Load a secret from the environment or return blank.

        Args:
            var_name (str): Environment variable name to load.

        Returns:
            Secret: Loaded secret or a blank secret if missing/empty.
        """
        dotenv.load_dotenv()
        if not (var_value := os.environ.get(var_name)):
            return cls.blank()
        return cls(name=var_name, value=var_value)

    @classmethod
    def set(cls, var_name: str, var_value: str) -> Self:
        """Set a secret in the environment and return it.

        Args:
            var_name (str): Environment variable name to set.
            var_value (str): Value to store in the environment.

        Returns:
            Secret: Secret with the provided name and value.
        """
        os.environ[var_name] = var_value
        return cls(name=var_name, value=var_value)

    @classmethod
    def blank(cls) -> Self:
        """Return a blank secret.

        Returns:
            Secret: Secret with empty name and value.
        """
        return cls(name="", value="")

    def is_blank(self) -> bool:
        """Check whether the secret is blank.

        Returns:
            bool: True if name and value are empty strings.
        """
        return self.name == "" and self.value == ""


class CreateOrder(Struct):
    """Represents a create-order action request.

    Attributes:
        instrument: Instrument the order targets.
        size: Requested order size.
        is_buy: Whether the order is a buy.
        is_maker: Whether the order should rest as maker liquidity.
        tif: Time-in-force policy for the order.
        reduce_only: Whether the order may only reduce exposure.
        price: Optional limit price.
        client_order_id: Optional client-assigned identifier.
        id: Unique identifier for this action message.
        origin_id: Identifier of the upstream event that caused this action.
    """

    instrument: Instrument

    size: float
    is_buy: bool
    is_maker: bool
    tif: OrderTimeInForce
    reduce_only: bool
    price: Optional[float] = None
    client_order_id: Optional[ClientOrderId] = None
    id: MessageId = field(default_factory=MessageId)
    origin_id: MessageId | None = None

    def __post_init__(self) -> None:
        """Validate the create-order request.

        Raises:
            ValueError: If the order size, price, or maker/taker flags are invalid.
        """
        if self.origin_id is None:
            self.origin_id = self.id
        if self.size <= 0.0:
            raise ValueError("Size must be greater than 0")
        if self.price is not None and self.price <= 0.0:
            raise ValueError("Price must be greater than 0")
        if self.is_maker and self.price is None:
            raise ValueError("Maker orders must have a price")
        if not self.is_maker and self.tif == OrderTimeInForce.PO:
            raise ValueError("Taker orders cannot be PostOnly")


class AmendOrder(Struct):
    """Represents an amend-order action request.

    Attributes:
        instrument: Instrument the order targets.
        size: Replacement order size.
        price: Optional replacement price.
        order_id: Optional exchange-assigned order identifier.
        client_order_id: Optional client-assigned order identifier.
        id: Unique identifier for this action message.
        origin_id: Identifier of the upstream event that caused this action.
    """

    instrument: Instrument

    size: float
    price: Optional[float] = None
    order_id: Optional[OrderId] = None
    client_order_id: Optional[ClientOrderId] = None
    id: MessageId = field(default_factory=MessageId)
    origin_id: MessageId | None = None

    def __post_init__(self) -> None:
        """Validate the amend-order request.

        Raises:
            ValueError: If the replacement fields are invalid or no identifier exists.
        """
        if self.origin_id is None:
            self.origin_id = self.id
        if self.size <= 0.0:
            raise ValueError("Size must be greater than 0")
        if self.price is not None and self.price <= 0.0:
            raise ValueError("Price must be greater than 0")
        if self.order_id is None and self.client_order_id is None:
            raise ValueError(
                "Missing id; order_id or client_order_id must be provided but found neither"
            )


class CancelOrder(Struct):
    """Represents a cancel-order action request.

    Attributes:
        instrument: Instrument the order targets.
        order_id: Optional exchange-assigned order identifier.
        client_order_id: Optional client-assigned order identifier.
        id: Unique identifier for this action message.
        origin_id: Identifier of the upstream event that caused this action.
    """

    instrument: Instrument

    order_id: Optional[OrderId] = None
    client_order_id: Optional[ClientOrderId] = None
    id: MessageId = field(default_factory=MessageId)
    origin_id: MessageId | None = None

    def __post_init__(self) -> None:
        """Validate the cancel-order request.

        Raises:
            ValueError: If neither order identifier is provided.
        """
        if self.origin_id is None:
            self.origin_id = self.id
        if self.order_id is None and self.client_order_id is None:
            raise ValueError("Either order_id or client_order_id must be provided")


class CancelAllOrders(Struct):
    """Represents a cancel-all-orders action request.

    Attributes:
        instrument: Instrument scope for the cancellation.
        order_ids: Optional exchange order identifiers to cancel.
        client_order_ids: Optional client order identifiers to cancel.
        id: Unique identifier for this action message.
        origin_id: Identifier of the upstream event that caused this action.
    """

    instrument: Instrument

    order_ids: Optional[list[OrderId]] = None
    client_order_ids: Optional[list[ClientOrderId]] = None
    id: MessageId = field(default_factory=MessageId)
    origin_id: MessageId | None = None

    def __post_init__(self) -> None:
        """Populate default causal identifiers for the cancel-all action."""
        if self.origin_id is None:
            self.origin_id = self.id


type OrderAction = CreateOrder | AmendOrder | CancelOrder | CancelAllOrders


class CreateOrderResponse(EnvelopeSchema):
    """Represents the response from a create-order action.

    Attributes:
        order_id: Exchange-assigned order identifier when available.
        client_order_id: Client-assigned order identifier when available.
    """

    order_id: Optional[OrderId] = None
    client_order_id: Optional[ClientOrderId] = None


class AmendOrderResponse(EnvelopeSchema):
    """Represents the response from an amend-order action.

    Attributes:
        order_id: Exchange-assigned order identifier when available.
        client_order_id: Client-assigned order identifier when available.
    """

    order_id: Optional[OrderId] = None
    client_order_id: Optional[ClientOrderId] = None


class CancelOrderResponse(EnvelopeSchema):
    """Represents the response from a cancel-order action.

    Attributes:
        order_id: Exchange-assigned order identifier when available.
        client_order_id: Client-assigned order identifier when available.
    """

    order_id: Optional[OrderId] = None
    client_order_id: Optional[ClientOrderId] = None


class CancelAllOrdersResponse(EnvelopeSchema):
    """Represents the response from a cancel-all-orders action.

    Attributes:
        order_ids: Exchange order identifiers reported as cancelled.
        client_order_ids: Client order identifiers reported as cancelled.
    """

    # Some exchanges annoyingly do not return which orders were
    # cancelled, merely confirm that they were ALL cancelled. You can
    # check this success with 'response.is_successful'
    order_ids: Optional[list[OrderId]] = None
    client_order_ids: Optional[list[ClientOrderId]] = None


class TradesResponse(EnvelopeSchema):
    """Represents a list of trades.

    Trades are guaranteed to be in ascending order of time.

    Attributes:
        trades: Trades sorted by ascending trade timestamp.
    """

    trades: list[Trade]

    def __post_init__(self) -> None:
        """Validate and order trade responses.

        Raises:
            ValueError: If any trade timestamp is non-positive.
        """
        for trade in self.trades:
            if trade.time_ms <= 0:
                raise ValueError(
                    f"Invalid trade time_ms; expected >0 but got {trade.time_ms}"
                )
        self.trades.sort(key=lambda x: x.time_ms)


class OrderbookResponse(EnvelopeSchema):
    """Represents the current state of the orderbook.

    Orderbook levels are guaranteed to be in ascending order of price.

    Attributes:
        bids: Bid levels sorted by ascending price when not BBO-only.
        asks: Ask levels sorted by ascending price when not BBO-only.
        is_bbo: Whether the payload is restricted to best bid and offer.
    """

    bids: list[OrderbookLevel]
    asks: list[OrderbookLevel]
    is_bbo: bool = False

    def __post_init__(self) -> None:
        """Validate and order orderbook responses.

        Raises:
            ValueError: If both bids and asks are empty.
        """
        if not self.bids and not self.asks:
            raise ValueError(
                "Invalid OrderbookResponse; expected non-empty bids or asks lists."
            )
        if not self.is_bbo:
            self.bids.sort(key=lambda x: x.price)
            self.asks.sort(key=lambda x: x.price)


class TickerResponse(EnvelopeSchema):
    """Represents current ticker information for an instrument.

    Attributes:
        mark_price: Current mark price.
        index_price: Current index price.
        funding_rate: Current funding rate.
        next_funding_time_ms: Next funding timestamp in milliseconds.
        open_interest: Current open interest.
        avg_volume_24h: Rolling 24-hour average traded volume.
        price_chg_24h: Rolling 24-hour absolute price change.
    """

    mark_price: float
    index_price: float
    funding_rate: float
    next_funding_time_ms: float
    open_interest: float
    avg_volume_24h: float
    price_chg_24h: float

    def __post_init__(self) -> None:
        """Validate ticker response values.

        Raises:
            ValueError: If any non-negative field is below zero.
        """
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


class InstrumentInfoResponse(EnvelopeSchema):
    """Represents static instrument metadata.

    Attributes:
        tick_size: Minimum allowed price increment.
        lot_size: Minimum allowed size increment.
        max_taker_size: Maximum taker order size.
        max_maker_size: Maximum maker order size.
    """

    tick_size: float
    lot_size: float
    max_taker_size: float
    max_maker_size: float

    def __post_init__(self) -> None:
        """Validate instrument info response values.

        Raises:
            ValueError: If tick/lot sizes are non-positive or max sizes are negative.
        """
        if self.tick_size <= 0.0:
            raise ValueError(f"Invalid tick_size; expected >0 but got {self.tick_size}")
        if self.lot_size <= 0.0:
            raise ValueError(f"Invalid lot_size; expected >0 but got {self.lot_size}")
        if self.max_taker_size < 0.0:
            raise ValueError(
                f"Invalid max_taker_size; expected >=0 but got {self.max_taker_size}"
            )
        if self.max_maker_size < 0.0:
            raise ValueError(
                f"Invalid max_maker_size; expected >=0 but got {self.max_maker_size}"
            )


class OrdersResponse(EnvelopeSchema):
    """Represents a list of order states.

    Attributes:
        orders: Order states returned by the exchange.
    """

    orders: list[Order]


class PositionResponse(EnvelopeSchema):
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
        """Validate position response values.

        Raises:
            ValueError: If price or size is negative.
        """
        if self.price < 0.0:
            raise ValueError(f"Invalid price; expected >=0 but got {self.price}")
        if self.size < 0.0:
            raise ValueError(f"Invalid size; expected >=0 but got {self.size}")

    @property
    def value(self) -> float:
        """Return the notional value of the position.

        Returns:
            float: Product of the position price and size.
        """
        return self.price * self.size


class ExecutionResponse(EnvelopeSchema):
    """Represents a collection of execution fills.

    Attributes:
        executions: Executions returned by the exchange.
    """

    executions: list[Execution]


class AccountResponse(EnvelopeSchema):
    """Represents account balance and margin information.

    Attributes:
        balance: Total account balance.
        initial_margin: Initial margin currently reserved.
        maintenance_margin: Maintenance margin currently required.
        unrealized_pnl: Unrealized profit and loss.
    """

    balance: float
    initial_margin: float
    maintenance_margin: float
    unrealized_pnl: float

    def __post_init__(self) -> None:
        """Validate account response values.

        Raises:
            ValueError: If balance or margin fields are negative.
        """
        if self.balance < 0.0:
            raise ValueError(f"Invalid balance; expected >=0 but got {self.balance}")
        if self.initial_margin < 0.0:
            raise ValueError(
                f"Invalid initial_margin; expected >=0 but got {self.initial_margin}"
            )
        if self.maintenance_margin < 0.0:
            raise ValueError(
                f"Invalid maintenance_margin; expected >=0 but got {self.maintenance_margin}"
            )


class ClientResponseTransport(Enum):
    """Transport categories for client response metadata."""

    HTTP = "http"
    WS = "ws"
    INTERNAL = "internal"


class ClientResponseMeta(Struct, frozen=True):
    """Metadata envelope attached to all client responses.

    Attributes:
        started_ns: Local timestamp when the request began.
        finished_ns: Local timestamp when the request completed.
        venue: Venue where the request was routed.
        transport: Transport type used for the request.
        operation: Full endpoint or operation name for observability.
        request_id: Optional request identifier when available.
        status_code: Optional transport/application status code.
        attempt: One-based retry attempt counter.
        timeout: Whether the response resulted from a timeout.
    """

    started_ns: int
    finished_ns: int
    venue: Venue
    transport: ClientResponseTransport
    operation: str
    request_id: str | None = None
    status_code: int | None = None
    attempt: int = 1
    timeout: bool = False

    @classmethod
    def immediate(
        cls,
        *,
        venue: Venue = Venue.NULL,
        transport: ClientResponseTransport = ClientResponseTransport.INTERNAL,
        operation: str = "unknown",
        request_id: str | None = None,
        status_code: int | None = None,
        attempt: int = 1,
        timeout: bool = False,
    ) -> Self:
        """Create metadata for an immediate local result.

        Args:
            venue: Venue where the request was routed.
            transport: Transport type used for the request.
            operation: Full endpoint or operation name.
            request_id: Optional request identifier.
            status_code: Optional transport/application status code.
            attempt: One-based retry attempt counter.
            timeout: Whether the response resulted from a timeout.

        Returns:
            ClientResponseMeta: Metadata with identical start/finish timestamps.
        """
        now_ns = time_ns()
        return cls(
            started_ns=now_ns,
            finished_ns=now_ns,
            venue=venue,
            transport=transport,
            operation=operation,
            request_id=request_id,
            status_code=status_code,
            attempt=attempt,
            timeout=timeout,
        )

    @property
    def latency_ns(self) -> int:
        """Return wall-clock request latency in nanoseconds.

        Returns:
            int: Non-negative duration between start and finish timestamps.
        """
        return max(self.finished_ns - self.started_ns, 0)

    @property
    def latency_ms(self) -> float:
        """Return wall-clock request latency in milliseconds.

        Returns:
            float: Non-negative request duration in milliseconds.
        """
        return self.latency_ns / 1_000_000.0

    def __post_init__(self) -> None:
        """Validate metadata invariants in debug builds.

        Raises:
            ValueError: If metadata fields are inconsistent.
        """
        if __debug__:
            if self.started_ns <= 0:
                raise ValueError("ClientResponseMeta.started_ns must be > 0")
            if self.finished_ns <= 0:
                raise ValueError("ClientResponseMeta.finished_ns must be > 0")
            if self.finished_ns < self.started_ns:
                raise ValueError("ClientResponseMeta.finished_ns must be >= started_ns")
            if self.operation == "":
                raise ValueError("ClientResponseMeta.operation must be non-empty")
            if self.attempt <= 0:
                raise ValueError("ClientResponseMeta.attempt must be >= 1")


class ClientResponseSuccess[T](Struct):
    """Represents a successful response from a client.

    Attributes:
        data: Response payload returned by the client.
        is_successful: Success marker fixed to ``True``.
        err_no: Numeric error code, typically zero.
        err_msg: Error message, typically empty.
    """

    data: T
    meta: ClientResponseMeta = field(default_factory=ClientResponseMeta.immediate)
    is_successful: Literal[True] = True
    err_no: int = 0
    err_msg: str = ""

    def __post_init__(self) -> None:
        """Validate success response invariants in debug builds.

        Raises:
            ValueError: If success fields contain error data or are inconsistent.
        """
        if __debug__:
            if self.is_successful is not True:
                raise ValueError("ClientResponseSuccess requires is_successful=True")
            if self.err_no != 0:
                raise ValueError("ClientResponseSuccess err_no must be 0")
            if self.err_msg != "":
                raise ValueError("ClientResponseSuccess err_msg must be empty")


class ClientResponseFailure[T](Struct):
    """Represents a failed response from a client.

    Attributes:
        is_successful: Failure marker fixed to ``False``.
        data: Payload marker fixed to ``None``.
        err_no: Numeric error code.
        err_msg: Error message describing the failure.
    """

    is_successful: Literal[False] = False
    meta: ClientResponseMeta = field(default_factory=ClientResponseMeta.immediate)
    data: None = None
    err_no: int = 0
    err_msg: str = ""

    def __post_init__(self) -> None:
        """Validate failure response invariants in debug builds.

        Raises:
            ValueError: If failure fields are inconsistent or missing error details.
        """
        if __debug__:
            if self.is_successful is not False:
                raise ValueError("ClientResponseFailure requires is_successful=False")
            if self.data is not None:
                raise ValueError("ClientResponseFailure data must be None")
            if self.err_no == 0 and self.err_msg == "":
                raise ValueError("ClientResponseFailure requires err_no or err_msg")


# Union type helps with type inference for the ClientResponse[T] type
# for both is_successful result values.
type ClientResponse[T] = ClientResponseSuccess[T] | ClientResponseFailure[T]


def is_success[T](response: ClientResponse[T]) -> TypeGuard[ClientResponseSuccess[T]]:
    """Check whether a client response represents success.

    Args:
        response: Response to inspect.

    Returns:
        bool: True when the response is a successful variant.
    """
    return response.is_successful is True


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
