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


class BookTickerStreamUpdate(Struct, tag=True):
    """https://developers.binance.com/docs/derivatives/usds-margined-futures/websocket-market-streams/Individual-Symbol-Book-Ticker-Streams."""

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


class DiffBookDepthStreamUpdate(Struct, tag=True):
    """https://developers.binance.com/docs/derivatives/usds-margined-futures/websocket-market-streams/Diff-Book-Depth-Streams."""

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


class TradeStreamUpdate(Struct):
    """https://developers.binance.com/docs/derivatives/usds-margined-futures/websocket-market-streams/Individual-Symbol-Trade-Streams."""

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


class OpenInterestInfo(Struct):
    open_interest: float


class TickerStats24h(Struct):
    price_chg_24h_pct: float
    avg_volume_24h: float


class TickerStats24hStreamUpdate(Struct):
    """https://developers.binance.com/docs/derivatives/usds-margined-futures/websocket-market-streams/24hr-Ticker-Price-Change-Statistics-Streams."""

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


class MarkPriceStreamUpdate(Struct):
    """https://developers.binance.com/docs/derivatives/usds-margined-futures/websocket-market-streams/Mark-Price-Stream."""

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


class OrderUpdateStreamUpdate(Struct):
    """https://developers.binance.com/docs/derivatives/usds-margined-futures/websocket-market-streams/Order-Update."""

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


class AccountUpdateStreamUpdate(Struct):
    """https://developers.binance.com/docs/derivatives/usds-margined-futures/websocket-market-streams/Account-Update."""

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


class PositionUpdateStreamUpdate(Struct):
    """https://developers.binance.com/docs/derivatives/usds-margined-futures/websocket-market-streams/Position-Update."""

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


class ExecutionReportStreamUpdate(Struct):
    """https://developers.binance.com/docs/derivatives/usds-margined-futures/websocket-market-streams/Execution-Report."""

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
