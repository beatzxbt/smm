"""Shared message builders and wire-assertion helpers for SMM trader tests.

Usage: construct normalized stream messages with valid envelope metadata and
inspect scripted-exchange wire frames.
Components: message factories, frame query helpers, and the canonical Bybit
BTCUSDT instrument.
"""

from __future__ import annotations

from framework.base.common import (
    Asset,
    ClientOrderId,
    Instrument,
    InstrumentType,
    OrderId,
    Symbol,
    Venue,
)
from framework.base.schema import MessageId, Moments
from framework.base.stream.models import (
    DataStreamEvent,
    DataStreamEventMsg,
    Execution,
    ExecutionMsg,
    Order,
    OrderMsg,
    OrderTimeInForce,
    OrderbookLevel,
    OrderbookMsg,
    PositionMsg,
    Trade,
    TradeMsg,
)
from mm_toolbox.rounding import Rounder, RounderConfig

NOW_NS = 1_700_000_000_000_000_000


def fresh_recv_ns() -> int:
    """Return the current wall-clock receive timestamp in nanoseconds.

    Used by trader scenarios where staleness checks compare against the
    real clock.

    Returns:
        int: Current time in nanoseconds.
    """
    from mm_toolbox.time import time_ns

    return time_ns()


def make_instrument(tick_size: float = 0.01, lot_size: float = 0.001) -> Instrument:
    """Build a Bybit BTCUSDT perpetual instrument.

    Args:
        tick_size: Tick size used for price rounding.
        lot_size: Lot size used for quantity rounding.

    Returns:
        Instrument: BTCUSDT perpetual instrument on Bybit.
    """
    return Instrument(
        venue=Venue.BYBIT,
        base=Asset("BTC"),
        quote=Asset("USDT"),
        symbol=Symbol("BTCUSDT"),
        code=0,
        instrument_type=InstrumentType.PERPETUAL,
        tick_size=tick_size,
        lot_size=lot_size,
    )


def make_moments(recv_ns: int = NOW_NS) -> Moments:
    """Build timing metadata anchored at a receive timestamp.

    Args:
        recv_ns: Local receive timestamp in nanoseconds.

    Returns:
        Moments: Exchange and receive timestamps at the anchor.
    """
    return Moments(recv_time_ns=recv_ns, exch_time_ns=recv_ns)


def make_msg(cls: type, instrument: Instrument, recv_ns: int = NOW_NS, **fields):
    """Build a normalized stream message with valid envelope metadata.

    Args:
        cls: StreamSchema message class to construct.
        instrument: Instrument the message applies to.
        recv_ns: Local receive timestamp in nanoseconds.
        **fields: Remaining message payload fields.

    Returns:
        StreamSchema: Constructed message.
    """
    return cls(
        moments=make_moments(recv_ns),
        instrument=instrument,
        id=MessageId(recv_time_ns=recv_ns),
        origin_id=MessageId(recv_time_ns=recv_ns),
        is_snapshot=True,
        **fields,
    )


def make_orderbook(
    instrument: Instrument,
    mid: float = 30_000.0,
    spread: float = 1.0,
    depth: int = 5,
    recv_ns: int = NOW_NS,
) -> OrderbookMsg:
    """Build a symmetric orderbook message around a mid price.

    Args:
        instrument: Instrument the book applies to.
        mid: Mid price of the book.
        spread: Price distance from mid to the first level.
        depth: Number of levels per side.
        recv_ns: Local receive timestamp in nanoseconds.

    Returns:
        OrderbookMsg: Symmetric book with best bid/ask adjacent to the mid.
    """
    bids = tuple(
        OrderbookLevel(price=mid - spread * i, size=10.0) for i in range(depth, 0, -1)
    )
    asks = tuple(
        OrderbookLevel(price=mid + spread * i, size=10.0) for i in range(1, depth + 1)
    )
    return make_msg(
        OrderbookMsg,
        instrument,
        recv_ns,
        bids=bids,
        asks=asks,
        is_bbo=False,
    )


def make_empty_book(instrument: Instrument, recv_ns: int = NOW_NS) -> OrderbookMsg:
    """Build an orderbook message with no levels.

    Args:
        instrument: Instrument the book applies to.
        recv_ns: Local receive timestamp in nanoseconds.

    Returns:
        OrderbookMsg: Empty book message.
    """
    return make_msg(
        OrderbookMsg,
        instrument,
        recv_ns,
        bids=(),
        asks=(),
        is_bbo=False,
    )


def make_position(
    instrument: Instrument,
    size: float,
    is_long: bool = True,
    price: float = 30_000.0,
    recv_ns: int = NOW_NS,
) -> PositionMsg:
    """Build a position message.

    Args:
        instrument: Instrument the position applies to.
        size: Position size in base units.
        is_long: True for a long position.
        price: Entry or mark price.
        recv_ns: Local receive timestamp in nanoseconds.

    Returns:
        PositionMsg: Position message with the given state.
    """
    return make_msg(
        PositionMsg,
        instrument,
        recv_ns,
        price=price,
        is_long=is_long,
        size=size,
    )


def make_trade_msg(
    instrument: Instrument,
    price: float = 30_000.0,
    size: float = 0.1,
    is_buy: bool = True,
    time_ms: int = 1_700_000_000_000,
    recv_ns: int = NOW_NS,
) -> TradeMsg:
    """Build a trade message containing a single trade.

    Args:
        instrument: Instrument the trade applies to.
        price: Trade price.
        size: Trade size.
        is_buy: Whether the aggressing side was a buyer.
        time_ms: Exchange trade timestamp in milliseconds.
        recv_ns: Local receive timestamp in nanoseconds.

    Returns:
        TradeMsg: Trade message with a single trade.
    """
    return make_msg(
        TradeMsg,
        instrument,
        recv_ns,
        trades=(
            Trade(
                time_ms=time_ms,
                price=price,
                is_buy=is_buy,
                size=size,
            ),
        ),
    )


def make_execution_msg(
    instrument: Instrument,
    exec_time_ms: float,
    price: float = 30_000.0,
    size: float = 0.01,
    is_buy: bool = True,
    order_id: str = "order-1",
    recv_ns: int = NOW_NS,
) -> ExecutionMsg:
    """Build an execution message containing a single fill.

    Args:
        instrument: Instrument the fill applies to.
        exec_time_ms: Exchange execution timestamp in milliseconds.
        price: Execution price.
        size: Executed quantity.
        is_buy: Whether the fill was on the buy side.
        order_id: Exchange-assigned order identifier.
        recv_ns: Local receive timestamp in nanoseconds.

    Returns:
        ExecutionMsg: Execution message with a single fill.
    """
    return make_msg(
        ExecutionMsg,
        instrument,
        recv_ns,
        executions=(
            Execution(
                exec_time_ms=exec_time_ms,
                order_id=OrderId(order_id),
                price=price,
                is_buy=is_buy,
                size=size,
                is_maker=False,
            ),
        ),
    )


def make_order_msg(
    instrument: Instrument,
    cloid: str,
    price: float = 30_000.0,
    size: float = 1.0,
    size_remaining: float = 1.0,
    is_buy: bool = True,
    is_cancelled: bool = False,
    recv_ns: int = NOW_NS,
) -> OrderMsg:
    """Build an order message containing a single order state.

    Args:
        instrument: Instrument the order applies to.
        cloid: Client order id of the order.
        price: Order price.
        size: Original order size.
        size_remaining: Remaining unfilled size.
        is_buy: Whether the order is a buy order.
        is_cancelled: Whether the order was cancelled.
        recv_ns: Local receive timestamp in nanoseconds.

    Returns:
        OrderMsg: Order message with a single order state.
    """
    return make_msg(
        OrderMsg,
        instrument,
        recv_ns,
        orders=(
            Order(
                create_time_ms=recv_ns / 1_000_000,
                order_id=OrderId(f"order-{cloid}"),
                price=price,
                is_buy=is_buy,
                size=size,
                size_remaining=size_remaining,
                tif=OrderTimeInForce.GTC,
                is_cancelled=is_cancelled,
                is_reduce_only=False,
                client_order_id=ClientOrderId(cloid),
            ),
        ),
    )


def make_heartbeat(
    time_next_check_ms: int, venue: Venue = Venue.BYBIT, recv_ns: int = NOW_NS
) -> DataStreamEventMsg:
    """Build a heartbeat lifecycle event.

    Args:
        time_next_check_ms: Next expected heartbeat timestamp in milliseconds.
        venue: Venue the stream applies to.
        recv_ns: Local receive timestamp in nanoseconds.

    Returns:
        DataStreamEventMsg: Heartbeat event with the given check time.
    """
    return DataStreamEventMsg(
        time_ms=recv_ns // 1_000_000,
        venue=venue,
        event=DataStreamEvent.HEARTBEAT,
        changes={},
        state={},
        time_next_check_ms=time_next_check_ms,
    )


def op_frames(server, op: str) -> list[dict]:
    """Return decoded wire frames matching an operation.

    Args:
        server: Scripted exchange server recording client frames.
        op: Operation name to match (e.g. ``order.create``).

    Returns:
        list[dict]: Frames whose ``op`` field matches, in send order.
    """
    return [
        frame
        for frame in server.ws_frames
        if isinstance(frame, dict) and frame.get("op") == op
    ]


def op_args(server, op: str, cloid: str | None = None) -> list[list[dict]]:
    """Return the args payload of wire frames matching an operation.

    Args:
        server: Scripted exchange server recording client frames.
        op: Operation name to match.
        cloid: Optional client order id to filter frames on.

    Returns:
        list[list[dict]]: Args lists of matching frames, in send order.
    """
    matching = op_frames(server, op)
    if cloid is None:
        return [frame["args"] for frame in matching]
    return [
        frame["args"]
        for frame in matching
        if any(
            isinstance(arg, dict) and arg.get("orderLinkId") == cloid
            for arg in frame["args"]
        )
    ]


def op_count(server, op: str) -> int:
    """Count wire frames matching an operation.

    Args:
        server: Scripted exchange server recording client frames.
        op: Operation name to match.

    Returns:
        int: Number of matching frames.
    """
    return len(op_frames(server, op))


def expected_plain_prices(
    mid: float,
    levels: int,
    base_spread_bps: float,
    *,
    multiplier: float = 1.0,
    tick_size: float = 0.01,
    lot_size: float = 0.001,
) -> list[tuple[float, float]]:
    """Mirror plain pricing math to derive expected (bid, ask) prices.

    Args:
        mid: Mid price used by the engine.
        levels: Number of quote levels per side.
        base_spread_bps: Base spread in basis points.
        multiplier: Inventory spread ladder multiplier.
        tick_size: Tick size used by the rounder.
        lot_size: Lot size used by the rounder.

    Returns:
        list[tuple[float, float]]: Expected (bid, ask) price pairs per level.
    """
    rounder = Rounder(RounderConfig.default(tick_size=tick_size, lot_size=lot_size))
    spread_bps = base_spread_bps * multiplier
    prices = []
    for level in range(levels):
        level_spread = (level + 1) * (spread_bps / 10_000.0)
        prices.append(
            (
                rounder.bid(mid * (1.0 - level_spread)),
                rounder.ask(mid * (1.0 + level_spread)),
            )
        )
    return prices


def expected_stinky_prices(
    mid: float,
    levels: int,
    min_spread_bps: float,
    max_spread_bps: float,
    *,
    tick_size: float = 0.01,
    lot_size: float = 0.001,
) -> list[tuple[float, float]]:
    """Mirror stinky pricing math to derive expected (bid, ask) prices.

    Args:
        mid: Mid price used by the engine.
        levels: Number of quote levels per side.
        min_spread_bps: Minimum spread in basis points.
        max_spread_bps: Maximum spread in basis points.
        tick_size: Tick size used by the rounder.
        lot_size: Lot size used by the rounder.

    Returns:
        list[tuple[float, float]]: Expected (bid, ask) price pairs per level.
    """
    rounder = Rounder(RounderConfig.default(tick_size=tick_size, lot_size=lot_size))
    spread_range = max_spread_bps - min_spread_bps
    prices = []
    for level in range(levels):
        if levels == 1:
            level_spread_bps = min_spread_bps
        else:
            level_spread_bps = min_spread_bps + (spread_range * (level / (levels - 1)))
        level_spread = level_spread_bps / 10_000.0
        prices.append(
            (
                rounder.bid(mid * (1.0 - level_spread)),
                rounder.ask(mid * (1.0 + level_spread)),
            )
        )
    return prices
