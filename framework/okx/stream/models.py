"""Structs for deserializing OKX V5 websocket stream events.

This module provides dataclass-like structs that deserialize raw API payloads from
OKX's websocket streams into strongly-typed Python objects. Each struct maps directly
to a specific stream event type, handling field name conversions via msgspec.

The module includes structs for public streams (ticker, depth, trades) and private
streams (orders, positions, executions, wallet).
"""

from __future__ import annotations

from msgspec import Struct, field

from framework.base.common import (
    Asset,
    ClientOrderId,
    Instrument,
    InstrumentCollection,
    OrderId,
    Symbol,
    Venue,
)
from framework.base.schema import MessageId, Moments
from framework.base.stream.models import (
    Balance,
    AccountMsg,
    Execution,
    Order,
    OrderTimeInForce,
    OrderbookLevel,
    OrderbookMsg,
    PositionMsg,
    TickerMsg,
    Trade,
)
from framework.base.tools import EnumMap
from mm_toolbox.time import time_ns


OKX_TIF_MAP = EnumMap(
    OrderTimeInForce,
    {
        OrderTimeInForce.GTC: "normal",
        OrderTimeInForce.IOC: "ioc",
        OrderTimeInForce.FOK: "fok",
        OrderTimeInForce.PO: "post_only",
    },
)


class OkxTickerMsg(Struct, frozen=True):
    """24-hour ticker statistics for a perpetual contract.

    Provides real-time market statistics including mark price, index price, funding
    rate, open interest, and 24-hour volume data. Used for monitoring market
    conditions and ticker displays.

    Docs: https://www.okx.com/docs-v5/en/#websocket-api-public-channel-tickers-channel

    Example payload::

        {
          "instId": "BTC-USDT-SWAP",             // instrument ID
          "last": "30000.5",                     // last trade price
          "lastSz": "1.0",                       // last trade size
          "askPx": "30001.0",                    // best ask price
          "askSz": "10.0",                       // best ask size
          "bidPx": "30000.0",                    // best bid price
          "bidSz": "15.0",                       // best bid size
          "open24h": "29000.0",                  // 24h open price
          "high24h": "31000.0",                  // 24h high price
          "low24h": "28000.0",                   // 24h low price
          "volCcy24h": "5000000000",             // 24h volume in quote currency
          "vol24h": "100000",                    // 24h volume in base currency
          "sodUtc0": "29500.0",                  // open price at UTC 0
          "sodUtc8": "29800.0",                  // open price at UTC 8
          "ts": "1597026383085",                 // update time (ms)
          "markPx": "30000.0",                   // mark price
          "idxPx": "29995.25",                   // index price
          "fundingRate": "0.0001",               // funding rate
          "nextFundingTime": "1597027200000",    // next funding time (ms)
          "openInterest": "100000.5"             // open interest (contracts)
        }
    """

    inst_id: Symbol = field(name="instId")

    def to_ticker_msg(
        self,
        venue: Venue,
        instrument_collection: InstrumentCollection,
        is_snapshot: bool,
        origin_id: MessageId | None = None,
        recv_time_ns: int | None = None,
    ) -> TickerMsg:
        instrument = instrument_collection.get(self.inst_id)
        if not instrument:
            raise KeyError(f"Instrument not found for {venue}:{self.inst_id}")

        exch_time_ns = int(self.ts) * 1_000_000
        recv_time_ns = time_ns() if recv_time_ns is None else recv_time_ns
        price_chg_pct = (
            (float(self.last) - float(self.open_24h)) / float(self.open_24h) * 100.0
            if float(self.open_24h) > 0
            else 0.0
        )
        msg_id = MessageId(recv_time_ns=recv_time_ns)
        origin_id = msg_id if origin_id is None else origin_id

        return TickerMsg(
            id=msg_id,
            origin_id=origin_id,
            moments=Moments(exch_time_ns=exch_time_ns, recv_time_ns=recv_time_ns),
            instrument=instrument,
            is_snapshot=is_snapshot,
            mark_price=float(self.mark_px),
            index_price=float(self.idx_px),
            funding_rate=float(self.funding_rate),
            funding_period_min=480,
            next_funding_time_ms=float(self.next_funding_time),
            open_interest=float(self.open_interest),
            avg_volume_24h=float(self.vol_24h),
            price_chg_24h_pct=price_chg_pct,
        )


class OkxTradeMsg(Struct, frozen=True):
    """Individual trade execution on the market.

    Represents a single trade for a symbol including price, quantity, side, and
    execution time. Contains unique trade ID for deduplication.

    Docs: https://www.okx.com/docs-v5/en/#websocket-api-public-channel-trades-channel

    Example payload::

        {
          "instId": "BTC-USDT-SWAP",             // instrument ID
          "tradeId": "123456789",                // trade ID
          "px": "30000.5",                       // price
          "sz": "1.0",                           // size
          "side": "buy",                         // side (buy/sell)
          "ts": "1597026383085"                  // trade time (ms)
        }
    """

    inst_id: Symbol = field(name="instId")
    trade_id: str = field(name="tradeId")
    px: str
    sz: str
    side: str
    ts: str

    def to_trade(self) -> Trade:
        return Trade(
            time_ms=int(self.ts),
            price=float(self.px),
            is_buy=self.side == "buy",
            size=float(self.sz),
        )


class OkxOrderbookLevel(Struct, frozen=True, array_like=True):
    """A single level in the orderbook.

    OKX orderbook format: ["price", "size", "deprecated", "num_orders"]
    Index 2 is deprecated (liquidations), we ignore it.
    """

    price: str
    size: str
    deprecated: str
    num_orders: str


class OkxOrderbookMsg(Struct, frozen=True):
    """Orderbook depth snapshot or update.

    Provides bid and ask levels for a symbol. Can represent either a full snapshot
    or a differential update. Each level contains price, size, and number of orders.

    Docs: https://www.okx.com/docs-v5/en/#websocket-api-public-channel-order-book-channel

    Example payload::

        {
          "asks": [
            ["30001.0", "1.5", "0", "3"],        // [price, size, deprecated, num_orders]
            ["30002.0", "3.0", "0", "5"]
          ],
          "bids": [
            ["30000.0", "1.0", "0", "2"],
            ["29999.5", "2.0", "0", "4"]
          ],
          "ts": "1597026383085",                 // timestamp (ms)
          "checksum": 123456789                  // checksum for validation
        }
    """

    asks: list[OkxOrderbookLevel]
    bids: list[OkxOrderbookLevel]
    ts: str
    checksum: int

    def to_orderbook_msg(
        self,
        venue: Venue,
        instrument_collection: InstrumentCollection,
        inst_id: str,
        is_bbo: bool,
        is_snapshot: bool = False,
        origin_id: MessageId | None = None,
        recv_time_ns: int | None = None,
    ) -> OrderbookMsg:
        instrument = instrument_collection.get(Symbol(inst_id))
        if not instrument:
            raise KeyError(f"Instrument not found for {venue}:{inst_id}")

        exch_time_ns = int(self.ts) * 1_000_000
        recv_time_ns = time_ns() if recv_time_ns is None else recv_time_ns
        msg_id = MessageId(recv_time_ns=recv_time_ns)
        origin_id = msg_id if origin_id is None else origin_id
        return OrderbookMsg(
            id=msg_id,
            origin_id=origin_id,
            moments=Moments(
                exch_time_ns=exch_time_ns,
                recv_time_ns=recv_time_ns,
            ),
            instrument=instrument,
            is_snapshot=is_snapshot,
            bids=tuple(
                OrderbookLevel(
                    float(level.price), float(level.size), int(level.num_orders)
                )
                for level in self.bids
            ),
            asks=tuple(
                OrderbookLevel(
                    float(level.price), float(level.size), int(level.num_orders)
                )
                for level in self.asks
            ),
            is_bbo=is_bbo,
        )


class OkxTickerPublicMsg(Struct, frozen=True):
    """Wrapper for OKX ticker websocket messages.

    Docs: https://www.okx.com/docs-v5/en/#websocket-api-public-channel-tickers-channel
    """

    arg: dict[str, str]
    data: list[OkxTickerMsg]
    action: str | None = None


class OkxOrderbookPublicMsg(Struct, frozen=True):
    """Wrapper for OKX orderbook websocket messages.

    Docs: https://www.okx.com/docs-v5/en/#websocket-api-public-channel-order-book-channel
    """

    arg: dict[str, str]
    data: list[OkxOrderbookMsg]
    action: str | None = None


class OkxTradesPublicMsg(Struct, frozen=True):
    """Wrapper for OKX trades websocket messages.

    Docs: https://www.okx.com/docs-v5/en/#websocket-api-public-channel-trades-channel
    """

    arg: dict[str, str]
    data: list[OkxTradeMsg]
    action: str | None = None


class OkxPositionMsg(Struct, frozen=True):
    """Position update for a symbol (private stream).

    Provides position data including size, entry price, mark price, leverage,
    PnL, liquidation price, and margin info.

    Docs: https://www.okx.com/docs-v5/en/#websocket-api-private-channel-positions-channel

    Example payload::

        {
          "instId": "BTC-USDT-SWAP",             // instrument ID
          "instType": "SWAP",                    // instrument type
          "mgnMode": "cross",                    // margin mode (cross/isolated)
          "posId": "123456789",                  // position ID
          "posSide": "net",                      // position side (net/long/short)
          "pos": "1.0",                          // position size (positive=long, negative=short)
          "availPos": "1.0",                     // available position
          "avgPx": "30000.0",                    // average entry price
          "upl": "500.0",                        // unrealized PnL
          "uplRatio": "0.0167",                  // unrealized PnL ratio
          "lever": "10",                         // leverage
          "liqPx": "25000.0",                    // liquidation price
          "markPx": "30500.0",                   // mark price
          "imr": "3000.0",                       // initial margin requirement
          "margin": "3000.0",                    // margin
          "mgnRatio": "0.1",                     // margin ratio
          "mmr": "1500.0",                       // maintenance margin requirement
          "notionalUsd": "30500.0",              // notional value in USD
          "cTime": "1597026383085",              // creation time (ms)
          "uTime": "1597026483085"               // update time (ms)
        }
    """

    inst_id: Symbol = field(name="instId")
    inst_type: str = field(name="instType")
    mgn_mode: str = field(name="mgnMode")
    pos_id: str = field(name="posId")
    pos_side: str = field(name="posSide")
    pos: str
    avail_pos: str = field(name="availPos")
    avg_px: str = field(name="avgPx")
    upl: str
    upl_ratio: str = field(name="uplRatio")
    lever: str
    liq_px: str = field(name="liqPx")
    mark_px: str = field(name="markPx")
    imr: str
    margin: str
    mgn_ratio: str = field(name="mgnRatio")
    mmr: str
    notional_usd: str = field(name="notionalUsd")
    c_time: str = field(name="cTime")
    u_time: str = field(name="uTime")

    def to_position_msg(
        self,
        venue: Venue,
        instrument_collection: InstrumentCollection,
        is_snapshot: bool,
        origin_id: MessageId | None = None,
        recv_time_ns: int | None = None,
    ) -> PositionMsg:
        instrument = instrument_collection.get(self.inst_id)
        if not instrument:
            raise KeyError(f"Instrument not found for {venue}:{self.inst_id}")

        pos_size = float(self.pos)
        exch_time_ns = int(self.u_time) * 1_000_000
        recv_time_ns = time_ns() if recv_time_ns is None else recv_time_ns
        msg_id = MessageId(recv_time_ns=recv_time_ns)
        origin_id = msg_id if origin_id is None else origin_id

        return PositionMsg(
            id=msg_id,
            origin_id=origin_id,
            moments=Moments(
                exch_time_ns=exch_time_ns,
                recv_time_ns=recv_time_ns,
            ),
            instrument=instrument,
            is_snapshot=is_snapshot,
            price=float(self.avg_px),
            is_long=pos_size > 0,
            size=abs(pos_size),
        )


class OkxOrderMsg(Struct, frozen=True):
    """Order update (private stream).

    Provides order data including status, filled quantity, price, and timestamps.

    Docs: https://www.okx.com/docs-v5/en/#websocket-api-private-channel-orders-channel

    Example payload::

        {
          "instId": "BTC-USDT-SWAP",             // instrument ID
          "instType": "SWAP",                    // instrument type
          "ordId": "123456789",                  // order ID
          "clOrdId": "client123",                // client order ID
          "px": "30000.0",                       // price
          "sz": "1.0",                           // size
          "ordType": "limit",                    // order type (limit/market/post_only)
          "side": "buy",                         // side (buy/sell)
          "posSide": "net",                      // position side
          "tdMode": "cross",                     // trade mode
          "tgtCcy": "",                          // target currency
          "fillSz": "0.5",                       // filled size
          "fillPx": "30000.0",                   // filled price
          "avgPx": "30000.0",                    // average filled price
          "state": "live",                       // order state (live/filled/canceled)
          "lever": "10",                         // leverage
          "tpTriggerPx": "",                     // TP trigger price
          "tpOrdPx": "",                         // TP order price
          "slTriggerPx": "",                     // SL trigger price
          "slOrdPx": "",                         // SL order price
          "feeCcy": "USDT",                      // fee currency
          "fee": "-0.0015",                      // fee amount (negative = paid)
          "rebateCcy": "",                       // rebate currency
          "rebate": "0",                         // rebate amount
          "tgtCcy": "",                          // target currency
          "category": "normal",                  // category
          "reduceOnly": false,                   // reduce only flag
          "quickMgnType": "",                    // quick margin type
          "algoId": "",                          // algo order ID
          "cTime": "1597026383085",              // creation time (ms)
          "uTime": "1597026483085"               // update time (ms)
        }
    """

    inst_id: Symbol = field(name="instId")
    inst_type: str = field(name="instType")
    ord_id: str = field(name="ordId")
    cl_ord_id: str = field(name="clOrdId")
    px: str
    sz: str
    ord_type: str = field(name="ordType")
    side: str
    pos_side: str = field(name="posSide")
    td_mode: str = field(name="tdMode")
    fill_sz: str = field(name="fillSz")
    fill_px: str = field(name="fillPx")
    avg_px: str = field(name="avgPx")
    state: str
    lever: str
    fee_ccy: Asset = field(name="feeCcy")
    fee: str
    rebate_ccy: str = field(name="rebateCcy")
    rebate: str
    category: str
    reduce_only: str = field(name="reduceOnly")
    c_time: str = field(name="cTime")
    u_time: str = field(name="uTime")

    def to_order(self) -> Order:
        filled_size = float(self.fill_sz)
        total_size = float(self.sz)
        is_cancelled = self.state in ("canceled", "cancelled")

        # Map OKX order type to TIF
        tif = OrderTimeInForce.GTC
        if self.ord_type == "post_only":
            tif = OrderTimeInForce.PO
        elif self.ord_type == "ioc":
            tif = OrderTimeInForce.IOC
        elif self.ord_type == "fok":
            tif = OrderTimeInForce.FOK

        return Order(
            create_time_ms=float(self.c_time),
            order_id=OrderId(str(self.ord_id)),
            price=float(self.px) if self.px else 0.0,
            is_buy=self.side == "buy",
            size=total_size,
            size_remaining=total_size - filled_size,
            tif=tif,
            is_cancelled=is_cancelled,
            is_reduce_only=self.reduce_only == "true",
            client_order_id=ClientOrderId(str(self.cl_ord_id))
            if self.cl_ord_id
            else None,
        )


class OkxExecutionMsg(Struct, frozen=True):
    """Execution (fill) update from order channel.

    OKX sends execution data through the order channel. We extract fill information
    from order updates when fillSz > 0.

    Docs: https://www.okx.com/docs-v5/en/#websocket-api-private-channel-orders-channel

    Example: Same as OkxOrderMsg, but we extract execution info.
    """

    inst_id: Symbol = field(name="instId")
    ord_id: str = field(name="ordId")
    cl_ord_id: str = field(name="clOrdId")
    px: str
    sz: str
    side: str
    fill_sz: str = field(name="fillSz")
    fill_px: str = field(name="fillPx")
    avg_px: str = field(name="avgPx")
    fee: str
    fee_ccy: Asset = field(name="feeCcy")
    u_time: str = field(name="uTime")
    ord_type: str = field(name="ordType")

    def to_execution(self) -> Execution | None:
        fill_size = float(self.fill_sz)
        if fill_size <= 0:
            return None

        # Determine if maker or taker
        is_maker = self.ord_type == "post_only"

        return Execution(
            exec_time_ms=float(self.u_time),
            order_id=OrderId(str(self.ord_id)),
            price=float(self.avg_px) if self.avg_px else float(self.fill_px),
            is_buy=self.side == "buy",
            size=fill_size,
            is_maker=is_maker,
            fee_paid=abs(float(self.fee)) if self.fee else 0.0,
            client_order_id=ClientOrderId(str(self.cl_ord_id))
            if self.cl_ord_id
            else None,
        )


class OkxAccountMsg(Struct, frozen=True):
    """Account balance update (private stream).

    Provides account-level information including total equity, available balance,
    margin requirements, and unrealized PnL.

    Docs: https://www.okx.com/docs-v5/en/#websocket-api-private-channel-account-channel

    Example payload::

        {
          "uTime": "1597026383085",              // update time (ms)
          "totalEq": "100000.0",                 // total equity in USD
          "isoEq": "0",                          // isolated margin equity
          "adjEq": "99500.0",                    // adjusted equity
          "ordFroz": "500.0",                    // margin frozen for orders
          "imr": "3000.0",                       // initial margin requirement
          "mmr": "1500.0",                       // maintenance margin requirement
          "mgnRatio": "33.333",                  // margin ratio
          "notionalUsd": "30000.0",              // notional value in USD
          "upl": "500.0",                        // unrealized PnL
          "details": [...]                       // currency details (optional)
        }
    """

    u_time: str = field(name="uTime")
    total_eq: str = field(name="totalEq")
    iso_eq: str = field(name="isoEq")
    adj_eq: str = field(name="adjEq")
    ord_froz: str = field(name="ordFroz")
    imr: str
    mmr: str
    mgn_ratio: str = field(name="mgnRatio")
    notional_usd: str = field(name="notionalUsd")
    upl: str

    def to_account_msg(
        self,
        venue: Venue,
        instrument: Instrument,
        is_snapshot: bool,
        origin_id: MessageId | None = None,
        recv_time_ns: int | None = None,
    ) -> AccountMsg:
        exch_time_ns = int(self.u_time) * 1_000_000
        recv_time_ns = time_ns() if recv_time_ns is None else recv_time_ns
        msg_id = MessageId(recv_time_ns=recv_time_ns)
        origin_id = msg_id if origin_id is None else origin_id

        return AccountMsg(
            id=msg_id,
            origin_id=origin_id,
            moments=Moments(
                exch_time_ns=exch_time_ns,
                recv_time_ns=recv_time_ns,
            ),
            instrument=instrument,
            is_snapshot=is_snapshot,
            balances={
                instrument: Balance(currency=Asset("USD"), amount=float(self.total_eq))
            },
            initial_margin=float(self.imr),
            maintenance_margin=float(self.mmr),
            unrealized_pnl=float(self.upl),
        )


class OkxOrdersPrivateMsg(Struct, frozen=True):
    """Wrapper for OKX orders websocket messages.

    Docs: https://www.okx.com/docs-v5/en/#websocket-api-private-channel-orders-channel
    """

    arg: dict[str, str]
    data: list[OkxOrderMsg]


class OkxPositionsPrivateMsg(Struct, frozen=True):
    """Wrapper for OKX positions websocket messages.

    Docs: https://www.okx.com/docs-v5/en/#websocket-api-private-channel-positions-channel
    """

    arg: dict[str, str]
    data: list[OkxPositionMsg]


class OkxAccountPrivateMsg(Struct, frozen=True):
    """Wrapper for OKX account websocket messages.

    Docs: https://www.okx.com/docs-v5/en/#websocket-api-private-channel-account-channel
    """

    arg: dict[str, str]
    data: list[OkxAccountMsg]
