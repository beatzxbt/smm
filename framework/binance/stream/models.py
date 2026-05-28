"""Structs for deserializing Binance USDS-M Futures websocket stream events.

The module includes structs for market data streams (ticker, depth, trades) and
user data streams (orders, positions, account updates, executions).
"""

from __future__ import annotations

from msgspec import Struct, field

from framework.base.common import Asset, Symbol


class BookTickerStreamUpdate(Struct, tag=True, frozen=True):
    """Best bid/ask price and quantity update for a symbol.

    Pushes real-time updates whenever the best bid or ask price/quantity changes.
    Useful for monitoring top-of-book levels without requiring full depth updates.

    Docs: https://developers.binance.com/docs/derivatives/usds-margined-futures/websocket-market-streams/Individual-Symbol-Book-Ticker-Streams

    Example payload::

        {
          "u": 400900217,           // order book update ID
          "E": 1568014460893,       // event time (ms)
          "T": 1568014460891,       // transaction time (ms)
          "s": "BTCUSDT",           // symbol
          "b": "25.35190000",       // best bid price
          "B": "31.21000000",       // best bid quantity
          "a": "25.36520000",       // best ask price
          "A": "40.66000000"        // best ask quantity
        }
    """

    update_id: int = field(name="u")
    event_time: int = field(name="E")
    transaction_time: int = field(name="T")
    symbol: Symbol = field(name="s")
    best_bid_price: str = field(name="b")
    best_bid_qty: str = field(name="B")
    best_ask_price: str = field(name="a")
    best_ask_qty: str = field(name="A")


class DiffBookDepthStreamUpdate(Struct, tag=True, frozen=True):
    """Partial orderbook depth update with only changed price levels.

    Provides efficient depth updates by sending only the bid/ask levels that changed
    since the last update. Updates are delivered at configurable intervals (100ms,
    250ms, or 500ms). Can be used to reconstruct full orderbook by applying changes
    sequentially from a snapshot.

    Docs: https://developers.binance.com/docs/derivatives/usds-margined-futures/websocket-market-streams/Diff-Book-Depth-Streams

    Example payload::

        {
          "e": "depthUpdate",           // event type
          "E": 123456789,               // event time (ms)
          "T": 123456788,               // transaction time (ms)
          "s": "BTCUSDT",               // symbol
          "U": 157,                     // first update ID in batch
          "u": 160,                     // final update ID in batch
          "pu": 149,                    // previous stream final update ID
          "b": [["0.0024", "10"]],      // [[price, quantity], ...] for bids
          "a": [["0.0026", "100"]]      // [[price, quantity], ...] for asks
        }
    """

    event_type: str = field(name="e")
    event_time: int = field(name="E")
    transaction_time: int = field(name="T")
    symbol: Symbol = field(name="s")
    first_update_id: int = field(name="U")
    final_update_id: int = field(name="u")
    prev_final_update_id: int = field(name="pu")
    bids: tuple[tuple[str, str]] = field(name="b")
    asks: tuple[tuple[str, str]] = field(name="a")


class TradeStreamUpdate(Struct, tag=True, frozen=True):
    """Trade execution update for a symbol.

    Docs: https://developers.binance.com/docs/derivatives/usds-margined-futures/websocket-market-streams/Individual-Symbol-Trade-Streams

    Attributes:
        event_type (str): Event type, expected "trade".
        event_time (int): Event time in milliseconds.
        transaction_time (int): Trade time in milliseconds.
        symbol (str): Trading symbol.
        trade_id (int): Trade identifier.
        price (str): Trade price.
        quantity (str): Trade quantity.
        trade_type (str): Trade type (e.g. "MARKET").
        is_buyer_maker (bool): Whether the buyer is the maker.

    Example:
        {
          "e": "trade",               // event type
          "E": 1568014460893,         // event time (ms)
          "T": 1568014460891,         // trade time (ms)
          "s": "BTCUSDT",             // symbol
          "t": 123456,                // trade id
          "p": "30000.50",            // price
          "q": "0.1",                 // quantity
          "X": "MARKET",
          "m": false                  // buyer is maker
        }
    """

    event_type: str = field(name="e")
    event_time: int = field(name="E")
    transaction_time: int = field(name="T")
    symbol: Symbol = field(name="s")
    trade_id: int = field(name="t")
    price: str = field(name="p")
    quantity: str = field(name="q")
    trade_type: str = field(name="X")
    is_buyer_maker: bool = field(name="m")


class OpenInterestInfo(Struct, frozen=True):
    open_interest: float


class TickerStats24h(Struct, frozen=True):
    price_chg_24h_pct: float
    avg_volume_24h: float


class TickerStats24hStreamUpdate(Struct, tag=True, frozen=True):
    """24-hour rolling statistics for a symbol.

    Provides price change, percentage change, and volume information over a 24-hour
    window. Updates occur on a configurable interval. Useful for displaying summary
    market statistics in UI or for volatility calculations.

    Docs: https://developers.binance.com/docs/derivatives/usds-margined-futures/websocket-market-streams/24hr-Ticker-Price-Change-Statistics-Streams

    Example payload::

        {
          "E": 1568014460893,           // event time (ms)
          "s": "BTCUSDT",               // symbol
          "p": "100.0",                 // price change (absolute)
          "P": "0.5",                   // price change percent
          "v": "10000.0",               // total traded base asset volume
          "q": "1000000.0"              // total traded quote asset volume
        }
    """

    event_time: int = field(name="E")
    symbol: Symbol = field(name="s")
    price_change: str = field(name="p")
    price_change_percent: str = field(name="P")
    volume: str = field(name="v")
    quote_volume: str = field(name="q")

    def to_ticker_stats_24h(self) -> TickerStats24h:
        return TickerStats24h(
            price_chg_24h_pct=float(self.price_change_percent),
            avg_volume_24h=float(self.volume),
        )


class MarkPriceStreamUpdate(Struct, frozen=True):
    """Mark price, index price, and funding rate for a perpetual contract.

    Delivers real-time mark price (used for liquidations), index price (underlying
    spot index), and current funding rate. Critical for risk management and PnL
    calculations. Updates typically arrive every 3 seconds.

    Docs: https://developers.binance.com/docs/derivatives/usds-margined-futures/websocket-market-streams/Mark-Price-Stream

    Example payload::

        {
          "E": 1568014460893,           // event time (ms)
          "s": "BTCUSDT",               // symbol
          "p": "30000.50",              // mark price
          "i": "29995.25",              // index price
          "P": "30002.00",              // estimated settle price
          "r": "0.0001",                // funding rate
          "T": 1568014500000            // next funding time (ms)
        }
    """

    event_time: int = field(name="E")
    symbol: Symbol = field(name="s")
    mark_price: str = field(name="p")
    index_price: str = field(name="i")
    estimated_settle_price: str = field(name="P")
    funding_rate: str = field(name="r")
    next_funding_time: int = field(name="T")


class OrderUpdateOrderData(Struct, frozen=True):
    """Order details payload embedded in order update messages."""

    symbol: Symbol = field(name="s")
    client_order_id: str = field(name="c")
    side: str = field(name="S")
    order_type: str = field(name="o")
    time_in_force: str = field(name="f")
    quantity: str = field(name="q")
    price: str = field(name="p")
    avg_price: str = field(name="ap")
    last_exec_qty: str = field(name="l")
    cum_exec_qty: str = field(name="z")
    last_exec_price: str = field(name="L")
    commission: str = field(name="n")
    commission_asset: Asset = field(name="N")
    trade_time: int = field(name="T")
    create_time: int = field(name="t")
    is_maker: bool = field(name="m")
    order_id: int = field(name="i")
    position_side: str = field(name="ps")
    status: str = field(name="X")
    reduce_only: bool = field(name="R")


class AccountBalanceData(Struct, frozen=True):
    """Account balance details from account update payloads."""

    asset: Asset = field(name="a")
    wallet_balance: str = field(name="wb")
    cross_wallet_balance: str = field(name="cw")


class PositionUpdateData(Struct, frozen=True):
    """Position details from account update payloads."""

    symbol: Symbol = field(name="s")
    position_amount: str = field(name="pa")
    entry_price: str = field(name="ep")
    cumulative_realized: str = field(name="cr")
    unrealized_pnl: str = field(name="up")
    position_side: str = field(name="ps")


class AccountUpdateData(Struct, frozen=True):
    """Account update data including balances and positions."""

    balances: list[AccountBalanceData] = field(name="B")
    positions: list[PositionUpdateData] = field(name="P")
    maintenance_margin: str = field(name="m")
    maintenance_margin_level: str = field(name="mm")
    unrealized_pnl: str = field(name="u")
    unrealized_pnl_usd: str = field(name="up")


class PositionAccountData(Struct, frozen=True):
    """Position update data including balances and positions."""

    balances: list[AccountBalanceData] = field(name="B")
    positions: list[PositionUpdateData] = field(name="P")


class OrderUpdateStreamUpdate(
    Struct, frozen=True, tag_field="e", tag="ORDER_TRADE_UPDATE"
):
    """Order status update from the exchange (user data stream).

    Provides real-time order state changes including partial fills, cancellations,
    and rejections. Contains full order details and execution information. Triggered
    whenever an order's state changes.

    Docs: https://developers.binance.com/docs/derivatives/usds-margined-futures/websocket-market-streams/Order-Update

    Example payload::

        {
          "e": "ORDER_TRADE_UPDATE",    // event type
          "E": 1568014460893,           // event time (ms)
          "T": 1568014460891,           // transaction time (ms)
          "o": {
            "s": "BTCUSDT",             // symbol
            "c": "client_order_1",      // client order ID
            "S": "BUY",                 // side
            "o": "LIMIT",               // order type
            "f": "GTC",                 // time in force
            "q": "1.0",                 // quantity
            "p": "30000.0",             // price
            "ap": "30000.0",            // average price
            "l": "0.1",                 // last executed qty
            "z": "0.5",                 // cumulative filled qty
            "L": "30000.0",             // last executed price
            "n": "0.01",                // commission
            "N": "USDT",                // commission asset
            "T": 1568014460891,         // trade time
            "t": 123456,                // order creation time
            "m": false,                 // is maker
            "i": 1,                     // order ID
            "ps": "LONG"                // position side
          }
        }
    """

    event_time: int = field(name="E")
    transaction_time: int = field(name="T")
    order: OrderUpdateOrderData = field(name="o")


class AccountUpdateStreamUpdate(
    Struct, frozen=True, tag_field="e", tag="ACCOUNT_UPDATE"
):
    """Account balance and margin status update (user data stream).

    Provides balance changes, margin levels, and PnL updates. Triggered by balance
    changes from trades, deposits, withdrawals, or funding payments. Essential for
    monitoring account health and margin requirements.

    Docs: https://developers.binance.com/docs/derivatives/usds-margined-futures/websocket-market-streams/Account-Update

    Example payload::

        {
          "e": "ACCOUNT_UPDATE",        // event type
          "E": 1568014460893,           // event time (ms)
          "T": 1568014460891,           // transaction time (ms)
          "a": {
            "B": [
              {
                "a": "USDT",            // asset
                "wb": "1000.0",         // wallet balance
                "cw": "950.0"           // cross wallet balance
              }
            ],
            "P": [],                    // positions (array)
            "m": "1.0",                 // maintenance margin requirement
            "mm": "0.5",                // maintenance margin level
            "u": "0.01",                // unrealized PnL
            "up": "10.0"                // unrealized PnL in USD
          }
        }
    """

    event_time: int = field(name="E")
    transaction_time: int = field(name="T")
    account_data: AccountUpdateData = field(name="a")


class PositionUpdateStreamUpdate(Struct, frozen=True):
    """Position size and entry price update (user data stream).

    Contains position changes for each symbol including size (positive for long,
    negative for short), entry price, and unrealized PnL. Included as part of
    ACCOUNT_UPDATE events. Filtered to only non-zero positions.

    Docs: https://developers.binance.com/docs/derivatives/usds-margined-futures/websocket-market-streams/Position-Update

    Example payload::

        {
          "e": "ACCOUNT_UPDATE",        // event type (part of account update)
          "E": 1568014460893,           // event time (ms)
          "T": 1568014460891,           // transaction time (ms)
          "a": {
            "P": [
              {
                "s": "BTCUSDT",         // symbol
                "pa": "1.0",            // position amount (quantity)
                "ep": "30000.0",        // entry price
                "cr": "0.01",           // cumulative realized
                "up": "100.0",          // unrealized PnL
                "ps": "LONG"            // position side
              }
            ],
            "B": []                     // balances (array)
          }
        }
    """

    event_type: str = field(name="e")
    event_time: int = field(name="E")
    transaction_time: int = field(name="T")
    account_data: AccountUpdateData = field(name="a")


class ExecutionReportStreamUpdate(Struct, frozen=True):
    """Trade execution details for an order (user data stream).

    Contains details of executed trades, including price, quantity, fees, and
    execution timestamp. Only includes events where quantity was actually traded
    (ignores filled: 0 events). Part of the order update stream.

    Docs: https://developers.binance.com/docs/derivatives/usds-margined-futures/websocket-market-streams/Execution-Report

    Example payload::

        {
          "e": "executionReport",       // event type
          "E": 1568014460893,           // event time (ms)
          "T": 1568014460891,           // transaction time (ms)
          "o": {
            "s": "BTCUSDT",             // symbol
            "c": "client_order_1",      // client order ID
            "S": "BUY",                 // side
            "o": "LIMIT",               // order type
            "f": "GTC",                 // time in force
            "q": "1.0",                 // quantity
            "p": "30000.0",             // price
            "ap": "30000.0",            // average price
            "l": "0.1",                 // last executed qty
            "z": "0.5",                 // cumulative filled qty
            "L": "30000.0",             // last executed price
            "n": "0.01",                // commission (fee)
            "N": "USDT",                // commission asset
            "T": 1568014460891,         // trade time
            "t": 123456,                // order creation time
            "m": false,                 // is maker
            "i": 1,                     // order ID
            "ps": "LONG"                // position side
          }
        }
    """

    event_type: str = field(name="e")
    event_time: int = field(name="E")
    transaction_time: int = field(name="T")
    order: OrderUpdateOrderData = field(name="o")
