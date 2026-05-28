"""
Binance stream handlers for market and private websocket connections.

Usage: instantiated by BinanceMarketStreamManager and BinancePrivateStreamManager.
Components: typed decoders, subscription payloads, and REST polling for ticker stats.
"""

from __future__ import annotations

import asyncio
from itertools import count
from typing import ClassVar

import msgspec

from framework.base.common import (
    Asset,
    ClientOrderId,
    Instrument,
    InstrumentCollection,
    OrderId,
    Venue,
)
from framework.base.schema import MessageId, Moments
from framework.base.stream.connection import WebSocketConnection
from framework.base.stream.handlers import (
    BBOStreamHandler,
    OrderbookStreamHandler,
    PrivateStreamHandler,
    TickerStreamHandler,
    TradesStreamHandler,
)
from framework.base.stream.models import (
    AccountMsg,
    Balance,
    Execution,
    ExecutionMsg,
    Order,
    OrderMsg,
    OrderTimeInForce,
    OrderbookLevel,
    OrderbookMsg,
    PositionMsg,
    StreamType,
    TickerMsg,
    Trade,
    TradeMsg,
)
from framework.base.stream.shared import StreamSharedContext
from framework.base.tools import EnumMap, SimpleCache
from framework.base.trading.models import TickerResponse, is_success
from framework.binance.stream.models import (
    AccountUpdateStreamUpdate,
    BookTickerStreamUpdate,
    DiffBookDepthStreamUpdate,
    MarkPriceStreamUpdate,
    OrderUpdateStreamUpdate,
    TradeStreamUpdate,
)
from framework.binance.trading.exchange import BinanceExchange
from mm_toolbox.logging.standard import Logger
from mm_toolbox.ringbuffer import GenericRingBuffer

_BINANCE_ORDERBOOK_SEQ_ID_CACHE_KEY = "binance.orderbook_seq_id_cache"
_BINANCE_TRADES_SEQ_ID_CACHE_KEY = "binance.trades_seq_id_cache"
BINANCE_TIF_MAP = EnumMap(
    enum_class=OrderTimeInForce,
    mapping={
        OrderTimeInForce.GTC: "GTC",
        OrderTimeInForce.PO: "GTX",
        OrderTimeInForce.IOC: "IOC",
        OrderTimeInForce.FOK: "FOK",
    },
)


def _handle_ack(raw_msg: bytes, logger: Logger, stream_suffix: str) -> bool:
    """Handle Binance subscription ACK/control messages.

    Args:
        raw_msg: Raw websocket payload bytes.
        logger: Logger for diagnostics.
        stream_suffix: Stream suffix used by the handler.

    Returns:
        bool: True if the message is an ACK/control response.
    """
    try:
        payload = msgspec.json.decode(raw_msg)
    except Exception:
        return False
    if not isinstance(payload, dict):
        return False
    if "code" in payload and "msg" in payload:
        req_id = payload.get("id")
        logger.error(
            "_handle_ack ACK error; "
            f"stream={stream_suffix} id={req_id} "
            f"code={payload.get('code')} msg={payload.get('msg')}"
        )
        return True
    if "result" in payload and "id" in payload:
        return True
    return False


class BinanceTickerHandler(TickerStreamHandler):
    """Binance ticker handler with REST polling for auxiliary stats."""

    def __init__(
        self,
        connection: WebSocketConnection,
        instrument_collection: InstrumentCollection,
        venue: Venue,
        logger: Logger,
        consumer_buffer: GenericRingBuffer,
        exchange: BinanceExchange,
        shared_context: StreamSharedContext | None = None,
    ) -> None:
        """Initialize the Binance ticker handler.

        Args:
            connection: WebSocket connection for ticker stream.
            instrument_collection: Shared instrument collection.
            venue: Venue for the handler.
            logger: Logger for diagnostics.
            consumer_buffer: Ring buffer to broadcast messages to.
            exchange: Binance exchange for REST polling.
            shared_context: Optional manager-scoped shared context.
        """
        TickerStreamHandler.__init__(
            self,
            connection=connection,
            instrument_collection=instrument_collection,
            venue=venue,
            logger=logger,
            consumer_buffer=consumer_buffer,
            shared_context=shared_context,
        )
        self._stream_suffix = "markPrice@1s"
        self._req_id_counter = count(start=1)
        self._decoder = msgspec.json.Decoder(MarkPriceStreamUpdate)
        self._exchange = exchange
        self._poll_tasks: list[asyncio.Task[None]] = []
        self._instrument_to_latest_ticker_map: dict[Instrument, TickerResponse] = {}

    def build_authentication_payload(self) -> bytes:
        """No authentication needed for public market streams.

        Returns:
            bytes: Empty bytes (no auth required).
        """
        return b""

    def build_subscribe_payload(
        self,
        instruments: list[Instrument],
        stream_types: set[StreamType] | None = None,
    ) -> bytes:
        """Build the Binance ticker subscribe payload.

        Args:
            instruments: Instruments to subscribe to.
            stream_types: Ignored for market streams.

        Returns:
            bytes: Serialized payload bytes.
        """
        params = [
            f"{inst.symbol.lower()}@{self._stream_suffix}" for inst in instruments
        ]
        return msgspec.json.encode(
            {"method": "SUBSCRIBE", "params": params, "id": next(self._req_id_counter)}
        )

    def build_unsubscribe_payload(
        self,
        instruments: list[Instrument],
        stream_types: set[StreamType] | None = None,
    ) -> bytes:
        """Build the Binance ticker unsubscribe payload.

        Args:
            instruments: Instruments to unsubscribe from.
            stream_types: Ignored for market streams.

        Returns:
            bytes: Serialized payload bytes.
        """
        params = [
            f"{inst.symbol.lower()}@{self._stream_suffix}" for inst in instruments
        ]
        return msgspec.json.encode(
            {
                "method": "UNSUBSCRIBE",
                "params": params,
                "id": next(self._req_id_counter),
            }
        )

    async def start(self) -> None:
        """Start the handler, connection, and polling tasks."""
        if self._is_running:
            return
        self._is_running = True
        await self._connection.connect()
        await self.authenticate()
        self._message_task = asyncio.create_task(self._message_loop())
        self._poll_tasks = [asyncio.create_task(self._poll_ticker())]

    async def stop(self) -> None:
        """Stop the handler, connection, and polling tasks."""
        if not self._is_running:
            return
        self._is_running = False
        for task in self._poll_tasks:
            task.cancel()
        if self._poll_tasks:
            await asyncio.gather(*self._poll_tasks, return_exceptions=True)
        self._poll_tasks = []
        if self._message_task is not None:
            self._message_task.cancel()
            await asyncio.gather(self._message_task, return_exceptions=True)
            self._message_task = None
        await self._connection.disconnect()
        self._subscribed_instruments.clear()
        self._subscribed_stream_types.clear()

    async def decode_and_broadcast(
        self,
        recv_time_ns: int,
        raw_msg: bytes,
    ) -> None:
        """Decode ticker messages and broadcast updates.

        Args:
            recv_time_ns: Receive timestamp captured when the websocket payload arrived.
            raw_msg: Raw websocket payload bytes.
        """
        try:
            data = self._decoder.decode(raw_msg)
            instrument = self.instrument_collection.get(data.symbol)
            if not instrument:
                raise KeyError(f"Instrument not found for {self.venue}:{data.symbol}")
            ticker_data = self._instrument_to_latest_ticker_map.get(instrument)
            origin_id = MessageId(recv_time_ns=recv_time_ns)
            ticker_msg = TickerMsg(
                id=MessageId(recv_time_ns=recv_time_ns),
                origin_id=origin_id,
                moments=Moments(
                    exch_time_ns=data.event_time * 1_000_000,
                    recv_time_ns=recv_time_ns,
                ),
                instrument=instrument,
                is_snapshot=False,
                mark_price=float(data.mark_price),
                index_price=float(data.index_price),
                funding_rate=float(data.funding_rate),
                funding_period_min=480,
                next_funding_time_ms=data.next_funding_time,
                open_interest=(
                    ticker_data.open_interest if ticker_data is not None else 0.0
                ),
                avg_volume_24h=(
                    ticker_data.avg_volume_24h if ticker_data is not None else 0.0
                ),
                price_chg_24h_pct=(
                    ticker_data.price_chg_24h if ticker_data is not None else 0.0
                ),
            )
            self.broadcast(ticker_msg)
        except Exception:
            if _handle_ack(
                raw_msg=raw_msg, logger=self._logger, stream_suffix=self._stream_suffix
            ):
                return
            raise

    async def _poll_ticker(self) -> None:
        """Poll 24h ticker stats at a fixed interval."""
        while self._is_running:
            if instruments := list(self._subscribed_instruments):
                try:
                    response = await self._exchange.get_ticker(instruments)
                    if not is_success(response):
                        return

                    for ticker in response.data:
                        self._instrument_to_latest_ticker_map[ticker.instrument] = (
                            ticker
                        )
                except Exception as exc:
                    self._logger.warning(
                        f"{self.__class__.__name__}._poll_ticker error; {exc}"
                    )

            # Approx REST usage: 3 reqs/symbol when <=10 instruments, 2 reqs/symbol above.
            poll_interval_s = (
                1.0
                if (instrument_count := len(self._subscribed_instruments)) <= 10
                else 2.0
                if instrument_count <= 20
                else 5.0
                if instrument_count <= 100
                else 10.0
            )
            await asyncio.sleep(poll_interval_s)


class BinanceBBOHandler(BBOStreamHandler):
    """Binance top-of-book stream handler."""

    shared_slots: ClassVar[dict[str, type[SimpleCache]]] = {
        _BINANCE_ORDERBOOK_SEQ_ID_CACHE_KEY: SimpleCache
    }

    def __init__(
        self,
        connection: WebSocketConnection,
        instrument_collection: InstrumentCollection,
        venue: Venue,
        logger: Logger,
        consumer_buffer: GenericRingBuffer,
        shared_context: StreamSharedContext | None = None,
    ) -> None:
        """Initialize the Binance BBO handler.

        Args:
            connection: WebSocket connection for BBO stream.
            instrument_collection: Shared instrument collection.
            venue: Venue for the handler.
            logger: Logger for diagnostics.
            consumer_buffer: Ring buffer to broadcast messages to.
            shared_context: Optional manager-scoped shared context.
        """
        BBOStreamHandler.__init__(
            self,
            connection=connection,
            instrument_collection=instrument_collection,
            venue=venue,
            logger=logger,
            consumer_buffer=consumer_buffer,
            shared_context=shared_context,
        )
        self._stream_suffix = "bookTicker"
        self._req_id_counter = count(start=1)
        self._decoder = msgspec.json.Decoder(BookTickerStreamUpdate)
        self._orderbook_seq_id_cache: SimpleCache = self.get_shared(
            _BINANCE_ORDERBOOK_SEQ_ID_CACHE_KEY, SimpleCache
        )

    def build_authentication_payload(self) -> bytes:
        """No authentication needed for public market streams.

        Returns:
            bytes: Empty bytes (no auth required).
        """
        return b""

    def build_subscribe_payload(
        self,
        instruments: list[Instrument],
        stream_types: set[StreamType] | None = None,
    ) -> bytes:
        """Build the Binance BBO subscribe payload.

        Args:
            instruments: Instruments to subscribe to.
            stream_types: Ignored for market streams.

        Returns:
            bytes: Serialized payload bytes.
        """
        params = [
            f"{inst.symbol.lower()}@{self._stream_suffix}" for inst in instruments
        ]
        return msgspec.json.encode(
            {"method": "SUBSCRIBE", "params": params, "id": next(self._req_id_counter)}
        )

    def build_unsubscribe_payload(
        self,
        instruments: list[Instrument],
        stream_types: set[StreamType] | None = None,
    ) -> bytes:
        """Build the Binance BBO unsubscribe payload.

        Args:
            instruments: Instruments to unsubscribe from.
            stream_types: Ignored for market streams.

        Returns:
            bytes: Serialized payload bytes.
        """
        params = [
            f"{inst.symbol.lower()}@{self._stream_suffix}" for inst in instruments
        ]
        return msgspec.json.encode(
            {
                "method": "UNSUBSCRIBE",
                "params": params,
                "id": next(self._req_id_counter),
            }
        )

    async def decode_and_broadcast(
        self,
        recv_time_ns: int,
        raw_msg: bytes,
    ) -> None:
        """Decode BBO messages and broadcast updates.

        Args:
            recv_time_ns: Receive timestamp captured when the websocket payload arrived.
            raw_msg: Raw websocket payload bytes.
        """
        try:
            data = self._decoder.decode(raw_msg)
            if not self._orderbook_seq_id_cache.is_higher(data.symbol, data.update_id):
                return
            instrument = self.instrument_collection.get(data.symbol)
            if not instrument:
                raise KeyError(f"Instrument not found for {self.venue}:{data.symbol}")
            origin_id = MessageId(recv_time_ns=recv_time_ns)
            orderbook_msg = OrderbookMsg(
                id=MessageId(recv_time_ns=recv_time_ns),
                origin_id=origin_id,
                moments=Moments(
                    exch_time_ns=data.event_time * 1_000_000,
                    recv_time_ns=recv_time_ns,
                ),
                instrument=instrument,
                is_snapshot=False,
                bids=(
                    OrderbookLevel(
                        float(data.best_bid_price), float(data.best_bid_qty)
                    ),
                ),
                asks=(
                    OrderbookLevel(
                        float(data.best_ask_price), float(data.best_ask_qty)
                    ),
                ),
                is_bbo=True,
            )
            self.broadcast(orderbook_msg)
        except Exception:
            if _handle_ack(
                raw_msg=raw_msg, logger=self._logger, stream_suffix=self._stream_suffix
            ):
                return
            raise


class BinanceOrderbookHandler(OrderbookStreamHandler):
    """Binance full orderbook stream handler."""

    shared_slots: ClassVar[dict[str, type[SimpleCache]]] = {
        _BINANCE_ORDERBOOK_SEQ_ID_CACHE_KEY: SimpleCache
    }

    def __init__(
        self,
        connection: WebSocketConnection,
        instrument_collection: InstrumentCollection,
        venue: Venue,
        logger: Logger,
        consumer_buffer: GenericRingBuffer,
        shared_context: StreamSharedContext | None = None,
    ) -> None:
        """Initialize the Binance orderbook handler.

        Args:
            connection: WebSocket connection for orderbook stream.
            instrument_collection: Shared instrument collection.
            venue: Venue for the handler.
            logger: Logger for diagnostics.
            consumer_buffer: Ring buffer to broadcast messages to.
            shared_context: Optional manager-scoped shared context.
        """
        OrderbookStreamHandler.__init__(
            self,
            connection=connection,
            instrument_collection=instrument_collection,
            venue=venue,
            logger=logger,
            consumer_buffer=consumer_buffer,
            shared_context=shared_context,
        )
        self._stream_suffix = "depth@100ms"
        self._req_id_counter = count(start=1)
        self._decoder = msgspec.json.Decoder(DiffBookDepthStreamUpdate)
        self._orderbook_seq_id_cache: SimpleCache = self.get_shared(
            _BINANCE_ORDERBOOK_SEQ_ID_CACHE_KEY, SimpleCache
        )

    def build_authentication_payload(self) -> bytes:
        """No authentication needed for public market streams.

        Returns:
            bytes: Empty bytes (no auth required).
        """
        return b""

    def build_subscribe_payload(
        self,
        instruments: list[Instrument],
        stream_types: set[StreamType] | None = None,
    ) -> bytes:
        """Build the Binance orderbook subscribe payload.

        Args:
            instruments: Instruments to subscribe to.
            stream_types: Ignored for market streams.

        Returns:
            bytes: Serialized payload bytes.
        """
        params = [
            f"{inst.symbol.lower()}@{self._stream_suffix}" for inst in instruments
        ]
        return msgspec.json.encode(
            {"method": "SUBSCRIBE", "params": params, "id": next(self._req_id_counter)}
        )

    def build_unsubscribe_payload(
        self,
        instruments: list[Instrument],
        stream_types: set[StreamType] | None = None,
    ) -> bytes:
        """Build the Binance orderbook unsubscribe payload.

        Args:
            instruments: Instruments to unsubscribe from.
            stream_types: Ignored for market streams.

        Returns:
            bytes: Serialized payload bytes.
        """
        params = [
            f"{inst.symbol.lower()}@{self._stream_suffix}" for inst in instruments
        ]
        return msgspec.json.encode(
            {
                "method": "UNSUBSCRIBE",
                "params": params,
                "id": next(self._req_id_counter),
            }
        )

    async def decode_and_broadcast(
        self,
        recv_time_ns: int,
        raw_msg: bytes,
    ) -> None:
        """Decode orderbook messages and broadcast updates.

        Args:
            recv_time_ns: Receive timestamp captured when the websocket payload arrived.
            raw_msg: Raw websocket payload bytes.
        """
        try:
            data = self._decoder.decode(raw_msg)
            if not self._orderbook_seq_id_cache.is_higher(
                data.symbol, data.final_update_id
            ):
                return
            instrument = self.instrument_collection.get(data.symbol)
            if not instrument:
                raise KeyError(f"Instrument not found for {self.venue}:{data.symbol}")
            origin_id = MessageId(recv_time_ns=recv_time_ns)
            orderbook_msg = OrderbookMsg(
                id=MessageId(recv_time_ns=recv_time_ns),
                origin_id=origin_id,
                moments=Moments(
                    exch_time_ns=data.event_time * 1_000_000,
                    recv_time_ns=recv_time_ns,
                ),
                instrument=instrument,
                is_snapshot=False,
                bids=tuple(
                    OrderbookLevel(float(price), float(size))
                    for price, size in data.bids
                ),
                asks=tuple(
                    OrderbookLevel(float(price), float(size))
                    for price, size in data.asks
                ),
                is_bbo=False,
            )
            self.broadcast(orderbook_msg)
        except Exception:
            if _handle_ack(
                raw_msg=raw_msg, logger=self._logger, stream_suffix=self._stream_suffix
            ):
                return
            raise


class BinanceTradesHandler(TradesStreamHandler):
    """Binance trades stream handler with trade id deduplication."""

    shared_slots: ClassVar[dict[str, type[SimpleCache]]] = {
        _BINANCE_TRADES_SEQ_ID_CACHE_KEY: SimpleCache
    }

    def __init__(
        self,
        connection: WebSocketConnection,
        instrument_collection: InstrumentCollection,
        venue: Venue,
        logger: Logger,
        consumer_buffer: GenericRingBuffer,
        shared_context: StreamSharedContext | None = None,
    ) -> None:
        """Initialize the Binance trades handler.

        Args:
            connection: WebSocket connection for trades stream.
            instrument_collection: Shared instrument collection.
            venue: Venue for the handler.
            logger: Logger for diagnostics.
            consumer_buffer: Ring buffer to broadcast messages to.
            shared_context: Optional manager-scoped shared context.
        """
        TradesStreamHandler.__init__(
            self,
            connection=connection,
            instrument_collection=instrument_collection,
            venue=venue,
            logger=logger,
            consumer_buffer=consumer_buffer,
            shared_context=shared_context,
        )
        self._stream_suffix = "trade"
        self._req_id_counter = count(start=1)
        self._decoder = msgspec.json.Decoder(TradeStreamUpdate)
        self._trades_seq_id_cache: SimpleCache = self.get_shared(
            _BINANCE_TRADES_SEQ_ID_CACHE_KEY, SimpleCache
        )

    def build_authentication_payload(self) -> bytes:
        """No authentication needed for public market streams.

        Returns:
            bytes: Empty bytes (no auth required).
        """
        return b""

    def build_subscribe_payload(
        self,
        instruments: list[Instrument],
        stream_types: set[StreamType] | None = None,
    ) -> bytes:
        """Build the Binance trades subscribe payload.

        Args:
            instruments: Instruments to subscribe to.
            stream_types: Ignored for market streams.

        Returns:
            bytes: Serialized payload bytes.
        """
        params = [
            f"{inst.symbol.lower()}@{self._stream_suffix}" for inst in instruments
        ]
        return msgspec.json.encode(
            {"method": "SUBSCRIBE", "params": params, "id": next(self._req_id_counter)}
        )

    def build_unsubscribe_payload(
        self,
        instruments: list[Instrument],
        stream_types: set[StreamType] | None = None,
    ) -> bytes:
        """Build the Binance trades unsubscribe payload.

        Args:
            instruments: Instruments to unsubscribe from.
            stream_types: Ignored for market streams.

        Returns:
            bytes: Serialized payload bytes.
        """
        params = [
            f"{inst.symbol.lower()}@{self._stream_suffix}" for inst in instruments
        ]
        return msgspec.json.encode(
            {
                "method": "UNSUBSCRIBE",
                "params": params,
                "id": next(self._req_id_counter),
            }
        )

    async def decode_and_broadcast(
        self,
        recv_time_ns: int,
        raw_msg: bytes,
    ) -> None:
        """Decode trade messages and broadcast updates.

        Args:
            recv_time_ns: Receive timestamp captured when the websocket payload arrived.
            raw_msg: Raw websocket payload bytes.
        """
        try:
            data = self._decoder.decode(raw_msg)
            match trade_type := data.trade_type:
                case "INSURANCE_FUND":
                    raw_text = raw_msg.decode("utf-8", errors="replace")
                    self._logger.debug(
                        f"{self.__class__.__name__}.decode_and_broadcast "
                        "dropped insurance fund trade; "
                        f"symbol={data.symbol} trade_id={data.trade_id} "
                        f"trade_type={trade_type} price={data.price} "
                        f"qty={data.quantity} raw={raw_text}"
                    )
                    return
                case "NA":
                    raw_text = raw_msg.decode("utf-8", errors="replace")
                    self._logger.debug(
                        f"{self.__class__.__name__}.decode_and_broadcast "
                        "dropped empty trade update; "
                        f"symbol={data.symbol} trade_id={data.trade_id} "
                        f"trade_type={trade_type} price={data.price} "
                        f"qty={data.quantity} raw={raw_text}"
                    )
                    return
                case _:
                    if not self._trades_seq_id_cache.is_higher(
                        data.symbol, data.trade_id
                    ):
                        return
                    instrument = self.instrument_collection.get(data.symbol)
                    if not instrument:
                        raise KeyError(
                            f"Instrument not found for {self.venue}:{data.symbol}"
                        )
                    origin_id = MessageId(recv_time_ns=recv_time_ns)
                    trade_msg = TradeMsg(
                        id=MessageId(recv_time_ns=recv_time_ns),
                        origin_id=origin_id,
                        moments=Moments(
                            exch_time_ns=data.event_time * 1_000_000,
                            recv_time_ns=recv_time_ns,
                        ),
                        instrument=instrument,
                        is_snapshot=False,
                        trades=(
                            Trade(
                                time_ms=data.transaction_time,
                                price=float(data.price),
                                is_buy=not data.is_buyer_maker,
                                size=float(data.quantity),
                            ),
                        ),
                    )
                    self.broadcast(trade_msg)
        except Exception:
            if _handle_ack(
                raw_msg=raw_msg, logger=self._logger, stream_suffix=self._stream_suffix
            ):
                return
            raise


class BinancePrivateHandler(PrivateStreamHandler):
    """Unified Binance private stream handler for all 4 private stream types.

    Binance private streams use listen-key authentication rather than signature-based
    auth. The listen key is embedded in the connection URL, so no authentication
    payload is needed.
    """

    def __init__(
        self,
        venue: Venue,
        logger: Logger,
        connection: WebSocketConnection,
        instrument_collection: InstrumentCollection,
        consumer_buffer: GenericRingBuffer,
        exchange: BinanceExchange,
        listen_key: str,
        shared_context: StreamSharedContext | None = None,
    ) -> None:
        """Initialize the Binance private handler.

        Args:
            venue: Venue this handler streams from.
            logger: Logger for diagnostics.
            connection: WebSocket connection for private streams.
            instrument_collection: Shared instrument collection.
            consumer_buffer: Ring buffer to broadcast messages to.
            exchange: Binance exchange client for listen-key refresh.
            listen_key: Listen key for private stream connection.
            shared_context: Optional manager-scoped shared context.
        """
        super().__init__(
            venue=venue,
            logger=logger,
            connection=connection,
            instrument_collection=instrument_collection,
            consumer_buffer=consumer_buffer,
            shared_context=shared_context,
        )
        self._stream_suffix = "userData"
        self._exchange = exchange
        self._listen_key = listen_key
        self._decoder = msgspec.json.Decoder(
            OrderUpdateStreamUpdate | AccountUpdateStreamUpdate
        )
        self._listen_key_refresh_task: asyncio.Task[None] | None = None

    async def start(self) -> None:
        """Start the handler, connection, and listen-key refresh loop."""
        if self._is_running:
            return
        self._is_running = True
        await self._connection.connect()
        await self.authenticate()
        self._message_task = asyncio.create_task(self._message_loop())
        self._listen_key_refresh_task = asyncio.create_task(
            self._refresh_listen_key_loop()
        )

    async def stop(self) -> None:
        """Stop the handler, connection, and listen-key refresh loop."""
        if not self._is_running:
            return
        self._is_running = False
        if self._listen_key_refresh_task is not None:
            self._listen_key_refresh_task.cancel()
            await asyncio.gather(self._listen_key_refresh_task, return_exceptions=True)
            self._listen_key_refresh_task = None
        if self._message_task is not None:
            self._message_task.cancel()
            await asyncio.gather(self._message_task, return_exceptions=True)
            self._message_task = None
        await self._connection.disconnect()
        self._subscribed_instruments.clear()
        self._subscribed_stream_types.clear()

    def build_authentication_payload(self) -> bytes:
        """No authentication payload needed (listen-key is in URL).

        Returns:
            bytes: Empty bytes (no auth payload required).
        """
        return b""

    def build_subscribe_payload(
        self,
        instruments: list[Instrument],
        stream_types: set[StreamType] | None = None,
    ) -> bytes:
        """Binance private streams do not require subscribe payloads.

        Args:
            instruments: Ignored for Binance private streams.
            stream_types: Ignored for Binance private streams.

        Returns:
            bytes: Empty bytes (no subscribe payload required).
        """
        return b""

    def build_unsubscribe_payload(
        self,
        instruments: list[Instrument],
        stream_types: set[StreamType] | None = None,
    ) -> bytes:
        """Binance private streams do not require unsubscribe payloads.

        Args:
            instruments: Ignored for Binance private streams.
            stream_types: Ignored for Binance private streams.

        Returns:
            bytes: Empty bytes (no unsubscribe payload required).
        """
        return b""

    async def decode_and_broadcast(
        self,
        recv_time_ns: int,
        raw_msg: bytes,
    ) -> None:
        """Decode and broadcast Binance private messages.

        Args:
            recv_time_ns: Receive timestamp captured when the websocket payload arrived.
            raw_msg: Raw websocket payload bytes.
        """
        try:
            payload = self._decoder.decode(raw_msg)
        except Exception:
            if _handle_ack(
                raw_msg=raw_msg, logger=self._logger, stream_suffix=self._stream_suffix
            ):
                return
            raise

        if isinstance(payload, OrderUpdateStreamUpdate):
            origin_id = MessageId(recv_time_ns=recv_time_ns)
            order_data = payload.order
            instrument = self._instrument_collection.get(order_data.symbol)
            if not instrument:
                raise KeyError(
                    f"Instrument not found for {self._venue}:{order_data.symbol}"
                )

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
                order_id=OrderId(str(order_data.order_id)),
                price=float(order_data.price),
                is_buy=order_data.side == "BUY",
                size=size,
                size_remaining=max(0.0, size - filled),
                tif=tif,
                is_cancelled=is_cancelled,
                is_reduce_only=order_data.reduce_only,
                client_order_id=ClientOrderId(str(order_data.client_order_id)),
            )
            self.broadcast(
                OrderMsg(
                    id=MessageId(recv_time_ns=recv_time_ns),
                    origin_id=origin_id,
                    moments=Moments(
                        exch_time_ns=payload.event_time * 1_000_000,
                        recv_time_ns=recv_time_ns,
                    ),
                    instrument=instrument,
                    is_snapshot=False,
                    orders=(order,),
                )
            )

            if order_data.status == "TRADE":
                last_executed_qty = float(order_data.last_exec_qty)
                if last_executed_qty == 0.0:
                    raise ValueError("Execution update has zero executed quantity")
                execution = Execution(
                    exec_time_ms=float(order_data.trade_time),
                    order_id=OrderId(str(order_data.order_id)),
                    price=float(order_data.last_exec_price),
                    is_buy=order_data.side == "BUY",
                    size=last_executed_qty,
                    is_maker=order_data.is_maker,
                    fee_paid=float(order_data.commission),
                    client_order_id=ClientOrderId(str(order_data.client_order_id)),
                )
                self.broadcast(
                    ExecutionMsg(
                        id=MessageId(recv_time_ns=recv_time_ns),
                        origin_id=origin_id,
                        moments=Moments(
                            exch_time_ns=payload.event_time * 1_000_000,
                            recv_time_ns=recv_time_ns,
                        ),
                        instrument=instrument,
                        is_snapshot=False,
                        executions=(execution,),
                    )
                )
        elif isinstance(payload, AccountUpdateStreamUpdate):
            origin_id = MessageId(recv_time_ns=recv_time_ns)
            for position in payload.account_data.positions:
                instrument = self._instrument_collection.get(position.symbol)
                if not instrument:
                    raise KeyError(
                        f"Instrument not found for {self._venue}:{position.symbol}"
                    )
                position_amt = float(position.position_amount)
                if position_amt == 0.0:
                    continue
                self.broadcast(
                    PositionMsg(
                        id=MessageId(recv_time_ns=recv_time_ns),
                        origin_id=origin_id,
                        moments=Moments(
                            exch_time_ns=payload.event_time * 1_000_000,
                            recv_time_ns=recv_time_ns,
                        ),
                        instrument=instrument,
                        is_snapshot=False,
                        price=float(position.entry_price),
                        is_long=position_amt > 0.0,
                        size=abs(position_amt),
                    )
                )

            wallet_balance = 0.0
            for balance in payload.account_data.balances:
                if balance.asset == "USDT":
                    wallet_balance = float(balance.wallet_balance)
                    break
            account_instrument = Instrument.empty_with(venue=self._venue)
            self.broadcast(
                AccountMsg(
                    id=MessageId(recv_time_ns=recv_time_ns),
                    origin_id=origin_id,
                    moments=Moments(
                        exch_time_ns=payload.event_time * 1_000_000,
                        recv_time_ns=recv_time_ns,
                    ),
                    instrument=account_instrument,
                    is_snapshot=False,
                    balances={
                        account_instrument: Balance(
                            currency=Asset("USDT"), amount=wallet_balance
                        )
                    },
                    initial_margin=float(payload.account_data.maintenance_margin),
                    maintenance_margin=float(
                        payload.account_data.maintenance_margin_level
                    ),
                    unrealized_pnl=float(payload.account_data.unrealized_pnl_usd),
                )
            )

    async def _refresh_listen_key_loop(self, interval_s: int = 50 * 60) -> None:
        """Refresh the listen key at a fixed interval.

        Args:
            interval_s: Interval in seconds between refresh attempts.
        """
        while True:
            if not self._is_running:
                await asyncio.sleep(1)
                continue
            await asyncio.sleep(interval_s)
            try:
                extend_listen_key = getattr(self._exchange, "extend_listen_key", None)
                if not callable(extend_listen_key):
                    self._logger.warning(
                        f"{self.__class__.__name__}._refresh_listen_key_loop "
                        "listen key refresh not supported by exchange client."
                    )
                    continue
                response = await extend_listen_key(self._listen_key)
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                self._logger.warning(
                    f"{self.__class__.__name__}._refresh_listen_key_loop error; {exc}"
                )
                continue
            if not is_success(response):
                self._logger.warning(
                    f"{self.__class__.__name__}._refresh_listen_key_loop "
                    f"listen key refresh failed; {response.err_msg}"
                )
                continue
            self._logger.info(
                f"{self.__class__.__name__}._refresh_listen_key_loop "
                "listen key refreshed."
            )
