"""Structs for deserializing Binance USDS-M Futures websocket stream events.

The module includes structs for market data streams (ticker, depth, trades) and
user data streams (orders, positions, account updates, executions).
"""

from __future__ import annotations

from msgspec import Struct, field

from framework.base.tools import EnumMap
from framework.base.common import (
    Instrument,
    InstrumentCollection,
    Venue,
)
from framework.base.stream.models import (
    AccountMsg,
    Execution,
    ExecutionMsg,
    Moments,
    OrderbookLevel,
    OrderbookMsg,
    Order,
    OrderMsg,
    PositionMsg,
    TickerMsg,
    Trade,
    TradeMsg,
    OrderTimeInForce,
)
from mm_toolbox.time import time_ns

BINANCE_TIF_MAP = EnumMap(
    enum_class=OrderTimeInForce,
    mapping={
        OrderTimeInForce.GTC: "GTC",
        OrderTimeInForce.PO: "GTX",
        OrderTimeInForce.IOC: "IOC",
        OrderTimeInForce.FOK: "FOK",
    },
)


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
    symbol: str = field(name="s")
    trade_id: int = field(name="t")
    price: str = field(name="p")
    quantity: str = field(name="q")
    trade_type: str = field(name="X")
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


class OrderUpdateOrderData(Struct, frozen=True):
    """Order details payload embedded in order update messages."""

    symbol: str = field(name="s")
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
    commission_asset: str = field(name="N")
    trade_time: int = field(name="T")
    create_time: int = field(name="t")
    is_maker: bool = field(name="m")
    order_id: int = field(name="i")
    position_side: str = field(name="ps")
    status: str = field(name="X")
    reduce_only: bool = field(name="R")


class AccountBalanceData(Struct, frozen=True):
    """Account balance details from account update payloads."""

    asset: str = field(name="a")
    wallet_balance: str = field(name="wb")
    cross_wallet_balance: str = field(name="cw")


class PositionUpdateData(Struct, frozen=True):
    """Position details from account update payloads."""

    symbol: str = field(name="s")
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

    def to_order_msg(
        self, venue: Venue, instrument_collection: InstrumentCollection
    ) -> OrderMsg:
        """Convert an order update payload into an order message.

        Args:
            venue: Venue associated with the stream.
            instrument_collection: Collection of available instruments.

        Returns:
            OrderMsg: Order message.
        """
        order_data = self.order
        instrument = instrument_collection.get(venue, order_data.symbol)

        if not instrument:
            raise KeyError(f"Instrument not found for {venue}:{order_data.symbol}")

        tif = BINANCE_TIF_MAP.str_to_enum(
            order_data.time_in_force,
            default=OrderTimeInForce.GTC,
        )

        size = float(order_data.quantity)
        filled = float(order_data.cum_exec_qty)
        status = str(order_data.status)
        is_cancelled = status in {"CANCELED", "REJECTED", "EXPIRED", "CANCELLED"}
        order = Order(
            create_time_ms=float(order_data.create_time),
            order_id=str(order_data.order_id),
            price=float(order_data.price),
            is_buy=order_data.side == "BUY",
            size=size,
            size_remaining=max(0.0, size - filled),
            tif=tif,
            is_cancelled=is_cancelled,
            is_reduce_only=order_data.reduce_only,
            client_order_id=order_data.client_order_id,
        )

        return OrderMsg(
            moments=Moments(
                exch_time_ns=self.event_time * 1_000_000,
                recv_time_ns=time_ns(),
            ),
            venue=venue,
            instrument=instrument,
            orders=[order],
        )

    def to_execution_msg(
        self, venue: Venue, instrument_collection: InstrumentCollection
    ) -> ExecutionMsg:
        """Convert an order update payload into an execution message.

        Args:
            venue: Venue associated with the stream.
            instrument_collection: Collection of available instruments.

        Returns:
            ExecutionMsg: Execution message.
        """
        order_data = self.order
        if order_data.status != "TRADE":
            raise ValueError(
                f"Execution update expected status TRADE, got {order_data.status}"
            )
        instrument = instrument_collection.get(venue, order_data.symbol)
        if not instrument:
            raise KeyError(f"Instrument not found for {venue}:{order_data.symbol}")
        last_executed_qty = float(order_data.last_exec_qty)
        if last_executed_qty == 0:
            raise ValueError("Execution update has zero executed quantity")

        execution = Execution(
            exec_time_ms=float(order_data.trade_time),
            order_id=str(order_data.order_id),
            price=float(order_data.last_exec_price),
            is_buy=order_data.side == "BUY",
            size=last_executed_qty,
            is_maker=order_data.is_maker,
            fee_paid=float(order_data.commission),
            client_order_id=order_data.client_order_id,
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

    def to_account_msg(self, venue: Venue) -> AccountMsg:
        """Convert account update payload into an account message.

        Args:
            venue: Venue associated with the stream.

        Returns:
            AccountMsg: Normalized account balance update.
        """
        balance_data = self.account_data.balances
        wallet_balance = 0.0

        for balance in balance_data:
            if balance.asset == "USDT":  # Focus on USDT balance
                wallet_balance = float(balance.wallet_balance)
                break

        # Provide a dummy instrument (non-specific) to satisfy schema expectations
        instrument = Instrument.empty()
        return AccountMsg(
            moments=Moments(
                exch_time_ns=self.event_time * 1_000_000,
                recv_time_ns=time_ns(),
            ),
            venue=venue,
            instrument=instrument,
            balance=wallet_balance,
            initial_margin=float(self.account_data.maintenance_margin),
            maintenance_margin=float(self.account_data.maintenance_margin_level),
            unrealized_pnl=float(self.account_data.unrealized_pnl_usd),
        )

    def to_position_msg(
        self, venue: Venue, instrument_collection: InstrumentCollection
    ) -> list[PositionMsg]:
        """Convert account update payload into position messages.

        Args:
            venue: Venue associated with the stream.
            instrument_collection: Collection of available instruments.

        Returns:
            list[PositionMsg]: Position messages for non-zero positions.
        """
        positions: list[PositionMsg] = []
        for position in self.account_data.positions:
            instrument = instrument_collection.get(venue, position.symbol)
            if not instrument:
                raise KeyError(f"Instrument not found for {venue}:{position.symbol}")
            position_amt = float(position.position_amount)
            if position_amt == 0.0:
                continue
            positions.append(
                PositionMsg(
                    moments=Moments(
                        exch_time_ns=self.event_time * 1_000_000,
                        recv_time_ns=time_ns(),
                    ),
                    venue=venue,
                    instrument=instrument,
                    price=float(position.entry_price),
                    is_long=position_amt > 0,
                    size=abs(position_amt),
                )
            )
        return positions


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

    def to_position_msg(
        self, venue: Venue, instrument_collection: InstrumentCollection
    ) -> PositionMsg:
        """Convert position update payload into a position message.

        Args:
            venue: Venue associated with the stream.
            instrument_collection: Collection of available instruments.

        Returns:
            PositionMsg: Position message.
        """
        positions_data = self.account_data.positions

        # Process position updates
        for position in positions_data:
            instrument = instrument_collection.get(venue, position.symbol)

            if not instrument:
                raise KeyError(f"Instrument not found for {venue}:{position.symbol}")

            position_amt = float(position.position_amount)
            if position_amt == 0:
                continue

            return PositionMsg(
                moments=Moments(
                    exch_time_ns=self.event_time * 1_000_000,
                    recv_time_ns=time_ns(),
                ),
                venue=venue,
                instrument=instrument,
                price=float(position.entry_price),
                is_long=position_amt > 0,
                size=abs(position_amt),
            )

        raise ValueError("Position update has no non-zero positions")


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

    def to_execution_msg(
        self, venue: Venue, instrument_collection: InstrumentCollection
    ) -> ExecutionMsg:
        """Convert execution report payload into an execution message.

        Args:
            venue: Venue associated with the stream.
            instrument_collection: Collection of available instruments.

        Returns:
            ExecutionMsg: Execution message.
        """
        order_data = self.order
        instrument = instrument_collection.get(venue, order_data.symbol)

        if not instrument:
            raise KeyError(f"Instrument not found for {venue}:{order_data.symbol}")

        # Only process if there was an execution
        last_executed_qty = float(order_data.last_exec_qty)
        if last_executed_qty == 0:
            raise ValueError("Execution report has zero executed quantity")

        execution = Execution(
            exec_time_ms=float(order_data.trade_time),
            order_id=str(order_data.order_id),
            price=float(order_data.last_exec_price),
            is_buy=order_data.side == "BUY",
            size=last_executed_qty,
            is_maker=order_data.is_maker,
            fee_paid=float(order_data.commission),
            client_order_id=order_data.client_order_id,
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
