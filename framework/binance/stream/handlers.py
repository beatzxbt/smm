"""
Binance stream handlers for market and private websocket connections.

Usage: instantiated by BinanceMarketStreamManager and BinancePrivateStreamManager.
Components: typed decoders, subscription payloads, and REST polling for ticker stats.
"""

from __future__ import annotations

import asyncio
from abc import ABC

import msgspec

from framework.base.common import Instrument, InstrumentCollection, Venue
from framework.base.stream.connection import WebSocketConnection
from framework.base.stream.handlers import (
    BBOStreamHandler,
    OrderbookStreamHandler,
    PrivateStreamHandler,
    TickerStreamHandler,
    TradesStreamHandler,
)
from framework.base.stream.models import Msg, StreamType
from framework.base.tools import SimpleCache
from framework.binance.stream.models import (
    AccountUpdateStreamUpdate,
    BookTickerStreamUpdate,
    DiffBookDepthStreamUpdate,
    MarkPriceStreamUpdate,
    OpenInterestInfo,
    OrderUpdateStreamUpdate,
    TickerStats24h,
    TradeStreamUpdate,
)
from framework.binance.trading.exchange import BinanceExchange
from mm_toolbox.logging.standard import Logger


class _BinanceStreamHandler(ABC):
    """Shared Binance stream behavior."""

    def __init__(self, stream_suffix: str) -> None:
        """Initialize the handler mixin.

        Args:
            stream_suffix: Stream suffix for Binance subscriptions.
        """
        self._stream_suffix = stream_suffix
        self._req_id_counter = 0

    def _next_req_id(self) -> int:
        """Return the next request id.

        Returns:
            int: Request identifier.
        """
        self._req_id_counter += 1
        return self._req_id_counter

    def _handle_ack(self, raw_msg: bytes, logger: Logger) -> bool:
        """Handle Binance subscription ACK/control messages.

        Args:
            raw_msg: Raw websocket payload bytes.
            logger: Logger for diagnostics.

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
                f"{self.__class__.__name__}._handle_ack "
                f"ACK error; stream={self._stream_suffix} id={req_id} "
                f"code={payload.get('code')} msg={payload.get('msg')}"
            )
            return True
        if "result" in payload and "id" in payload:
            return True
        return False


class BinanceTickerHandler(TickerStreamHandler, _BinanceStreamHandler):
    """Binance ticker handler with REST polling for auxiliary stats."""

    def __init__(
        self,
        connection: WebSocketConnection,
        instrument_collection: InstrumentCollection,
        venue: Venue,
        logger: Logger,
        consumer_queues: list[asyncio.Queue[Msg]],
        exchange: BinanceExchange,
    ) -> None:
        """Initialize the Binance ticker handler.

        Args:
            connection: WebSocket connection for ticker stream.
            instrument_collection: Shared instrument collection.
            venue: Venue for the handler.
            logger: Logger for diagnostics.
            consumer_queues: Queues to broadcast messages to.
            exchange: Binance exchange for REST polling.
        """
        TickerStreamHandler.__init__(
            self,
            connection=connection,
            instrument_collection=instrument_collection,
            venue=venue,
            logger=logger,
            consumer_queues=consumer_queues,
        )
        _BinanceStreamHandler.__init__(self, stream_suffix="markPrice@1s")
        self._decoder = msgspec.json.Decoder(MarkPriceStreamUpdate)
        self._exchange = exchange
        self._poll_interval_s = 5.0
        self._poll_tasks: list[asyncio.Task[None]] = []
        self._instrument_to_open_interest_map: dict[Instrument, OpenInterestInfo] = {}
        self._instrument_to_ticker_stats_24h_map: dict[Instrument, TickerStats24h] = {}

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
            {"method": "SUBSCRIBE", "params": params, "id": self._next_req_id()}
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
            {"method": "UNSUBSCRIBE", "params": params, "id": self._next_req_id()}
        )

    async def start(self) -> None:
        """Start the handler, connection, and polling tasks."""
        if self._is_running:
            return
        self._is_running = True
        await self._connection.connect()
        await self.authenticate()
        self._message_task = asyncio.create_task(self._message_loop())
        self._poll_tasks = [asyncio.create_task(self._poll_ticker_stats())]

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

    async def decode_and_broadcast(self, raw_msg: bytes) -> None:
        """Decode ticker messages and broadcast updates.

        Args:
            raw_msg: Raw websocket payload bytes.
        """
        try:
            data = self._decoder.decode(raw_msg)
            ticker_msg = data.to_ticker_msg(
                venue=self.venue,
                instrument_collection=self.instrument_collection,
                instrument_to_open_interest_map=self._instrument_to_open_interest_map,
                instrument_to_ticker_stats_24h_map=self._instrument_to_ticker_stats_24h_map,
            )
            self.broadcast(ticker_msg)
        except Exception:
            if self._handle_ack(raw_msg, self._logger):
                return
            raise

    async def _poll_ticker_stats(self) -> None:
        """Poll 24h ticker stats at a fixed interval."""
        while self._is_running:
            if instruments := list(self._subscribed_instruments):
                try:
                    response = await self._exchange.get_ticker(instruments)
                    if response.is_successful is True:
                        for ticker in response.data:
                            self._instrument_to_ticker_stats_24h_map[
                                ticker.instrument
                            ] = TickerStats24h(
                                price_chg_24h_pct=ticker.price_chg_24h or 0.0,
                                avg_volume_24h=ticker.avg_volume_24h or 0.0,
                            )
                except Exception as exc:
                    self._logger.warning(
                        f"{self.__class__.__name__}._poll_ticker_stats error; {exc}"
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


class BinanceBBOHandler(BBOStreamHandler, _BinanceStreamHandler):
    """Binance top-of-book stream handler."""

    def __init__(
        self,
        connection: WebSocketConnection,
        instrument_collection: InstrumentCollection,
        venue: Venue,
        logger: Logger,
        consumer_queues: list[asyncio.Queue[Msg]],
    ) -> None:
        """Initialize the Binance BBO handler.

        Args:
            connection: WebSocket connection for BBO stream.
            instrument_collection: Shared instrument collection.
            venue: Venue for the handler.
            logger: Logger for diagnostics.
            consumer_queues: Queues to broadcast messages to.
        """
        BBOStreamHandler.__init__(
            self,
            connection=connection,
            instrument_collection=instrument_collection,
            venue=venue,
            logger=logger,
            consumer_queues=consumer_queues,
        )
        _BinanceStreamHandler.__init__(self, stream_suffix="bookTicker")
        self._decoder = msgspec.json.Decoder(BookTickerStreamUpdate)

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
            {"method": "SUBSCRIBE", "params": params, "id": self._next_req_id()}
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
            {"method": "UNSUBSCRIBE", "params": params, "id": self._next_req_id()}
        )

    async def decode_and_broadcast(self, raw_msg: bytes) -> None:
        """Decode BBO messages and broadcast updates.

        Args:
            raw_msg: Raw websocket payload bytes.
        """
        try:
            data = self._decoder.decode(raw_msg)
            orderbook_msg = data.to_orderbook_msg(
                venue=self.venue,
                instrument_collection=self.instrument_collection,
            )
            self.broadcast(orderbook_msg)
        except Exception:
            if self._handle_ack(raw_msg, self._logger):
                return
            raise


class BinanceOrderbookHandler(OrderbookStreamHandler, _BinanceStreamHandler):
    """Binance full orderbook stream handler."""

    def __init__(
        self,
        connection: WebSocketConnection,
        instrument_collection: InstrumentCollection,
        venue: Venue,
        logger: Logger,
        consumer_queues: list[asyncio.Queue[Msg]],
    ) -> None:
        """Initialize the Binance orderbook handler.

        Args:
            connection: WebSocket connection for orderbook stream.
            instrument_collection: Shared instrument collection.
            venue: Venue for the handler.
            logger: Logger for diagnostics.
            consumer_queues: Queues to broadcast messages to.
        """
        OrderbookStreamHandler.__init__(
            self,
            connection=connection,
            instrument_collection=instrument_collection,
            venue=venue,
            logger=logger,
            consumer_queues=consumer_queues,
        )
        _BinanceStreamHandler.__init__(self, stream_suffix="depth@100ms")
        self._decoder = msgspec.json.Decoder(DiffBookDepthStreamUpdate)

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
            {"method": "SUBSCRIBE", "params": params, "id": self._next_req_id()}
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
            {"method": "UNSUBSCRIBE", "params": params, "id": self._next_req_id()}
        )

    async def decode_and_broadcast(self, raw_msg: bytes) -> None:
        """Decode orderbook messages and broadcast updates.

        Args:
            raw_msg: Raw websocket payload bytes.
        """
        try:
            data = self._decoder.decode(raw_msg)
            orderbook_msg = data.to_orderbook_msg(
                venue=self.venue,
                instrument_collection=self.instrument_collection,
            )
            self.broadcast(orderbook_msg)
        except Exception:
            if self._handle_ack(raw_msg, self._logger):
                return
            raise


class BinanceTradesHandler(TradesStreamHandler, _BinanceStreamHandler):
    """Binance trades stream handler with trade id deduplication."""

    def __init__(
        self,
        connection: WebSocketConnection,
        instrument_collection: InstrumentCollection,
        venue: Venue,
        logger: Logger,
        consumer_queues: list[asyncio.Queue[Msg]],
    ) -> None:
        """Initialize the Binance trades handler.

        Args:
            connection: WebSocket connection for trades stream.
            instrument_collection: Shared instrument collection.
            venue: Venue for the handler.
            logger: Logger for diagnostics.
            consumer_queues: Queues to broadcast messages to.
        """
        TradesStreamHandler.__init__(
            self,
            connection=connection,
            instrument_collection=instrument_collection,
            venue=venue,
            logger=logger,
            consumer_queues=consumer_queues,
        )
        _BinanceStreamHandler.__init__(self, stream_suffix="trade")
        self._decoder = msgspec.json.Decoder(TradeStreamUpdate)
        self._symbol_to_seq_cache: SimpleCache = SimpleCache()

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
            {"method": "SUBSCRIBE", "params": params, "id": self._next_req_id()}
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
            {"method": "UNSUBSCRIBE", "params": params, "id": self._next_req_id()}
        )

    async def decode_and_broadcast(self, raw_msg: bytes) -> None:
        """Decode trade messages and broadcast updates.

        Args:
            raw_msg: Raw websocket payload bytes.
        """
        try:
            data = self._decoder.decode(raw_msg)
            trade_type = data.trade_type.upper()
            if trade_type == "INSURANCE_FUND":
                raw_text = raw_msg.decode("utf-8", errors="replace")
                self._logger.trace(
                    f"{self.__class__.__name__}.decode_and_broadcast "
                    "dropped insurance fund trade; "
                    f"symbol={data.symbol} trade_id={data.trade_id} "
                    f"trade_type={data.trade_type} price={data.price} "
                    f"qty={data.quantity} raw={raw_text}"
                )
                return
            try:
                price = float(data.price)
                quantity = float(data.quantity)
            except (TypeError, ValueError):
                raw_text = raw_msg.decode("utf-8", errors="replace")
                self._logger.error(
                    f"{self.__class__.__name__}.decode_and_broadcast "
                    "invalid trade price; "
                    f"symbol={data.symbol} trade_id={data.trade_id} "
                    f"price={data.price} qty={data.quantity} raw={raw_text}"
                )
                return
            if price <= 0.0:
                if price == 0.0 and quantity == 0.0 and data.trade_type.upper() == "NA":
                    raw_text = raw_msg.decode("utf-8", errors="replace")
                    self._logger.debug(
                        f"{self.__class__.__name__}.decode_and_broadcast "
                        "dropped empty trade update; "
                        f"symbol={data.symbol} trade_id={data.trade_id} "
                        f"price={data.price} qty={data.quantity} raw={raw_text}"
                    )
                    return
                raw_text = raw_msg.decode("utf-8", errors="replace")
                self._logger.error(
                    f"{self.__class__.__name__}.decode_and_broadcast "
                    "invalid trade price; "
                    f"symbol={data.symbol} trade_id={data.trade_id} "
                    f"price={data.price} qty={data.quantity} raw={raw_text}"
                )
                return
            if not self._symbol_to_seq_cache.is_higher(data.symbol, data.trade_id):
                return
            trade_msg = data.to_trade_msg(
                venue=self.venue,
                instrument_collection=self.instrument_collection,
            )
            self.broadcast(trade_msg)
        except Exception:
            if self._handle_ack(raw_msg, self._logger):
                return
            raise


class BinancePrivateHandler(PrivateStreamHandler, _BinanceStreamHandler):
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
        consumer_queues: list[asyncio.Queue[Msg]],
        exchange: BinanceExchange,
        listen_key: str,
    ) -> None:
        """Initialize the Binance private handler.

        Args:
            venue: Venue this handler streams from.
            logger: Logger for diagnostics.
            connection: WebSocket connection for private streams.
            instrument_collection: Shared instrument collection.
            consumer_queues: Queues to broadcast messages to.
            exchange: Binance exchange client for listen-key refresh.
            listen_key: Listen key for private stream connection.
        """
        super().__init__(
            venue=venue,
            logger=logger,
            connection=connection,
            instrument_collection=instrument_collection,
            consumer_queues=consumer_queues,
        )
        _BinanceStreamHandler.__init__(self, stream_suffix="userData")
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

    async def decode_and_broadcast(self, raw_msg: bytes) -> None:
        """Decode and broadcast Binance private messages.

        Args:
            raw_msg: Raw websocket payload bytes.
        """
        try:
            payload = self._decoder.decode(raw_msg)
        except Exception:
            if self._handle_ack(raw_msg, self._logger):
                return
            raise

        if isinstance(payload, OrderUpdateStreamUpdate):
            self._handle_order(payload)
            self._handle_execution(payload)
        elif isinstance(payload, AccountUpdateStreamUpdate):
            self._handle_position(payload)
            self._handle_account(payload)

    def _handle_order(self, payload: OrderUpdateStreamUpdate) -> None:
        """Handle order update messages.

        Args:
            payload: Decoded order update payload.
        """
        msg = payload.to_order_msg(
            venue=self._venue,
            instrument_collection=self._instrument_collection,
        )
        self.broadcast(msg)

    def _handle_execution(self, payload: OrderUpdateStreamUpdate) -> None:
        """Handle execution update messages.

        Args:
            payload: Decoded order update payload.
        """
        if payload.order.status != "TRADE":
            return
        msg = payload.to_execution_msg(
            venue=self._venue,
            instrument_collection=self._instrument_collection,
        )
        self.broadcast(msg)

    def _handle_position(self, payload: AccountUpdateStreamUpdate) -> None:
        """Handle position update messages.

        Args:
            payload: Decoded account update payload.
        """
        for msg in payload.to_position_msg(
            venue=self._venue,
            instrument_collection=self._instrument_collection,
        ):
            self.broadcast(msg)

    def _handle_account(self, payload: AccountUpdateStreamUpdate) -> None:
        """Handle account update messages.

        Args:
            payload: Decoded account update payload.
        """
        msg = payload.to_account_msg(self._venue)
        self.broadcast(msg)

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
                response = await self._exchange.extend_listen_key(self._listen_key)
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                self._logger.warning(
                    f"{self.__class__.__name__}._refresh_listen_key_loop error; {exc}"
                )
                continue
            if not response.is_successful:
                self._logger.warning(
                    f"{self.__class__.__name__}._refresh_listen_key_loop "
                    f"listen key refresh failed; {response.err_msg}"
                )
                continue
            self._logger.info(
                f"{self.__class__.__name__}._refresh_listen_key_loop "
                "listen key refreshed."
            )
