"""
Bybit stream handlers for market and private websocket connections.

Usage: instantiated by BybitMarketStreamManager and BybitPrivateStreamManager.
Components: typed decoders, subscription payloads, authentication, and per-stream caching.
"""

from __future__ import annotations

import asyncio
import hashlib
import hmac
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
from framework.base.stream.models import (
    Execution,
    ExecutionMsg,
    Moments,
    Msg,
    Order,
    OrderMsg,
    PrivateDataStreamType,
    StreamType,
    TickerMsg,
)
from framework.base.tools import EnumMap, SimpleCache
from framework.bybit.stream.models import (
    BybitExecutionMsg,
    BybitOrderbookMsg,
    BybitOrderMsg,
    BybitPositionMsg,
    BybitPrivateMsg,
    BybitPublicMsg,
    BybitTickerMsg,
    BybitTradeMsg,
    BybitWalletMsg,
)
from mm_toolbox.logging.standard import Logger
from mm_toolbox.time import time_ns, time_ms


class _BybitStreamHandler(ABC):
    """Shared Bybit stream behavior with ACK logging."""

    _logger: Logger

    def __init__(self) -> None:
        """Initialize request identifier state."""
        self._req_id_counter = 0

    def _next_req_id(self) -> str:
        """Return a new request identifier.

        Returns:
            str: Request identifier.
        """
        self._req_id_counter += 1
        return str(self._req_id_counter)

    def _handle_ack(self, raw_msg: bytes) -> bool:
        """Handle ACK/control messages for logging.

        Args:
            raw_msg: Raw websocket payload bytes.

        Returns:
            bool: True if handled as an ACK message.
        """
        try:
            payload = msgspec.json.decode(raw_msg)
        except Exception:
            return False
        if not isinstance(payload, dict):
            return False
        op = payload.get("op")
        if not isinstance(op, str):
            return False
        if op in {"ping", "pong", "auth"}:
            return True
        success = payload.get("success")
        if success is None:
            ret_code = payload.get("retCode")
            if ret_code is None:
                return True
            success = ret_code == 0
        req_id = payload.get("req_id") or payload.get("reqId")
        message = payload.get("ret_msg") or payload.get("retMsg")
        suffix_parts: list[str] = []
        if req_id is not None:
            suffix_parts.append(f"req_id={req_id}")
        if message and not success:
            suffix_parts.append(message)
        suffix = f"; {'; '.join(suffix_parts)}" if suffix_parts else ""
        status = "succeeded" if success else "failed"
        log_fn = self._logger.info if success else self._logger.warning
        log_fn(f"{self.__class__.__name__}._handle_ack {op} ACK {status}{suffix}")
        return True


class BybitTickerHandler(TickerStreamHandler, _BybitStreamHandler):
    """Bybit ticker stream handler with partial data caching."""

    def __init__(
        self,
        connection: WebSocketConnection,
        instrument_collection: InstrumentCollection,
        venue: Venue,
        logger: Logger,
        consumer_queues: list[asyncio.Queue[Msg]],
    ) -> None:
        """Initialize the Bybit ticker handler.

        Args:
            connection: WebSocket connection for ticker stream.
            instrument_collection: Shared instrument collection.
            venue: Venue for the handler.
            logger: Logger for diagnostics.
            consumer_queues: Queues to broadcast messages to.
        """
        TickerStreamHandler.__init__(
            self,
            connection=connection,
            instrument_collection=instrument_collection,
            venue=venue,
            logger=logger,
            consumer_queues=consumer_queues,
        )
        _BybitStreamHandler.__init__(self)
        self._decoder = msgspec.json.Decoder(BybitPublicMsg[BybitTickerMsg])
        self._latest_symbol_ticker_map: dict[str, TickerMsg] = {}

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
        """Build the Bybit ticker subscribe payload.

        Args:
            instruments: Instruments to subscribe to.
            stream_types: Ignored for market streams.

        Returns:
            bytes: Serialized payload bytes.
        """
        args = [f"tickers.{inst.symbol}" for inst in instruments]
        req_id = self._next_req_id()
        return msgspec.json.encode({"op": "subscribe", "args": args, "req_id": req_id})

    def build_unsubscribe_payload(
        self,
        instruments: list[Instrument],
        stream_types: set[StreamType] | None = None,
    ) -> bytes:
        """Build the Bybit ticker unsubscribe payload.

        Args:
            instruments: Instruments to unsubscribe from.
            stream_types: Ignored for market streams.

        Returns:
            bytes: Serialized payload bytes.
        """
        args = [f"tickers.{inst.symbol}" for inst in instruments]
        req_id = self._next_req_id()
        return msgspec.json.encode(
            {"op": "unsubscribe", "args": args, "req_id": req_id}
        )

    async def decode_and_broadcast(self, raw_msg: bytes) -> None:
        """Decode ticker messages and broadcast updates.

        Args:
            raw_msg: Raw websocket payload bytes.
        """
        try:
            decoded = self._decoder.decode(raw_msg)
            exch_time_ns = decoded.ts * 1_000_000 if decoded.ts else None
            ticker_msg = decoded.data.to_ticker_msg(
                venue=self.venue,
                instrument_collection=self.instrument_collection,
                exch_time_ns=exch_time_ns,
            )
            symbol = decoded.data.symbol
            if decoded.type == "delta":
                ticker_msg = self._merge_cached_ticker(symbol, ticker_msg)
            self._latest_symbol_ticker_map[symbol] = ticker_msg
            self.broadcast(ticker_msg)
        except msgspec.DecodeError:
            if self._handle_ack(raw_msg):
                return
            raise
        except Exception as exc:
            self._logger.warning(
                f"{self.__class__.__name__}.decode_and_broadcast error; {exc}"
            )

    def _merge_cached_ticker(self, symbol: str, incoming: TickerMsg) -> TickerMsg:
        """Merge partial ticker fields with cached values.

        Args:
            symbol: Symbol key for the cache.
            incoming: Incoming ticker message.

        Returns:
            TickerMsg: Merged ticker message.
        """
        cached = self._latest_symbol_ticker_map.get(symbol)
        if cached is None:
            return incoming

        def pick(value: float, fallback: float) -> float:
            """Select fallback when the incoming value is zero.

            Args:
                value: Incoming value.
                fallback: Cached fallback value.

            Returns:
                float: Value with fallback applied.
            """
            return fallback if value == 0.0 and fallback != 0.0 else value

        return TickerMsg(
            moments=incoming.moments,
            venue=incoming.venue,
            instrument=incoming.instrument,
            mark_price=pick(incoming.mark_price, cached.mark_price),
            index_price=pick(incoming.index_price, cached.index_price),
            funding_rate=pick(incoming.funding_rate, cached.funding_rate),
            next_funding_time_ms=pick(
                incoming.next_funding_time_ms, cached.next_funding_time_ms
            ),
            open_interest=pick(incoming.open_interest, cached.open_interest),
            avg_volume_24h=pick(incoming.avg_volume_24h, cached.avg_volume_24h),
            price_chg_24h_pct=pick(
                incoming.price_chg_24h_pct, cached.price_chg_24h_pct
            ),
        )


class BybitBBOHandler(BBOStreamHandler, _BybitStreamHandler):
    """Bybit BBO stream handler."""

    def __init__(
        self,
        connection: WebSocketConnection,
        instrument_collection: InstrumentCollection,
        venue: Venue,
        logger: Logger,
        consumer_queues: list[asyncio.Queue[Msg]],
    ) -> None:
        """Initialize the Bybit BBO handler.

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
        _BybitStreamHandler.__init__(self)
        self._decoder = msgspec.json.Decoder(BybitPublicMsg[BybitOrderbookMsg])

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
        """Build the Bybit BBO subscribe payload.

        Args:
            instruments: Instruments to subscribe to.
            stream_types: Ignored for market streams.

        Returns:
            bytes: Serialized payload bytes.
        """
        args = [f"orderbook.1.{inst.symbol}" for inst in instruments]
        req_id = self._next_req_id()
        return msgspec.json.encode({"op": "subscribe", "args": args, "req_id": req_id})

    def build_unsubscribe_payload(
        self,
        instruments: list[Instrument],
        stream_types: set[StreamType] | None = None,
    ) -> bytes:
        """Build the Bybit BBO unsubscribe payload.

        Args:
            instruments: Instruments to unsubscribe from.
            stream_types: Ignored for market streams.

        Returns:
            bytes: Serialized payload bytes.
        """
        args = [f"orderbook.1.{inst.symbol}" for inst in instruments]
        req_id = self._next_req_id()
        return msgspec.json.encode(
            {"op": "unsubscribe", "args": args, "req_id": req_id}
        )

    async def decode_and_broadcast(self, raw_msg: bytes) -> None:
        """Decode BBO messages and broadcast updates.

        Args:
            raw_msg: Raw websocket payload bytes.
        """
        try:
            decoded = self._decoder.decode(raw_msg)
            exch_time_ns = decoded.ts * 1_000_000 if decoded.ts else None
            orderbook_msg = decoded.data.to_orderbook_msg(
                venue=self.venue,
                instrument_collection=self.instrument_collection,
                is_bbo=True,
                is_snapshot=decoded.type == "snapshot",
                exch_time_ns=exch_time_ns,
            )
            self.broadcast(orderbook_msg)
        except msgspec.DecodeError:
            if self._handle_ack(raw_msg):
                return
            raise
        except Exception as exc:
            self._logger.warning(
                f"{self.__class__.__name__}.decode_and_broadcast error; {exc}"
            )


class BybitOrderbookHandler(OrderbookStreamHandler, _BybitStreamHandler):
    """Bybit full orderbook stream handler."""

    def __init__(
        self,
        connection: WebSocketConnection,
        instrument_collection: InstrumentCollection,
        venue: Venue,
        logger: Logger,
        consumer_queues: list[asyncio.Queue[Msg]],
    ) -> None:
        """Initialize the Bybit orderbook handler.

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
        _BybitStreamHandler.__init__(self)
        self._decoder = msgspec.json.Decoder(BybitPublicMsg[BybitOrderbookMsg])

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
        """Build the Bybit orderbook subscribe payload.

        Args:
            instruments: Instruments to subscribe to.
            stream_types: Ignored for market streams.

        Returns:
            bytes: Serialized payload bytes.
        """
        args = [f"orderbook.500.{inst.symbol}" for inst in instruments]
        req_id = self._next_req_id()
        return msgspec.json.encode({"op": "subscribe", "args": args, "req_id": req_id})

    def build_unsubscribe_payload(
        self,
        instruments: list[Instrument],
        stream_types: set[StreamType] | None = None,
    ) -> bytes:
        """Build the Bybit orderbook unsubscribe payload.

        Args:
            instruments: Instruments to unsubscribe from.
            stream_types: Ignored for market streams.

        Returns:
            bytes: Serialized payload bytes.
        """
        args = [f"orderbook.1000.{inst.symbol}" for inst in instruments]
        req_id = self._next_req_id()
        return msgspec.json.encode(
            {"op": "unsubscribe", "args": args, "req_id": req_id}
        )

    async def decode_and_broadcast(self, raw_msg: bytes) -> None:
        """Decode orderbook messages and broadcast updates.

        Args:
            raw_msg: Raw websocket payload bytes.
        """
        try:
            decoded = self._decoder.decode(raw_msg)
            exch_time_ns = decoded.ts * 1_000_000 if decoded.ts else None
            orderbook_msg = decoded.data.to_orderbook_msg(
                venue=self.venue,
                instrument_collection=self.instrument_collection,
                is_bbo=False,
                is_snapshot=decoded.type == "snapshot",
                exch_time_ns=exch_time_ns,
            )
            self.broadcast(orderbook_msg)
        except msgspec.DecodeError:
            if self._handle_ack(raw_msg):
                return
            raise
        except Exception as exc:
            self._logger.warning(
                f"{self.__class__.__name__}.decode_and_broadcast error; {exc}"
            )


class BybitTradesHandler(TradesStreamHandler, _BybitStreamHandler):
    """Bybit trades stream handler with sequence deduplication."""

    def __init__(
        self,
        connection: WebSocketConnection,
        instrument_collection: InstrumentCollection,
        venue: Venue,
        logger: Logger,
        consumer_queues: list[asyncio.Queue[Msg]],
    ) -> None:
        """Initialize the Bybit trades handler.

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
        _BybitStreamHandler.__init__(self)
        self._decoder = msgspec.json.Decoder(BybitTradeMsg)
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
        """Build the Bybit trades subscribe payload.

        Args:
            instruments: Instruments to subscribe to.
            stream_types: Ignored for market streams.

        Returns:
            bytes: Serialized payload bytes.
        """
        args = [f"publicTrade.{inst.symbol}" for inst in instruments]
        req_id = self._next_req_id()
        return msgspec.json.encode({"op": "subscribe", "args": args, "req_id": req_id})

    def build_unsubscribe_payload(
        self,
        instruments: list[Instrument],
        stream_types: set[StreamType] | None = None,
    ) -> bytes:
        """Build the Bybit trades unsubscribe payload.

        Args:
            instruments: Instruments to unsubscribe from.
            stream_types: Ignored for market streams.

        Returns:
            bytes: Serialized payload bytes.
        """
        args = [f"publicTrade.{inst.symbol}" for inst in instruments]
        req_id = self._next_req_id()
        return msgspec.json.encode(
            {"op": "unsubscribe", "args": args, "req_id": req_id}
        )

    async def decode_and_broadcast(self, raw_msg: bytes) -> None:
        """Decode trade messages and broadcast updates.

        Args:
            raw_msg: Raw websocket payload bytes.
        """
        try:
            decoded = self._decoder.decode(raw_msg)
            trade_msg = decoded.to_trade_msg(
                venue=self.venue,
                instrument_collection=self.instrument_collection,
                symbol_to_seq_cache=self._symbol_to_seq_cache,
            )
            if trade_msg is not None:
                self.broadcast(trade_msg)
        except msgspec.DecodeError:
            if self._handle_ack(raw_msg):
                return
            raise
        except Exception as exc:
            self._logger.warning(
                f"{self.__class__.__name__}.decode_and_broadcast error; {exc}"
            )


class BybitPrivateHandler(PrivateStreamHandler, _BybitStreamHandler):
    """Unified Bybit private stream handler for all 4 private stream types.

    Handles order, position, execution, and account updates from a single
    websocket connection with HMAC authentication.
    """

    def __init__(
        self,
        venue: Venue,
        logger: Logger,
        connection: WebSocketConnection,
        instrument_collection: InstrumentCollection,
        consumer_queues: list[asyncio.Queue[Msg]],
        api_key: str,
        api_secret: str,
    ) -> None:
        """Initialize the Bybit private handler.

        Args:
            venue: Venue this handler streams from.
            logger: Logger for diagnostics.
            connection: WebSocket connection for private streams.
            instrument_collection: Shared instrument collection.
            consumer_queues: Queues to broadcast messages to.
            api_key: Bybit API key.
            api_secret: Bybit API secret.
        """
        super().__init__(
            venue=venue,
            logger=logger,
            connection=connection,
            instrument_collection=instrument_collection,
            consumer_queues=consumer_queues,
        )
        _BybitStreamHandler.__init__(self)
        self._api_key = api_key
        self._api_secret = api_secret
        self._stream_type_topic_map = EnumMap(
            PrivateDataStreamType,
            {
                PrivateDataStreamType.ORDER: "order",
                PrivateDataStreamType.POSITION: "position",
                PrivateDataStreamType.EXECUTION: "execution",
                PrivateDataStreamType.ACCOUNT: "wallet",
            },
        )
        self._decoder = msgspec.json.Decoder(
            BybitPrivateMsg[BybitOrderMsg]
            | BybitPrivateMsg[BybitPositionMsg]
            | BybitPrivateMsg[BybitExecutionMsg]
            | BybitPrivateMsg[BybitWalletMsg]
        )

    def build_authentication_payload(self) -> bytes:
        """Build Bybit HMAC authentication payload.

        Returns:
            bytes: Serialized authentication payload.
        """
        expire = str(time_ms() + 60_000)
        signature = hmac.new(
            key=self._api_secret.encode("utf-8"),
            msg=f"GET/realtime{expire}".encode("utf-8"),
            digestmod=hashlib.sha256,
        ).hexdigest()
        return msgspec.json.encode(
            {"op": "auth", "args": [self._api_key, expire, signature]}
        )

    def build_subscribe_payload(
        self,
        instruments: list[Instrument],
        stream_types: set[StreamType] | None = None,
    ) -> bytes:
        """Build Bybit private subscribe payload.

        Args:
            instruments: Ignored for private streams.
            stream_types: Private stream types to subscribe to.

        Returns:
            bytes: Serialized subscribe payload, or empty bytes if no types.
        """
        if not stream_types:
            return b""
        args = [self._stream_type_topic_map.enum_to_str(st) for st in stream_types]
        req_id = self._next_req_id()
        return msgspec.json.encode({"op": "subscribe", "args": args, "req_id": req_id})

    def build_unsubscribe_payload(
        self,
        instruments: list[Instrument],
        stream_types: set[StreamType] | None = None,
    ) -> bytes:
        """Build Bybit private unsubscribe payload.

        Args:
            instruments: Ignored for private streams.
            stream_types: Private stream types to unsubscribe from.

        Returns:
            bytes: Serialized unsubscribe payload, or empty bytes if no types.
        """
        if not stream_types:
            return b""
        args = [self._stream_type_topic_map.enum_to_str(st) for st in stream_types]
        req_id = self._next_req_id()
        return msgspec.json.encode(
            {"op": "unsubscribe", "args": args, "req_id": req_id}
        )

    async def decode_and_broadcast(self, raw_msg: bytes) -> None:
        """Decode and broadcast Bybit private messages.

        Args:
            raw_msg: Raw websocket payload bytes.
        """
        try:
            payload = self._decoder.decode(raw_msg)
            if not isinstance(payload, BybitPrivateMsg):
                return

            exch_time_ns = payload.ts * 1_000_000

            match payload.topic:
                case "order":
                    self._handle_order(payload, exch_time_ns)
                case "position":
                    self._handle_position(payload, exch_time_ns)
                case "execution":
                    self._handle_execution(payload, exch_time_ns)
                case "wallet":
                    self._handle_account(payload, exch_time_ns)
        except msgspec.DecodeError:
            if self._handle_control_message(raw_msg):
                return
            raise
        except Exception as exc:
            self._logger.warning(
                f"{self.__class__.__name__}.decode_and_broadcast error; {exc}"
            )

    def _handle_order(self, payload: BybitPrivateMsg, exch_time_ns: int) -> None:
        """Handle order update messages.

        Args:
            payload: Decoded private payload.
            exch_time_ns: Exchange timestamp in nanoseconds.
        """
        if not payload.data:
            return
        orders: list[Order] = []
        instrument: Instrument | None = None
        for update in payload.data:
            if not isinstance(update, BybitOrderMsg):
                continue
            inst = self._instrument_collection.get(self._venue, update.symbol)
            if not inst:
                continue
            instrument = inst
            orders.append(update.to_order())
        if orders and instrument is not None:
            self.broadcast(
                OrderMsg(
                    moments=Moments(exch_time_ns=exch_time_ns, recv_time_ns=time_ns()),
                    venue=self._venue,
                    instrument=instrument,
                    orders=orders,
                )
            )

    def _handle_position(self, payload: BybitPrivateMsg, exch_time_ns: int) -> None:
        """Handle position update messages.

        Args:
            payload: Decoded private payload.
            exch_time_ns: Exchange timestamp in nanoseconds.
        """
        for update in payload.data:
            if not isinstance(update, BybitPositionMsg):
                continue
            msg = update.to_position_msg(
                venue=self._venue,
                instrument_collection=self._instrument_collection,
                exch_time_ns=exch_time_ns,
            )
            if msg:
                self.broadcast(msg)

    def _handle_execution(self, payload: BybitPrivateMsg, exch_time_ns: int) -> None:
        """Handle execution update messages.

        Args:
            payload: Decoded private payload.
            exch_time_ns: Exchange timestamp in nanoseconds.
        """
        if not payload.data:
            return
        executions: list[Execution] = []
        instrument: Instrument | None = None
        for update in payload.data:
            if not isinstance(update, BybitExecutionMsg):
                continue
            inst = self._instrument_collection.get(self._venue, update.symbol)
            if not inst:
                continue
            instrument = inst
            executions.append(update.to_execution())
        if executions and instrument is not None:
            self.broadcast(
                ExecutionMsg(
                    moments=Moments(exch_time_ns=exch_time_ns, recv_time_ns=time_ns()),
                    venue=self._venue,
                    instrument=instrument,
                    executions=executions,
                )
            )

    def _handle_account(self, payload: BybitPrivateMsg, exch_time_ns: int) -> None:
        """Handle account update messages.

        Args:
            payload: Decoded private payload.
            exch_time_ns: Exchange timestamp in nanoseconds.
        """
        if not payload.data:
            return
        update = payload.data[0]
        if not isinstance(update, BybitWalletMsg):
            return
        self.broadcast(
            update.to_account_msg(venue=self._venue, exch_time_ns=exch_time_ns)
        )

    def _handle_control_message(self, raw_msg: bytes) -> bool:
        """Handle Bybit control messages (ACK/auth/ping).

        Args:
            raw_msg: Raw websocket payload bytes.

        Returns:
            bool: True if handled as a control message.
        """
        return self._handle_ack(raw_msg)
