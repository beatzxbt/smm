"""Structs for deserializing Binance USDS-M Futures websocket stream events.

This module provides dataclass-like structs that deserialize raw API payloads from
Binance's websocket streams into strongly-typed Python objects. Each struct maps
directly to a specific stream event type, handling field name conversions via msgspec.

The module includes structs for market data streams (ticker, depth, trades) and
user data streams (orders, positions, account updates, executions).
"""

from __future__ import annotations

from msgspec import Struct, field

from framework.base.common import (
    Instrument,
    InstrumentCollection,
    Venue,
    InstrumentType,
)
from framework.base.stream.models import (
    Execution,
    ExecutionMsg,
    Moments,
    OrderbookLevel,
    OrderbookMsg,
    TickerMsg,
    Trade,
    TradeMsg,
    OrderTimeInForce,
)
from mm_toolbox.time import time_ns

# Binance TIF mapping
BINANCE_TIF_MAP: dict[str, OrderTimeInForce] = {
    "GTC": OrderTimeInForce.GTC,
    "GTX": OrderTimeInForce.PO,
    "IOC": OrderTimeInForce.IOC,
    "FOK": OrderTimeInForce.FOK,
}


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
    symbol: str = field(name="s")
    best_bid_price: str = field(name="b")
    best_bid_qty: str = field(name="B")
    best_ask_price: str = field(name="a")
    best_ask_qty: str = field(name="A")

    def is_outdated(self, last_update_id: int) -> bool:
        return self.update_id <= last_update_id

    def to_orderbook_msg(
        self, venue: Venue, instrument_collection: InstrumentCollection
    ) -> OrderbookMsg:
        instrument = instrument_collection.get(venue, self.symbol)
        if not instrument:
            raise KeyError(f"Instrument not found for {venue}:{self.symbol}")

        return OrderbookMsg(
            moments=Moments(
                exch_time_ns=self.event_time * 1_000_000,  # ms -> ns
                recv_time_ns=time_ns(),
            ),
            venue=venue,
            instrument=instrument,
            bids=[OrderbookLevel(float(self.best_bid_price), float(self.best_bid_qty))],
            asks=[OrderbookLevel(float(self.best_ask_price), float(self.best_ask_qty))],
            is_bbo=True,
            is_snapshot=False,
        )


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
    symbol: str = field(name="s")
    first_update_id: int = field(name="U")
    final_update_id: int = field(name="u")
    prev_final_update_id: int = field(name="pu")
    bids: list[tuple[str, str]] = field(name="b")
    asks: list[tuple[str, str]] = field(name="a")

    def is_outdated(self, last_update_id: int) -> bool:
        return self.final_update_id <= last_update_id

    def to_orderbook_msg(
        self, venue: Venue, instrument_collection: InstrumentCollection
    ) -> OrderbookMsg:
        instrument = instrument_collection.get(venue, self.symbol)
        if not instrument:
            raise KeyError(f"Instrument not found for {venue}:{self.symbol}")

        return OrderbookMsg(
            moments=Moments(
                exch_time_ns=self.event_time * 1_000_000,  # ms -> ns
                recv_time_ns=time_ns(),
            ),
            venue=venue,
            instrument=instrument,
            bids=[
                OrderbookLevel(float(price), float(size)) for price, size in self.bids
            ],
            asks=[
                OrderbookLevel(float(price), float(size)) for price, size in self.asks
            ],
            is_bbo=False,
            is_snapshot=False,
        )


class TradeStreamUpdate(Struct, frozen=True):
    """Individual trade execution for a symbol.

    Delivers real-time trade data as transactions occur, including price, quantity,
    and aggressor side. Useful for monitoring market activity and building trade
    flow analytics.

    Docs: https://developers.binance.com/docs/derivatives/usds-margined-futures/websocket-market-streams/Individual-Symbol-Trade-Streams

    Example payload::

        {
          "E": 1568014460893,           // event time (ms)
          "T": 1568014460891,           // transaction time (ms)
          "s": "BTCUSDT",               // symbol
          "t": 123456,                  // trade ID
          "p": "30000.50",              // price
          "q": "0.1",                   // quantity
          "m": false                    // is buyer the market maker
        }
    """

    event_time: int = field(name="E")
    transaction_time: int = field(name="T")
    symbol: str = field(name="s")
    trade_id: int = field(name="t")
    price: str = field(name="p")
    quantity: str = field(name="q")
    is_buyer_maker: bool = field(name="m")

    def to_trade_msg(
        self, venue: Venue, instrument_collection: InstrumentCollection
    ) -> TradeMsg:
        instrument = instrument_collection.get(venue, self.symbol)
        if not instrument:
            raise KeyError(f"Instrument not found for {venue}:{self.symbol}")

        return TradeMsg(
            moments=Moments(
                exch_time_ns=self.event_time * 1_000_000,  # ms -> ns
                recv_time_ns=time_ns(),
            ),
            venue=venue,
            instrument=instrument,
            trades=[
                Trade(
                    time_ms=self.transaction_time,
                    price=float(self.price),
                    is_buy=not self.is_buyer_maker,
                    size=float(self.quantity),
                )
            ],
        )


class OpenInterestInfo(Struct, frozen=True):
    open_interest: float


class TickerStats24h(Struct, frozen=True):
    price_chg_24h_pct: float
    avg_volume_24h: float


class TickerStats24hStreamUpdate(Struct, frozen=True):
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
    symbol: str = field(name="s")
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
    symbol: str = field(name="s")
    mark_price: str = field(name="p")
    index_price: str = field(name="i")
    estimated_settle_price: str = field(name="P")
    funding_rate: str = field(name="r")
    next_funding_time: int = field(name="T")

    def to_ticker_msg(
        self,
        venue: Venue,
        instrument_collection: InstrumentCollection,
        instrument_to_open_interest_map: dict[Instrument, OpenInterestInfo],
        instrument_to_ticker_stats_24h_map: dict[Instrument, TickerStats24h],
    ) -> TickerMsg:
        instrument = instrument_collection.get(venue, self.symbol)
        if not instrument:
            raise KeyError(f"Instrument not found for {venue}:{self.symbol}")
        open_interest = instrument_to_open_interest_map.get(
            instrument, OpenInterestInfo(open_interest=0.0)
        )
        ticker_stats_24h = instrument_to_ticker_stats_24h_map.get(
            instrument, TickerStats24h(price_chg_24h_pct=0.0, avg_volume_24h=0.0)
        )

        return TickerMsg(
            moments=Moments(
                exch_time_ns=self.event_time * 1_000_000,  # ms -> ns
                recv_time_ns=time_ns(),
            ),
            venue=venue,
            instrument=instrument,
            mark_price=float(self.mark_price),
            index_price=float(self.index_price),
            funding_rate=float(self.funding_rate),
            next_funding_time_ms=self.next_funding_time,
            open_interest=open_interest.open_interest,
            avg_volume_24h=ticker_stats_24h.avg_volume_24h,
            price_chg_24h_pct=ticker_stats_24h.price_chg_24h_pct,
        )


class OrderUpdateStreamUpdate(Struct, frozen=True):
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

    event_type: str = field(name="e")
    event_time: int = field(name="E")
    transaction_time: int = field(name="T")
    order: dict = field(name="o")

    def to_order_msg(self, venue: Venue, symbol_map: dict[str, Instrument]):
        from framework.base.stream.models import OrderTimeInForce

        order_data = self.order
        symbol = order_data["s"]
        instrument = symbol_map.get(symbol.lower())

        if not instrument:
            return None

        BINANCE_TIF_MAP.get(order_data.get("timeInForce", "GTC"), OrderTimeInForce.GTC)

        execution = Execution(
            exec_time_ms=float(order_data["T"]),
            order_id=str(order_data["i"]),
            price=float(order_data["L"]),  # Last executed price
            is_buy=order_data["S"] == "BUY",
            size=float(order_data["l"]),  # Last executed quantity
            is_maker=order_data["m"],  # Is maker
            fee_paid=float(order_data.get("n", 0)),  # Commission
            client_order_id=order_data.get("c"),
        )

        return ExecutionMsg(
            moments=Moments(
                exch_time_ns=self.event_time * 1_000_000,
                recv_time_ns=time_ns(),
            ),
            venue=venue,
            instrument=instrument,
            executions=[execution],
        )


class AccountUpdateStreamUpdate(Struct, frozen=True):
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

    event_type: str = field(name="e")
    event_time: int = field(name="E")
    transaction_time: int = field(name="T")
    account_data: dict = field(name="a")

    def to_account_msg(self, venue: Venue):
        from framework.base.stream.models import AccountMsg

        balance_data = self.account_data.get("B", [])
        wallet_balance = 0.0

        for balance in balance_data:
            if balance["a"] == "USDT":  # Focus on USDT balance
                wallet_balance = float(balance["wb"])
                break

        # Provide a dummy instrument (non-specific) to satisfy schema expectations
        instrument = Instrument(
            venue=venue,
            symbol="",
            base="",
            quote="",
            code=0,
            instrument_type=InstrumentType.PERPETUAL,
        )
        return AccountMsg(
            moments=Moments(
                exch_time_ns=self.event_time * 1_000_000,
                recv_time_ns=time_ns(),
            ),
            venue=venue,
            instrument=instrument,
            balance=wallet_balance,
            initial_margin=float(self.account_data.get("m", 0)),
            maintenance_margin=float(self.account_data.get("mm", 0)),
            unrealized_pnl=float(self.account_data.get("up", 0)),
        )


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
    account_data: dict = field(name="a")

    def to_position_msg(self, venue: Venue, symbol_map: dict[str, Instrument]):
        from framework.base.stream.models import PositionMsg

        positions_data = self.account_data.get("P", [])

        # Process position updates
        for position in positions_data:
            symbol = position["s"]
            instrument = symbol_map.get(symbol.lower())

            if not instrument:
                continue

            position_amt = float(position.get("pa", 0))
            if position_amt == 0:
                continue

            return PositionMsg(
                moments=Moments(
                    exch_time_ns=self.event_time * 1_000_000,
                    recv_time_ns=time_ns(),
                ),
                venue=venue,
                instrument=instrument,
                price=float(position.get("ep", 0)),
                is_long=position_amt > 0,
                size=abs(position_amt),
            )

        return None


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
    order: dict = field(name="o")

    def to_execution_msg(self, venue: Venue, symbol_map: dict[str, Instrument]):
        from framework.base.stream.models import ExecutionMsg

        order_data = self.order
        symbol = order_data["s"]
        instrument = symbol_map.get(symbol.lower())

        if not instrument:
            return None

        # Only process if there was an execution
        last_executed_qty = float(order_data.get("l", 0))
        if last_executed_qty == 0:
            return None

        execution = Execution(
            exec_time_ms=float(order_data["T"]),
            order_id=str(order_data["i"]),
            price=float(order_data["L"]),
            is_buy=order_data["S"] == "BUY",
            size=last_executed_qty,
            is_maker=order_data.get("m", False),
            fee_paid=float(order_data.get("n", 0)),
            client_order_id=order_data.get("c"),
        )

        return ExecutionMsg(
            moments=Moments(
                exch_time_ns=self.event_time * 1_000_000,
                recv_time_ns=time_ns(),
            ),
            venue=venue,
            instrument=instrument,
            executions=[execution],
        )
