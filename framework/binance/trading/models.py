"""Structs for Binance USDS-M Futures websocket and REST API trading responses.

This module provides dataclass-like structs for deserializing order creation/amendment/
cancellation responses from the websocket Trade API, as well as REST API responses for
market data, account information, and trading history.

Includes both WebSocket Trade API responses (orders, positions, executions) and HTTP
REST API responses (market data, accounts, trades).
"""

from msgspec import Struct

from framework.base.common import Instrument, Venue
from framework.base.stream.models import (
    Execution,
)


class BinanceWsCreateOrderResult(Struct, rename="camel", frozen=True):
    """Result of a websocket order creation request.

    Contains complete order details after successful creation, including order ID,
    status, prices, quantities, and timing information. Used to confirm order
    placement through the Trade WebSocket API.

    Docs: https://developers.binance.com/docs/derivatives/usds-margined-futures/trade/websocket-api/Place-Order

    Example payload::

        {
          "orderId": 123456,                    // order ID
          "symbol": "BTCUSDT",                  // trading pair
          "status": "NEW",                      // order status
          "clientOrderId": "client_order_1",    // client-assigned ID
          "price": "30000.0",                   // limit price
          "avgPrice": "0",                      // average fill price
          "origQty": "1.0",                     // original quantity
          "executedQty": "0",                   // executed quantity
          "cumQty": "0",                        // cumulative quantity
          "cumQuote": "0",                      // cumulative quote
          "timeInForce": "GTC",                 // time in force
          "type": "LIMIT",                      // order type
          "reduceOnly": false,                  // reduce-only flag
          "closePosition": false,               // close position flag
          "side": "BUY",                        // order side
          "positionSide": "LONG",               // position side
          "stopPrice": "0",                     // stop price (if applicable)
          "workingType": "CONTRACT_PRICE",      // working type
          "priceProtect": false,                // price protection
          "origType": "LIMIT",                  // original order type
          "priceMatch": "NONE",                 // price matching mode
          "selfTradePreventionMode": "NONE",    // STP mode
          "goodTillDate": 0,                    // good till date (if GTD)
          "updateTime": 1568014460891           // update time (ms)
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
    positionSide: str
    stop_price: str
    working_type: str
    priceProtect: bool
    orig_type: str
    price_match: str
    self_trade_prevention_mode: str
    good_till_date: int
    update_time: int


class BinanceWsAmendOrderResult(Struct, rename="camel", frozen=True):
    """Result of a websocket order amendment request.

    Contains updated order details after successful modification, including all
    current order parameters. Used to confirm order amendments through the Trade
    WebSocket API.

    Docs: https://developers.binance.com/docs/derivatives/usds-margined-futures/trade/websocket-api/Amend-Order

    Example payload::

        {
          "orderId": 123456,                    // order ID
          "symbol": "BTCUSDT",                  // trading pair
          "status": "NEW",                      // order status
          "clientOrderId": "client_order_1",    // client-assigned ID
          "price": "31000.0",                   // updated price
          "avgPrice": "0",                      // average fill price
          "origQty": "1.0",                     // original quantity
          "executedQty": "0",                   // executed quantity
          "cumQty": "0",                        // cumulative quantity
          "cumQuote": "0",                      // cumulative quote
          "timeInForce": "GTC",                 // time in force
          "type": "LIMIT",                      // order type
          "reduceOnly": false,                  // reduce-only flag
          "closePosition": false,               // close position flag
          "side": "BUY",                        // order side
          "positionSide": "LONG",               // position side
          "stopPrice": "0",                     // stop price
          "workingType": "CONTRACT_PRICE",      // working type
          "priceProtect": false,                // price protection
          "origType": "LIMIT",                  // original order type
          "priceMatch": "NONE",                 // price matching mode
          "selfTradePreventionMode": "NONE",    // STP mode
          "goodTillDate": 0,                    // good till date
          "updateTime": 1568014460891           // update time (ms)
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


class BinanceWsCancelOrderResult(Struct, rename="camel", frozen=True):
    """Result of a websocket order cancellation request.

    Contains final order details after successful cancellation, confirming the order
    is no longer active. Used to confirm order cancellations through the Trade
    WebSocket API.

    Docs: https://developers.binance.com/docs/derivatives/usds-margined-futures/trade/websocket-api/Cancel-Order

    Example payload::

        {
          "orderId": 123456,                    // order ID
          "clientOrderId": "client_order_1",    // client-assigned ID
          "cumQty": "0",                        // cumulative quantity
          "cumQuote": "0",                      // cumulative quote
          "executedQty": "0",                   // executed quantity
          "origQty": "1.0",                     // original quantity
          "origType": "LIMIT",                  // original order type
          "price": "30000.0",                   // order price
          "reduceOnly": false,                  // reduce-only flag
          "side": "BUY",                        // order side
          "positionSide": "LONG",               // position side
          "status": "CANCELED",                 // final status
          "stopPrice": "0",                     // stop price
          "closePosition": false,               // close position flag
          "symbol": "BTCUSDT",                  // trading pair
          "timeInForce": "GTC",                 // time in force
          "type": "LIMIT",                      // order type
          "activatePrice": "0",                 // activation price
          "priceRate": "0",                     // price rate
          "updateTime": 1568014460891,          // update time (ms)
          "workingType": "CONTRACT_PRICE",      // working type
          "priceProtect": false,                // price protection
          "priceMatch": "NONE",                 // price matching mode
          "selfTradePreventionMode": "NONE",    // STP mode
          "goodTillDate": 0                     // good till date
        }
    """

    order_id: int
    client_order_id: str
    cum_qty: str
    cum_quote: str
    executed_qty: str
    orig_qty: str
    orig_type: str
    price: str
    reduce_only: bool
    side: str
    position_side: str
    status: str
    stop_price: str
    close_position: bool
    symbol: str
    time_in_force: str
    type: str
    activate_price: str
    price_rate: str
    update_time: int
    working_type: str
    price_protect: bool
    price_match: str
    self_trade_prevention_mode: str
    good_till_date: int


class BinanceWsOrderResponse[T](Struct, rename="camel", frozen=True):
    """Generic wrapper for websocket order action responses.

    Wraps the result field of websocket Trade API responses, providing status code
    and request ID alongside the typed result payload. The type parameter T is one of
    BinanceWsCreateOrderResult, BinanceWsAmendOrderResult, or BinanceWsCancelOrderResult.

    Docs: https://developers.binance.com/docs/derivatives/usds-margined-futures/trade/websocket-api/

    Example payload::

        {
          "id": "1",                   // request ID (echo from request)
          "status": 200,               // HTTP-like status code (0 or 200 for success)
          "result": {                  // typed result (CreateOrderResult, etc.)
            "orderId": 123456,
            "symbol": "BTCUSDT",
            ...
          }
        }
    """

    id: str
    status: int
    result: T

    @property
    def is_successful(self) -> bool:
        return self.status == 200 or self.status == 0


class BinanceHttpCancelAllOrdersResponse(Struct, frozen=True):
    """Response from canceling all open orders for a symbol (HTTP REST API).

    Confirms that a bulk order cancellation request succeeded or failed. Returns a
    simple status code and message.

    Docs: https://developers.binance.com/docs/derivatives/usds-margined-futures/trade/rest-api/Cancel-all-Open-Orders

    Example payload::

        {
          "code": 200,                 // status code (200 or 0 for success)
          "msg": "success"             // status message
        }
    """

    code: int
    msg: str

    @property
    def is_successful(self) -> bool:
        return self.code == 200 or self.code == 0


class BinanceHttpOrderbookResponse(Struct, rename="camel", frozen=True):
    """Full orderbook snapshot (HTTP REST API).

    Returns the current full depth of bids and asks for a symbol. Each level is a
    [price, quantity] pair as strings. Includes event and transaction timestamps.

    Docs: https://developers.binance.com/docs/derivatives/usds-margined-futures/market-data/rest-api/Order-Book

    Example payload::

        {
          "lastUpdateId": 1234,        // last update ID
          "E": 1568014460893,          // event time (ms)
          "T": 1568014460891,          // transaction time (ms)
          "bids": [
            ["30000.00", "1.0"],       // [price, quantity]
            ["29999.50", "2.0"]
          ],
          "asks": [
            ["30001.00", "1.5"],       // [price, quantity]
            ["30002.00", "3.0"]
          ]
        }
    """

    last_update_id: int
    E: int  # Event time
    T: int  # Transaction time
    bids: list[list[str]]
    asks: list[list[str]]


class BinanceHttpTicker24hrResponse(Struct, rename="camel", frozen=True):
    """24-hour rolling ticker statistics for a symbol (HTTP REST API).

    Provides comprehensive market statistics over the last 24 hours including price
    changes, volumes, high/low prices, and OHLC data.

    Docs: https://developers.binance.com/docs/derivatives/usds-margined-futures/market-data/rest-api/24hr-Ticker-Price-Change-Statistics

    Example payload::

        {
          "symbol": "BTCUSDT",               // symbol
          "priceChange": "1000.00",          // absolute price change
          "priceChangePercent": "3.50",      // percentage price change
          "weightedAvgPrice": "29500.00",    // weighted average price
          "lastPrice": "30000.00",           // last price
          "lastQty": "1.0",                  // last quantity
          "openPrice": "29000.00",           // open price
          "highPrice": "31000.00",           // 24h high
          "lowPrice": "28000.00",            // 24h low
          "volume": "100000.0",              // total volume (base asset)
          "quoteVolume": "2950000000.00",    // total volume (quote asset)
          "openTime": 1568014460000,         // period open time (ms)
          "closeTime": 1568100860000,        // period close time (ms)
          "firstId": 100,                    // first trade ID
          "lastId": 500,                     // last trade ID
          "count": 401                       // trade count
        }
    """

    symbol: str
    price_change: str
    price_change_percent: str
    weighted_avg_price: str
    last_price: str
    last_qty: str
    open_price: str
    high_price: str
    low_price: str
    volume: str
    quote_volume: str
    open_time: int
    close_time: int
    first_id: int
    last_id: int
    count: int


class BinanceHttpMarkPriceResponse(Struct, rename="camel", frozen=True):
    """Current mark price and funding information (HTTP REST API).

    Provides the current mark price, index price, funding rate, and next funding time
    for a perpetual contract. Used for liquidation pricing and PnL calculations.

    Docs: https://developers.binance.com/docs/derivatives/usds-margined-futures/market-data/rest-api/Mark-Price

    Example payload::

        {
          "symbol": "BTCUSDT",               // symbol
          "markPrice": "30000.50",           // mark price
          "indexPrice": "29995.25",          // index price
          "estimatedSettlePrice": "30002.00", // estimated settle price
          "lastFundingRate": "0.0001",       // last funding rate
          "nextFundingTime": 1568014500000,  // next funding time (ms)
          "interestRate": "0.0003",          // interest rate
          "time": 1568014460893              // timestamp (ms)
        }
    """

    symbol: str
    mark_price: str
    index_price: str
    estimated_settle_price: str
    last_funding_rate: str
    next_funding_time: int
    interest_rate: str
    time: int


class BinanceHttpOpenInterestResponse(Struct, rename="camel", frozen=True):
    """Current open interest for a perpetual contract (HTTP REST API).

    Provides the total open interest (sum of all long/short positions) for a symbol.
    Useful for gauging market activity and analyzing positioning.

    Docs: https://developers.binance.com/docs/derivatives/usds-margined-futures/market-data/rest-api/Open-Interest

    Example payload::

        {
          "openInterest": "100000.50",       // total open interest
          "symbol": "BTCUSDT",               // symbol
          "time": 1568014460893              // timestamp (ms)
        }
    """

    open_interest: str
    symbol: str
    time: int


class BinanceHttpTradeResponse(Struct, rename="camel", frozen=True):
    """Recent trade in the market (HTTP REST API).

    Represents a single recent trade for a symbol, including price, quantity, and
    aggressor side. Typically returned as a list in response to recent trades request.

    Docs: https://developers.binance.com/docs/derivatives/usds-margined-futures/market-data/rest-api/Recent-Trades-List

    Example payload::

        {
          "id": 123456,                      // trade ID
          "price": "30000.50",               // trade price
          "qty": "1.0",                      // trade quantity
          "quoteQty": "30000.50",            // trade quote quantity
          "time": 1568014460893,             // trade time (ms)
          "isBuyerMaker": false              // is buyer the market maker
        }
    """

    id: int
    price: str
    qty: str
    quote_qty: str
    time: int
    is_buyer_maker: bool


class PriceFilter(
    Struct,
    tag="PRICE_FILTER",
    tag_field="filterType",
    rename="camel",
    frozen=True,
):
    """Price constraints for a symbol.

    Args:
        min_price (str): Minimum allowed price.
        max_price (str): Maximum allowed price.
        tick_size (str): Price increment.
    """

    min_price: str
    max_price: str
    tick_size: str


class LotSizeFilter(
    Struct,
    tag="LOT_SIZE",
    tag_field="filterType",
    rename="camel",
    frozen=True,
):
    """Order size constraints for limit orders.

    Args:
        min_qty (str): Minimum order quantity.
        max_qty (str): Maximum order quantity.
        step_size (str): Quantity increment.
    """

    min_qty: str
    max_qty: str
    step_size: str


class MarketLotSizeFilter(
    Struct,
    tag="MARKET_LOT_SIZE",
    tag_field="filterType",
    rename="camel",
    frozen=True,
):
    """Order size constraints for market orders.

    Args:
        min_qty (str): Minimum order quantity.
        max_qty (str): Maximum order quantity.
        step_size (str): Quantity increment.
    """

    min_qty: str
    max_qty: str
    step_size: str


class MaxNumOrdersFilter(
    Struct,
    tag="MAX_NUM_ORDERS",
    tag_field="filterType",
    rename="camel",
    frozen=True,
):
    """Maximum number of open orders allowed.

    Args:
        limit (int): Maximum number of open orders.
    """

    limit: int


class MinNotionalFilter(
    Struct,
    tag="MIN_NOTIONAL",
    tag_field="filterType",
    rename="camel",
    frozen=True,
):
    """Minimum notional value for an order.

    Args:
        notional (str): Minimum notional requirement.
    """

    notional: str


class PercentPriceFilter(
    Struct,
    tag="PERCENT_PRICE",
    tag_field="filterType",
    rename="camel",
    frozen=True,
):
    """Percent price bounds for order placement.

    Args:
        multiplier_down (str): Lower price multiplier.
        multiplier_up (str): Upper price multiplier.
        multiplier_decimal (str): Decimal precision for multipliers.
    """

    multiplier_down: str
    multiplier_up: str
    multiplier_decimal: str


class PositionRiskControlFilter(
    Struct,
    tag="POSITION_RISK_CONTROL",
    tag_field="filterType",
    rename="camel",
    frozen=True,
):
    """Position risk control settings for a symbol.

    Args:
        position_control_side (str): Position control side (e.g. NONE).
    """

    position_control_side: str


type SymbolInformationFilters = (
    PriceFilter
    | LotSizeFilter
    | MarketLotSizeFilter
    | MaxNumOrdersFilter
    | MinNotionalFilter
    | PercentPriceFilter
    | PositionRiskControlFilter
)


class SymbolInformation(Struct, rename="camel", frozen=True):
    """Trading information for a single symbol.

    Provides status, base/quote assets, underlying type, and list of applicable
    trading filters (price, quantity, order constraints).

    Docs: https://developers.binance.com/docs/derivatives/usds-margined-futures/market-data/rest-api/Exchange-Information

    Example payload::

        {
          "status": "TRADING",               // symbol status
          "baseAsset": "BTC",                // base asset
          "quoteAsset": "USDT",              // quote asset
          "underlyingType": "COIN",          // underlying asset type
          "filters": [
            {
              "filterType": "PRICE_FILTER",
              "minPrice": "0.01",
              "maxPrice": "1000000.00",
              "tickSize": "0.01"
            },
            {
              "filterType": "LOT_SIZE",
              "minQty": "0.001",
              "maxQty": "1000000.0",
              "stepSize": "0.001"
            }
          ]
        }
    """

    status: str
    base_asset: str
    quote_asset: str
    underlying_type: str
    filters: list[SymbolInformationFilters]


class BinanceHttpExchangeInformationResponse(Struct, frozen=True):
    """Exchange information containing all tradable symbols and their constraints.

    Provides metadata about all symbols available on the exchange, including trading
    status, asset information, and applicable filters (price/quantity constraints).

    Docs: https://developers.binance.com/docs/derivatives/usds-margined-futures/market-data/rest-api/Exchange-Information

    Example payload::

        {
          "symbols": [
            {
              "status": "TRADING",
              "baseAsset": "BTC",
              "quoteAsset": "USDT",
              "underlyingType": "COIN",
              "filters": [...]
            },
            {
              "status": "TRADING",
              "baseAsset": "ETH",
              "quoteAsset": "USDT",
              "underlyingType": "COIN",
              "filters": [...]
            }
          ]
        }
    """

    symbols: list[SymbolInformation]


class BinanceHttpOrdersResponse(Struct, rename="camel", frozen=True):
    """Open order details (HTTP REST API).

    Represents a single open order returned from the current open orders endpoint.
    Contains all order parameters, status, and pricing information.

    Docs: https://developers.binance.com/docs/derivatives/usds-margined-futures/trade/rest-api/Current-Open-Orders

    Example payload::

        {
          "avgPrice": "0",                   // average fill price
          "clientOrderId": "client_order_1", // client-assigned ID
          "cumQuote": "0",                   // cumulative quote
          "executedQty": "0",                // executed quantity
          "orderId": 123456,                 // order ID
          "origQty": "1.0",                  // original quantity
          "origType": "LIMIT",               // original order type
          "price": "30000.0",                // order price
          "reduceOnly": false,               // reduce-only flag
          "side": "BUY",                     // order side
          "positionSide": "LONG",            // position side
          "status": "NEW",                   // order status
          "stopPrice": "0",                  // stop price
          "closePosition": false,            // close position flag
          "symbol": "BTCUSDT",               // symbol
          "time": 1568014460891,             // order creation time (ms)
          "timeInForce": "GTC",              // time in force
          "type": "LIMIT",                   // order type
          "updateTime": 1568014460891,       // update time (ms)
          "workingType": "CONTRACT_PRICE",   // working type
          "priceProtect": false,             // price protection
          "priceMatch": "NONE",              // price matching mode
          "selfTradePreventionMode": "NONE", // STP mode
          "goodTillDate": 0                  // good till date
        }
    """

    avg_price: str
    client_order_id: str
    cum_quote: str
    executed_qty: str
    order_id: int
    orig_qty: str
    orig_type: str
    price: str
    reduce_only: bool
    side: str
    position_side: str
    status: str
    stop_price: str
    close_position: bool
    symbol: str
    time: int
    time_in_force: str
    type: str
    update_time: int
    working_type: str
    price_protect: bool
    price_match: str
    self_trade_prevention_mode: str
    good_till_date: int


class BinanceHttpPositionResponse(Struct, rename="camel", frozen=True):
    """Position details for a symbol (HTTP REST API).

    Provides complete position information including size, entry price, mark price,
    PnL, liquidation price, margins, and leverage. Updated in real-time as positions
    change.

    Docs: https://developers.binance.com/docs/derivatives/usds-margined-futures/account/rest-api/Position-Information-V2

    Example payload::

        {
          "symbol": "BTCUSDT",               // symbol
          "positionSide": "LONG",            // position side
          "positionAmt": "1.0",              // position amount (quantity)
          "entryPrice": "30000.0",           // entry price
          "breakEvenPrice": "30100.0",       // break-even price
          "markPrice": "30500.0",            // current mark price
          "unRealizedProfit": "500.0",       // unrealized PnL
          "liquidationPrice": "25000.0",     // liquidation price
          "isolatedMargin": "1000.0",        // isolated margin (if isolated)
          "notional": "30500.0",             // notional value
          "marginAsset": "USDT",             // margin asset
          "isolatedWallet": "1000.0",        // isolated wallet balance
          "initialMargin": "1000.0",         // initial margin
          "maintMargin": "600.0",            // maintenance margin
          "positionInitialMargin": "1000.0", // position initial margin
          "openOrderInitialMargin": "0",     // open order initial margin
          "adl": 0,                          // auto-deleveraging level
          "updateTime": 1568014460891        // update time (ms)
        }
    """

    symbol: str
    position_side: str
    position_amt: str
    entry_price: str
    break_even_price: str
    mark_price: str
    un_realized_profit: str
    liquidation_price: str
    isolated_margin: str
    notional: str
    margin_asset: str
    isolated_wallet: str
    initial_margin: str
    maint_margin: str
    position_initial_margin: str
    open_order_initial_margin: str
    adl: int
    update_time: int


class ExecutionResponse(Struct, frozen=True):
    """Represents an execution (fill) of an order."""

    venue: Venue
    instrument: Instrument

    executions: list[Execution]


class AccountResponse(Struct, frozen=True):
    """Represents account information."""

    venue: Venue
    instrument: Instrument

    balance: float
    initial_margin: float
    maintenance_margin: float
    unrealized_pnl: float


class HttpOrder(Struct, rename="camel", frozen=True):
    """Order details from HTTP REST API.

    Represents a single order with complete details including pricing, execution
    status, and timing information.

    Docs: https://developers.binance.com/docs/derivatives/usds-margined-futures/trade/rest-api/Current-Open-Orders

    Example payload::

        {
          "symbol": "BTCUSDT",               // symbol
          "orderId": 123456,                 // order ID
          "clientOrderId": "client_order_1", // client-assigned ID
          "price": "30000.0",                // limit price
          "origQty": "1.0",                  // original quantity
          "executedQty": "0.5",              // executed quantity
          "cumulativeQuoteQty": "15000.0",   // cumulative quote quantity
          "status": "PARTIALLY_FILLED",      // order status
          "timeInForce": "GTC",              // time in force
          "type": "LIMIT",                   // order type
          "side": "BUY",                     // order side
          "stopPrice": "0",                  // stop price
          "time": 1568014460891,             // order creation time (ms)
          "updateTime": 1568014460991,       // update time (ms)
          "reduceOnly": false,               // reduce-only flag
          "closePosition": false             // close position flag
        }
    """

    symbol: str
    order_id: int
    client_order_id: str
    price: str
    orig_qty: str
    executed_qty: str
    cumulative_quote_qty: str
    status: str
    time_in_force: str
    type: str
    side: str
    stop_price: str
    time: int
    update_time: int
    reduce_only: bool
    close_position: bool


class HttpPosition(Struct, rename="camel", frozen=True):
    """Position information from HTTP REST API.

    Provides complete position data including entry price, mark price, unrealized PnL,
    liquidation price, leverage, and margin information.

    Docs: https://developers.binance.com/docs/derivatives/usds-margined-futures/account/rest-api/Position-Information-V2

    Example payload::

        {
          "symbol": "BTCUSDT",               // symbol
          "positionAmt": "1.0",              // position amount (quantity)
          "entryPrice": "30000.0",           // entry price
          "markPrice": "30500.0",            // mark price
          "unrealPnl": "500.0",              // unrealized PnL
          "liquidationPrice": "25000.0",     // liquidation price
          "leverage": "10",                  // leverage used
          "maxNotionalValue": "300000",      // max notional value
          "marginType": "cross",             // margin type (cross/isolated)
          "isolatedMargin": "0",             // isolated margin amount
          "isAutoAddMargin": false,          // auto-add margin enabled
          "positionSide": "LONG",            // position side
          "notional": "30500.0",             // notional value
          "isolatedWallet": "0",             // isolated wallet balance
          "updateTime": 1568014460891        // update time (ms)
        }
    """

    symbol: str
    position_amt: str
    entry_price: str
    mark_price: str
    unreal_pnl: str
    liquidation_price: str
    leverage: str
    max_notional_value: str
    margin_type: str
    isolated_margin: str
    is_auto_add_margin: bool
    position_side: str
    notional: str
    isolated_wallet: str
    update_time: int


class HttpUserTrade(Struct, rename="camel", frozen=True):
    """User trade/execution history from HTTP REST API.

    Represents a single trade executed by the user, including fill details, fees,
    and execution classification (maker/taker, buyer/seller).

    Docs: https://developers.binance.com/docs/derivatives/usds-margined-futures/trade/rest-api/Account-Trade-List

    Example payload::

        {
          "symbol": "BTCUSDT",               // symbol
          "id": 12345,                       // trade ID
          "orderId": 123456,                 // related order ID
          "side": "BUY",                     // trade side
          "qty": "0.5",                      // trade quantity
          "price": "30000.0",                // trade price
          "quoteQty": "15000.0",             // quote quantity
          "commission": "0.15",              // fee amount
          "commissionAsset": "USDT",         // fee asset
          "time": 1568014460891,             // trade time (ms)
          "isBuyer": true,                   // is buyer
          "isMaker": false,                  // is maker
          "isIsolated": false                // is isolated position
        }
    """

    symbol: str
    id: int
    order_id: int
    side: str
    qty: str
    price: str
    quote_qty: str
    commission: str
    commission_asset: str
    time: int
    is_buyer: bool
    is_maker: bool
    is_isolated: bool


class HttpAccount(Struct, rename="camel", frozen=True):
    """Account information and balance summary (HTTP REST API).

    Provides complete account-level information including trading permissions, margin
    levels, total balances, and unrealized PnL across all positions.

    Docs: https://developers.binance.com/docs/derivatives/usds-margined-futures/account/rest-api/Account-Information-V2

    Example payload::

        {
          "feeTier": 0,                        // maker fee tier
          "canTrade": true,                    // trading enabled
          "canDeposit": true,                  // deposits enabled
          "canWithdraw": true,                 // withdrawals enabled
          "updateTime": 1568014460891,         // update time (ms)
          "totalInitialMargin": "1000.0",      // total initial margin required
          "totalMaintMargin": "600.0",         // total maintenance margin required
          "totalWalletBalance": "5000.0",      // total wallet balance
          "totalUnrealizedPnl": "500.0",       // total unrealized PnL
          "totalMarginBalance": "5500.0",      // total margin balance
          "totalPositionInitialMargin": "1000.0", // position initial margin
          "totalOpenOrderInitialMargin": "100.0", // open order initial margin
          "totalCrossWalletBalance": "5000.0",    // cross margin wallet balance
          "totalCrossUnPnl": "500.0",             // cross margin unrealized PnL
          "availableBalance": "3400.0",           // available balance
          "maxWithdrawAmount": "3400.0"           // max withdrawal amount
        }
    """

    fee_tier: int
    can_trade: bool
    can_deposit: bool
    can_withdraw: bool
    update_time: int
    total_initial_margin: str
    total_maint_margin: str
    total_wallet_balance: str
    total_unrealized_pnl: str
    total_margin_balance: str
    total_position_initial_margin: str
    total_open_order_initial_margin: str
    total_cross_wallet_balance: str
    total_cross_un_pnl: str
    available_balance: str
    max_withdraw_amount: str
