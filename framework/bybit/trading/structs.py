"""Structs for Bybit V5 Trade WebSocket API responses.

This module provides dataclass-like structs for deserializing order creation/amendment/
cancellation responses from the Bybit Trade WebSocket API into strongly-typed Python objects.
"""

from msgspec import Struct


class BybitWsCreateOrderResult(Struct, rename="camel", frozen=True):
    """Result of a Trade WebSocket order creation request.

    Contains complete order details after successful creation, including order ID,
    status, prices, quantities, and timing information. Used to confirm order
    placement through the Trade WebSocket API.

    Docs: https://bybit-exchange.github.io/docs/v5/websocket/trade

    Example payload::

        {
          "orderId": 123456,                // order ID
          "symbol": "BTCUSDT",              // trading pair
          "status": "New",                  // order status
          "clientOrderId": "client_1",      // client order ID
          "price": "30000.0",               // limit price
          "avgPrice": "0",                  // average fill price
          "origQty": "1.0",                 // original quantity
          "executedQty": "0",               // executed quantity
          "cumQty": "0",                    // cumulative quantity
          "cumQuote": "0",                  // cumulative quote
          "timeInForce": "GTC",             // time in force
          "type": "Limit",                  // order type
          "reduceOnly": false,              // reduce-only flag
          "closePosition": false,           // close position flag
          "side": "Buy",                    // order side
          "positionSide": "Long",           // position side
          "stopPrice": "0",                 // stop price
          "workingType": "LinearFutures",   // working type
          "priceProtect": false,            // price protection
          "origType": "Limit",              // original order type
          "priceMatch": "None",             // price matching mode
          "selfTradePreventionMode": "None",// STP mode
          "goodTillDate": 0,                // good till date
          "updateTime": 1568014460891       // update time (ms)
        }
    """

    order_id: int
    symbol: str
    status: str
    client_order_id: str
    price: str
    avg_price: str
    orig_qty: str
    executed_qty: str
    cum_qty: str
    cum_quote: str
    time_in_force: str
    type: str
    reduce_only: bool
    close_position: bool
    side: str
    position_side: str
    stop_price: str
    working_type: str
    price_protect: bool
    orig_type: str
    price_match: str
    self_trade_prevention_mode: str
    good_till_date: int
    update_time: int


class BybitWsOrderResponse[T](Struct, rename="camel", frozen=True):
    """Generic wrapper for Trade WebSocket order action responses.

    Wraps the result of websocket Trade API requests, providing request ID, status code,
    and typed result payload. The type parameter T is BybitWsCreateOrderResult for order
    creation responses.

    Docs: https://bybit-exchange.github.io/docs/v5/websocket/trade

    Example payload::

        {
          "id": "1",                       // request ID (echo from request)
          "status": 0,                     // response status (0 for success)
          "result": {                      // typed result (CreateOrderResult)
            "orderId": 123456,
            "symbol": "BTCUSDT",
            "status": "New",
            ...
          }
        }
    """

    id: str
    status: int
    result: T

    @property
    def is_successful(self) -> bool:
        return self.status == 0 or self.status == 200
