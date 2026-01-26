"""Structs for deserializing Bybit V5 websocket stream events."""

from __future__ import annotations

from msgspec import Struct, field

from framework.base.common import (
    Instrument,
    InstrumentCollection,
    InstrumentType,
    Venue,
)
from framework.base.stream.models import (
    AccountMsg,
    Execution,
    Moments,
    Order,
    OrderTimeInForce,
    OrderbookLevel,
    OrderbookMsg,
    PositionMsg,
    TickerMsg,
    Trade,
    TradeMsg,
)
from framework.base.tools import EnumMap, SimpleCache
from mm_toolbox.time import time_ns


BYBIT_TIF_MAP = EnumMap(
    OrderTimeInForce,
    {
        OrderTimeInForce.GTC: "GTC",
        OrderTimeInForce.IOC: "IOC",
        OrderTimeInForce.FOK: "FOK",
        OrderTimeInForce.PO: "PostOnly",
    },
)


class BybitTickerMsg(Struct, rename="camel", frozen=True):
    """24-hour ticker statistics for a perpetual contract.

    Provides real-time market statistics including mark price, index price, funding
    rate, open interest, and 24-hour high/low/volume data. Used for monitoring market
    conditions and ticker displays.

    Docs: https://bybit-exchange.github.io/docs/v5/websocket/public/ticker

    Example payload::

        {
          "symbol": "BTCUSDT",               // trading symbol
          "tickDirection": "UpTick",         // tick direction
          "price24hPcnt": "0.035",           // 24h price change percent
          "lastPrice": "30000.50",           // last trade price
          "prevPrice24h": "29000.00",        // price 24h ago
          "highPrice24h": "31000.00",        // 24h high price
          "lowPrice24h": "28000.00",         // 24h low price
          "prevPrice1h": "29900.00",         // price 1h ago
          "markPrice": "30000.00",           // current mark price
          "indexPrice": "29995.25",          // index price
          "openInterest": "100000.50",       // total open interest
          "openInterestValue": "3000050000", // open interest value
          "turnover24h": "5000000000",       // 24h turnover
          "volume24h": "100000",             // 24h volume
          "nextFundingTime": 1568014500000,  // next funding time (ms)
          "fundingRate": "0.0001"            // current funding rate
        }
    """

    symbol: str
    tick_direction: str
    price_24h_pcnt: float
    last_price: float
    prev_price_24h: float
    high_price_24h: float
    low_price_24h: float
    prev_price_1h: float
    mark_price: float
    index_price: float
    open_interest: float
    open_interest_value: float
    turnover_24h: float
    volume_24h: float
    next_funding_time: int
    funding_rate: float

    def to_ticker_msg(
        self,
        venue: Venue,
        instrument_collection: InstrumentCollection,
        exch_time_ns: int,
    ) -> TickerMsg:
        instrument = instrument_collection.get(venue, self.symbol)
        if not instrument:
            raise KeyError(f"Instrument not found for {venue}:{self.symbol}")

        return TickerMsg(
            moments=Moments(exch_time_ns=exch_time_ns),
            venue=venue,
            instrument=instrument,
            mark_price=float(self.mark_price),
            index_price=float(self.index_price),
            funding_rate=float(self.funding_rate),
            next_funding_time_ms=float(self.next_funding_time),
            open_interest=float(self.open_interest),
            avg_volume_24h=float(self.volume_24h),
            price_chg_24h_pct=float(self.price_24h_pcnt),
        )


class BybitOrderbookMsg(Struct, rename="camel", frozen=True):
    """Orderbook depth snapshot or update.

    Provides bid and ask levels for a symbol. Can represent either a full snapshot
    or a differential update depending on the subscription type. Each level contains
    price and size.

    Docs: https://bybit-exchange.github.io/docs/v5/websocket/public/orderbook

    Example payload::

        {
          "s": "BTCUSDT",                   // symbol
          "b": [                            // bids (best to worst)
            {"price": "30000.00", "size": "1.0"},
            {"price": "29999.50", "size": "2.0"}
          ],
          "a": [                            // asks (best to worst)
            {"price": "30001.00", "size": "1.5"},
            {"price": "30002.00", "size": "3.0"}
          ],
          "u": 12345,                       // update ID
          "seq": 67890                      // sequence number
        }
    """

    symbol: str = field(name="s")

    # Since OrderbookLevel shares the exact same names for
    # prize and size, we can get away with using it directly.
    #
    # As there is no 'n', the default works and is never decoded.
    bids: list[OrderbookLevel] = field(name="b")
    asks: list[OrderbookLevel] = field(name="a")

    update_id: int = field(name="u")
    seq: int = field(name="seq")

    def to_orderbook_msg(
        self,
        venue: Venue,
        instrument_collection: InstrumentCollection,
        is_bbo: bool,
        is_snapshot: bool,
        exch_time_ns: int,
    ) -> OrderbookMsg:
        instrument = instrument_collection.get(venue, self.symbol)
        if not instrument:
            raise KeyError(f"Instrument not found for {venue}:{self.symbol}")

        return OrderbookMsg(
            moments=Moments(exch_time_ns=exch_time_ns),
            venue=venue,
            instrument=instrument,
            bids=self.bids,
            asks=self.asks,
            is_bbo=is_bbo,
            is_snapshot=is_snapshot,
        )


class BybitPublicMsg[T](Struct, frozen=True):
    """Generic wrapper for Bybit public websocket messages.

    Wraps public stream data (ticker, trades, orderbook) with metadata including
    topic, message type, and optional server timestamp. The type parameter T is one
    of BybitTickerMsg, BybitTradeMsg, or BybitOrderbookMsg.

    Docs: https://bybit-exchange.github.io/docs/v5/websocket/public/

    Example payload::

        {
          "topic": "tickers.BTCUSDT",       // subscription topic
          "type": "snapshot",               // message type (snapshot/delta)
          "data": {...},                    // typed data (ticker/trade/orderbook)
          "ts": 1568014460891               // server timestamp (ms, optional)
        }
    """

    topic: str
    type: str
    data: T
    ts: int | None = None


class BybitTrade(Struct, frozen=True):
    """Individual trade execution on the market.

    Represents a single trade for a symbol including price, quantity, side, and
    execution time. Contains unique trade ID and sequence number for deduplication.

    Docs: https://bybit-exchange.github.io/docs/v5/websocket/public/trade

    Example payload::

        {
          "T": 1568014460891,               // trade time (ms)
          "S": "BTCUSDT",                   // symbol
          "s": "Buy",                       // side (Buy/Sell)
          "v": "1.0",                       // volume (quantity)
          "p": "30000.50",                  // price
          "i": "1234567890",                // trade ID
          "seq": 12345                      // sequence number
        }
    """

    time_ms: int = field(name="T")
    symbol: str = field(name="S")
    side: str = field(name="s")
    size: float = field(name="v")
    price: float = field(name="p")
    id: str = field(name="i")
    seq: int

    def to_trade(self) -> Trade:
        return Trade(
            time_ms=int(self.time_ms),
            price=float(self.price),
            is_buy=self.side == "Buy",
            size=float(self.size),
        )


class BybitTradeMsg(Struct, frozen=True):
    """Wrapper for Bybit public trade stream messages.

    Contains a list of recent trades for a symbol. Includes server timestamp and
    message type (typically "snapshot" for initial data). Used for deduplicating
    trades by sequence number.

    Docs: https://bybit-exchange.github.io/docs/v5/websocket/public/trade

    Example payload::

        {
          "topic": "publicTrade.BTCUSDT",   // subscription topic
          "type": "snapshot",               // message type
          "ts": 1568014460891,              // server timestamp (ms)
          "data": [
            {
              "T": 1568014460891,           // trade time (ms)
              "S": "BTCUSDT",               // symbol
              "s": "Buy",                   // side
              "v": "1.0",                   // volume
              "p": "30000.50",              // price
              "i": "1234567890",            // trade ID
              "seq": 12345                  // sequence number
            }
          ]
        }
    """

    topic: str
    type: str
    ts: int
    data: list[BybitTradeMsg]

    def to_trade_msg(
        self,
        venue: Venue,
        instrument_collection: InstrumentCollection,
        symbol_to_seq_cache: SimpleCache,
        symbol_override: str | None = None,
    ) -> TradeMsg | None:
        if not self.data:
            return None

        symbol = symbol_override or self.data[0].symbol
        instrument = instrument_collection.get(venue, symbol)
        if not instrument:
            raise KeyError(f"Instrument not found for {venue}:{symbol}")

        trades: list[Trade] = []
        for trade_data in self.data:
            trade_symbol = trade_data.symbol or symbol
            trade_key = f"{trade_symbol}_{trade_data.seq}"
            if not symbol_to_seq_cache.is_higher(trade_key, trade_data.seq):
                continue
            trades.append(trade_data.to_trade())

        if not trades:
            return None

        return TradeMsg(
            moments=Moments(
                exch_time_ns=self.ts * 1_000_000,
                recv_time_ns=time_ns(),
            ),
            venue=venue,
            instrument=instrument,
            trades=trades,
        )


class BybitPrivateMsg[T](Struct, rename="camel", frozen=True):
    """Generic wrapper for Bybit private websocket messages.

    Wraps private stream data (orders, positions, executions, wallet) with metadata
    including topic, message type, and server timestamp. The type parameter T is one
    of BybitPositionMsg, BybitOrderMsg, BybitExecutionMsg, or BybitWalletMsg.

    Docs: https://bybit-exchange.github.io/docs/v5/websocket/private/

    Example payload::

        {
          "topic": "order.linear",          // subscription topic
          "type": "UPDATE",                 // message type (SNAPSHOT/UPDATE)
          "ts": 1568014460891,              // server timestamp (ms)
          "data": [...]                     // array of typed data objects
        }
    """

    topic: str
    type: str
    ts: int
    data: list[T]


class BybitPositionMsg(Struct, rename="camel", frozen=True):
    """Position update for a symbol (private stream).

    Provides complete position data including size, entry price, mark price, leverage,
    PnL, liquidation price, and risk metrics. Includes timestamps and risk management
    settings (TP/SL).

    Docs: https://bybit-exchange.github.io/docs/v5/websocket/private/position

    Example payload::

        {
          "positionIdx": 0,                 // position index (0=one-way, 1=buy, 2=sell)
          "tradeMode": 0,                   // trade mode
          "riskId": 1,                      // risk ID
          "riskLimitValue": "100000",       // risk limit value
          "symbol": "BTCUSDT",              // symbol
          "side": "Buy",                    // position side
          "size": "1.0",                    // position size
          "entryPrice": "30000.0",          // entry price
          "leverage": "10",                 // leverage
          "positionValue": "30000.0",       // position value
          "positionBalance": "3000.0",      // position balance
          "markPrice": "30500.0",           // mark price
          "positionIm": "3000.0",           // initial margin
          "positionImByMp": "3000.0",       // IM by mark price
          "positionMm": "1500.0",           // maintenance margin
          "positionMmByMp": "1500.0",       // MM by mark price
          "takeProfit": "31000.0",          // take profit price
          "stopLoss": "29000.0",            // stop loss price
          "trailingStop": "0",              // trailing stop
          "unrealisedPnl": "500.0",         // unrealized PnL
          "curRealisedPnl": "100.0",        // current realized PnL
          "cumRealisedPnl": "1000.0",       // cumulative realized PnL
          "sessionAvgPrice": "30200.0",     // session average price
          "createdTime": "1568014460891",   // creation time (ms)
          "updatedTime": "1568014461891",   // update time (ms)
          "tpslMode": "Full",               // TP/SL mode
          "liqPrice": "25000.0",            // liquidation price
          "bustPrice": "24000.0",           // bankruptcy price
          "category": "linear",             // product category
          "positionStatus": "Normal",       // position status
          "adlRankIndicator": 0,            // ADL rank
          "autoAddMargin": 0,               // auto-add margin enabled
          "leverageSysUpdatedTime": "0",    // leverage update time
          "mmrSysUpdatedTime": "0",         // MMR update time
          "seq": 12345,                     // sequence number
          "isReduceOnly": false             // reduce-only flag
        }
    """

    position_idx: int
    trade_mode: int
    risk_id: int
    risk_limit_value: str
    symbol: str
    side: str
    size: str
    entry_price: str
    leverage: str
    position_value: str
    position_balance: str
    mark_price: str
    position_im: str
    position_im_by_mp: str
    position_mm: str
    position_mm_by_mp: str
    take_profit: str
    stop_loss: str
    trailing_stop: str
    unrealised_pnl: str
    cur_realised_pnl: str
    cum_realised_pnl: str
    session_avg_price: str
    created_time: str
    updated_time: str
    tpsl_mode: str
    liq_price: str
    bust_price: str
    category: str
    position_status: str
    adl_rank_indicator: int
    auto_add_margin: int
    leverage_sys_updated_time: str
    mmr_sys_updated_time: str
    seq: int
    is_reduce_only: bool

    def to_position_msg(
        self,
        venue: Venue,
        instrument_collection: InstrumentCollection,
        exch_time_ns: int | None = None,
    ) -> PositionMsg | None:
        instrument = instrument_collection.get(venue, self.symbol)
        if not instrument:
            raise KeyError(f"Instrument not found for {venue}:{self.symbol}")

        size = float(self.size or 0)
        if size == 0:
            return None

        exchange_time_ns = exch_time_ns or time_ns()
        return PositionMsg(
            moments=Moments(
                exch_time_ns=exchange_time_ns,
                recv_time_ns=time_ns(),
            ),
            venue=venue,
            instrument=instrument,
            price=float(self.entry_price or 0),
            is_long=self.side == "Buy",
            size=abs(size),
        )


class BybitOrderMsg(Struct, rename="camel", frozen=True):
    """Order update for a submitted order (private stream).

    Provides order status, pricing, execution details, and metadata. Includes reject
    reasons, trigger information (for conditional orders), and creation/update times.

    Docs: https://bybit-exchange.github.io/docs/v5/websocket/private/order

    Example payload::

        {
          "symbol": "BTCUSDT",              // symbol
          "orderId": "123456789",           // order ID
          "side": "Buy",                    // order side
          "orderType": "Limit",             // order type
          "cancelType": "",                 // cancel type (if cancelled)
          "price": "30000.0",               // limit price
          "qty": "1.0",                     // order quantity
          "timeInForce": "GTC",             // time in force
          "orderStatus": "New",             // order status
          "orderLinkId": "client_order_1",  // client order ID
          "lastPriceOnCreated": "30100.0",  // mark price at creation
          "reduceOnly": false,              // reduce-only flag
          "leavesQty": "1.0",               // remaining quantity
          "leavesValue": "30000.0",         // remaining value
          "cumExecQty": "0",                // cumulative executed qty
          "cumExecValue": "0",              // cumulative executed value
          "avgPrice": "0",                  // average fill price
          "blockTradeId": "",               // block trade ID
          "positionIdx": 0,                 // position index
          "cumExecFee": "0",                // cumulative fee
          "closedPnl": "0",                 // closed PnL
          "createdTime": "1568014460891",   // creation time (ms)
          "updatedTime": "1568014460891",   // update time (ms)
          "rejectReason": "",               // rejection reason
          "stopOrderType": "TAKE_PROFIT",   // stop order type (if conditional)
          "triggerDirection": 1,            // trigger direction
          "triggerBy": "LastPrice",         // trigger by (LastPrice/IndexPrice)
          "closeOnTrigger": false,          // close-on-trigger flag
          "category": "linear",             // product category
          "placeType": "",                  // place type
          "placeType": ""                   // create type
        }
    """

    symbol: str
    order_id: str
    side: str
    order_type: str
    cancel_type: str
    price: str
    qty: str
    time_in_force: str
    order_status: str
    order_link_id: str
    last_price_on_created: str
    reduce_only: bool
    leaves_qty: str
    leaves_value: str
    cum_exec_qty: str
    cum_exec_value: str
    avg_price: str
    block_trade_id: str
    position_idx: int
    cum_exec_fee: str
    closed_pnl: str
    created_time: str
    updated_time: str
    reject_reason: str
    stop_order_type: str
    trigger_direction: int
    trigger_by: str
    close_on_trigger: bool
    category: str
    place_type: str

    def to_order(self, tif_map: EnumMap[OrderTimeInForce] | None = None) -> Order:
        tif_lookup = tif_map or BYBIT_TIF_MAP
        tif = tif_lookup.str_to_enum(self.time_in_force, default=OrderTimeInForce.GTC)
        size = float(self.qty or 0.0)
        cum_exec_qty = float(self.cum_exec_qty or 0.0)

        return Order(
            create_time_ms=float(self.created_time or 0),
            order_id=str(self.order_id),
            price=float(self.price or 0.0),
            is_buy=self.side == "Buy",
            size=size,
            size_remaining=max(0.0, size - cum_exec_qty),
            tif=tif,
            is_cancelled=(
                self.order_status
                in [
                    "Cancelled",
                    "Rejected",
                    "Deactivated",
                    "CancelledByReduceOnly",
                ]
            ),
            is_reduce_only=bool(self.reduce_only),
            client_order_id=self.order_link_id or None,
        )


class BybitExecutionMsg(Struct, rename="camel", frozen=True):
    """Trade execution/fill details (private stream).

    Provides details of a trade execution including filled price, quantity, fees, and
    execution classification. Includes order information and mark price at execution.

    Docs: https://bybit-exchange.github.io/docs/v5/websocket/private/execution

    Example payload::

        {
          "category": "linear",             // product category
          "symbol": "BTCUSDT",              // symbol
          "closedSize": "0",                // closed size
          "execFee": "0.15",                // execution fee
          "execId": "1234567890",           // execution ID
          "execPrice": "30000.0",           // execution price
          "execQty": "0.5",                 // execution quantity
          "execType": "Trade",              // execution type
          "execValue": "15000.0",           // execution value
          "feeRate": "0.0005",              // fee rate
          "markPrice": "30050.0",           // mark price
          "indexPrice": "30045.0",          // index price
          "underlyingPrice": "30040.0",     // underlying price
          "leavesQty": "0.5",               // remaining quantity
          "orderId": "123456789",           // order ID
          "orderLinkId": "client_order_1",  // client order ID
          "orderPrice": "30000.0",          // order price
          "orderQty": "1.0",                // order quantity
          "orderType": "Limit",             // order type
          "stopOrderType": "",              // stop order type
          "side": "Buy",                    // execution side
          "execTime": "1568014460891",      // execution time (ms)
          "isLeverage": "0",                // is leverage trade
          "isMaker": true,                  // is maker
          "seq": 12345,                     // sequence number
          "marketUnit": "USDT",             // market unit
          "execPnl": "0",                   // execution PnL
          "createType": ""                  // create type
        }
    """

    category: str
    symbol: str
    closed_size: str
    exec_fee: str
    exec_id: str
    exec_price: str
    exec_qty: str
    exec_type: str
    exec_value: str
    fee_rate: str
    mark_price: str
    index_price: str
    underlying_price: str
    leaves_qty: str
    order_id: str
    order_link_id: str
    order_price: str
    order_qty: str
    order_type: str
    stop_order_type: str
    side: str
    exec_time: str
    is_leverage: str
    is_maker: bool
    seq: int
    market_unit: str
    exec_pnl: str
    create_type: str

    def to_execution(self) -> Execution:
        return Execution(
            exec_time_ms=float(self.exec_time or 0),
            order_id=str(self.order_id),
            price=float(self.exec_price or 0),
            is_buy=self.side == "Buy",
            size=float(self.exec_qty or 0),
            is_maker=bool(self.is_maker),
            fee_paid=float(self.exec_fee or 0),
            client_order_id=self.order_link_id or None,
        )


class BybitWalletMsg(Struct, rename="camel", frozen=True):
    """Account wallet/balance update (private stream).

    Provides account equity, margin rates, and unrealized PnL. Updated whenever
    balance changes from trades, deposits, or funding payments.

    Docs: https://bybit-exchange.github.io/docs/v5/websocket/private/wallet

    Example payload::

        {
          "totalEquity": "5000.0",          // total account equity
          "accountIMRate": "0.20",          // account initial margin rate
          "accountMMRate": "0.12",          // account maintenance margin rate
          "totalPerpUPL": "500.0"           // total perpetual unrealized PnL
        }
    """

    total_equity: str
    account_im_rate: str = field(name="accountIMRate")
    account_mm_rate: str = field(name="accountMMRate")
    total_perp_upl: str = field(name="totalPerpUPL")

    def to_account_msg(
        self, venue: Venue, exch_time_ns: int | None = None
    ) -> AccountMsg:
        instrument = Instrument(
            venue=venue,
            symbol="",
            base="",
            quote="",
            code=0,
            instrument_type=InstrumentType.PERPETUAL,
        )
        exchange_time_ns = exch_time_ns or time_ns()
        return AccountMsg(
            moments=Moments(
                exch_time_ns=exchange_time_ns,
                recv_time_ns=time_ns(),
            ),
            venue=venue,
            instrument=instrument,
            balance=float(self.total_equity or 0.0),
            initial_margin=float(self.account_im_rate or 0.0),
            maintenance_margin=float(self.account_mm_rate or 0.0),
            unrealized_pnl=float(self.total_perp_upl or 0.0),
        )
