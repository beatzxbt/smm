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


class BybitTickerMsg(Struct, rename="camel"):
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
        symbol_override: str | None = None,
        exch_time_ns: int | None = None,
    ) -> TickerMsg:
        symbol = symbol_override or self.symbol
        instrument = instrument_collection.get(venue, symbol)
        if not instrument:
            raise KeyError(f"Instrument not found for {venue}:{symbol}")

        exchange_time_ns = exch_time_ns or time_ns()
        return TickerMsg(
            moments=Moments(
                exch_time_ns=exchange_time_ns,
                recv_time_ns=time_ns(),
            ),
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


class BybitTradeMsg(Struct):
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


class BybitOrderbookLevel(Struct):
    price: float
    size: float


class BybitOrderbookMsg(Struct, rename="camel"):
    symbol: str = field(name="s")
    bids: list[BybitOrderbookLevel] = field(name="b")
    asks: list[BybitOrderbookLevel] = field(name="a")
    update_id: int = field(name="u")
    seq: int = field(name="seq")

    def to_orderbook_msg(
        self,
        venue: Venue,
        instrument_collection: InstrumentCollection,
        is_bbo: bool,
        symbol_override: str | None = None,
        is_snapshot: bool = False,
        exch_time_ns: int | None = None,
    ) -> OrderbookMsg:
        symbol = symbol_override or self.symbol
        instrument = instrument_collection.get(venue, symbol)
        if not instrument:
            raise KeyError(f"Instrument not found for {venue}:{symbol}")

        exchange_time_ns = exch_time_ns or time_ns()
        return OrderbookMsg(
            moments=Moments(
                exch_time_ns=exchange_time_ns,
                recv_time_ns=time_ns(),
            ),
            venue=venue,
            instrument=instrument,
            bids=[
                OrderbookLevel(float(level.price), float(level.size))
                for level in self.bids
            ],
            asks=[
                OrderbookLevel(float(level.price), float(level.size))
                for level in self.asks
            ],
            is_bbo=is_bbo,
            is_snapshot=is_snapshot,
        )


class BybitPublicMsg[T](Struct):
    topic: str
    type: str
    data: T
    ts: int | None = None


class BybitTradePublicMsg(Struct, rename="camel"):
    """Wrapper for Bybit public trade messages."""

    topic: str
    type: str  # "snapshot"
    ts: int  # System timestamp
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


class BybitPrivateMsg[T](Struct, rename="camel"):
    topic: str
    type: str
    ts: int
    data: list[T]


class BybitPositionMsg(Struct, rename="camel"):
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


class BybitOrderMsg(Struct, rename="camel"):
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


class BybitExecutionMsg(Struct, rename="camel"):
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


class BybitWalletMsg(Struct, rename="camel"):
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
