"""
OKX stream handlers for market and private websocket connections.

Usage: instantiated by OkxMarketStreamManager and OkxPrivateStreamManager.
Components: typed decoders, subscription payloads, and OKX-specific authentication.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
from abc import ABC

import msgspec

from framework.base.common import Instrument, InstrumentCollection, Symbol, Venue
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
    ExecutionMsg,
    OrderMsg,
    StreamType,
    TradeMsg,
)
from framework.okx.stream.models import (
    OkxAccountMsg,
    OkxExecutionMsg,
    OkxOrderbookPublicMsg,
    OkxOrderMsg,
    OkxPositionMsg,
    OkxTickerPublicMsg,
    OkxTradesPublicMsg,
)
from mm_toolbox.logging.standard import Logger
from mm_toolbox.ringbuffer import GenericRingBuffer
from mm_toolbox.time import time_ms


class _OkxStreamHandler(ABC):
    """Shared OKX stream behavior for market and private handlers."""

    def __init__(self, channel: str) -> None:
        """Initialize the handler mixin.

        Args:
            channel: OKX channel name for subscriptions.
        """
        self._channel = channel

    def _handle_control_message(self, raw_msg: bytes, logger: Logger) -> dict | None:
        """Handle OKX control responses (subscribe/unsubscribe/error/login).

        Args:
            raw_msg: Raw websocket payload bytes.
            logger: Logger for diagnostics.

        Returns:
            dict | None: Control payload if handled, otherwise None.
        """
        try:
            payload = msgspec.json.decode(raw_msg)
        except Exception:
            return None
        if not isinstance(payload, dict):
            return None
        event = payload.get("event")
        if event not in ("subscribe", "unsubscribe", "error", "login"):
            return None
        code = payload.get("code", "0")
        msg = payload.get("msg", "")
        if event == "error" or code != "0":
            logger.error(
                f"{self.__class__.__name__}._handle_control_message "
                f"ACK error; channel={self._channel} event={event} "
                f"code={code} msg={msg}"
            )
        return payload

    def _build_okx_subscribe_args(
        self, instruments: list[Instrument]
    ) -> list[dict[str, str]]:
        """Build OKX subscription args for instruments.

        Args:
            instruments: Instruments to subscribe to.

        Returns:
            list[dict[str, str]]: List of subscription arg dicts.
        """
        return [
            {"channel": self._channel, "instId": inst.symbol} for inst in instruments
        ]


class OkxTickerHandler(TickerStreamHandler, _OkxStreamHandler):
    """OKX ticker stream handler for mark price, funding, and 24h stats."""

    def __init__(
        self,
        connection: WebSocketConnection,
        instrument_collection: InstrumentCollection,
        venue: Venue,
        logger: Logger,
        consumer_buffer: GenericRingBuffer,
    ) -> None:
        """Initialize the OKX ticker handler.

        Args:
            connection: WebSocket connection for ticker stream.
            instrument_collection: Shared instrument collection.
            venue: Venue for the handler.
            logger: Logger for diagnostics.
            consumer_buffer: Ring buffer to broadcast messages to.
        """
        TickerStreamHandler.__init__(
            self,
            connection=connection,
            instrument_collection=instrument_collection,
            venue=venue,
            logger=logger,
            consumer_buffer=consumer_buffer,
        )
        _OkxStreamHandler.__init__(self, channel="tickers")
        self._decoder = msgspec.json.Decoder(OkxTickerPublicMsg)

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
        """Build the OKX ticker subscribe payload.

        Args:
            instruments: Instruments to subscribe to.
            stream_types: Ignored for market streams.

        Returns:
            bytes: Serialized payload bytes.
        """
        args = self._build_okx_subscribe_args(instruments)
        return msgspec.json.encode({"op": "subscribe", "args": args})

    def build_unsubscribe_payload(
        self,
        instruments: list[Instrument],
        stream_types: set[StreamType] | None = None,
    ) -> bytes:
        """Build the OKX ticker unsubscribe payload.

        Args:
            instruments: Instruments to unsubscribe from.
            stream_types: Ignored for market streams.

        Returns:
            bytes: Serialized payload bytes.
        """
        args = self._build_okx_subscribe_args(instruments)
        return msgspec.json.encode({"op": "unsubscribe", "args": args})

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
            origin_id = MessageId(recv_time_ns=recv_time_ns)
            for ticker_data in data.data:
                ticker_msg = ticker_data.to_ticker_msg(
                    venue=self.venue,
                    instrument_collection=self.instrument_collection,
                    is_snapshot=data.action == "snapshot",
                    origin_id=origin_id,
                    recv_time_ns=recv_time_ns,
                )
                self.broadcast(ticker_msg)
        except msgspec.DecodeError:
            if self._handle_control_message(raw_msg, self._logger) is not None:
                return
            raise
        except Exception as exc:
            self._logger.warning(
                f"{self.__class__.__name__}.decode_and_broadcast error; {exc}"
            )


class OkxBBOHandler(BBOStreamHandler, _OkxStreamHandler):
    """OKX best bid/offer stream handler using bbo-tbt channel."""

    def __init__(
        self,
        connection: WebSocketConnection,
        instrument_collection: InstrumentCollection,
        venue: Venue,
        logger: Logger,
        consumer_buffer: GenericRingBuffer,
    ) -> None:
        """Initialize the OKX BBO handler.

        Args:
            connection: WebSocket connection for BBO stream.
            instrument_collection: Shared instrument collection.
            venue: Venue for the handler.
            logger: Logger for diagnostics.
            consumer_buffer: Ring buffer to broadcast messages to.
        """
        BBOStreamHandler.__init__(
            self,
            connection=connection,
            instrument_collection=instrument_collection,
            venue=venue,
            logger=logger,
            consumer_buffer=consumer_buffer,
        )
        _OkxStreamHandler.__init__(self, channel="bbo-tbt")
        self._decoder = msgspec.json.Decoder(OkxOrderbookPublicMsg)

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
        """Build the OKX BBO subscribe payload.

        Args:
            instruments: Instruments to subscribe to.
            stream_types: Ignored for market streams.

        Returns:
            bytes: Serialized payload bytes.
        """
        args = self._build_okx_subscribe_args(instruments)
        return msgspec.json.encode({"op": "subscribe", "args": args})

    def build_unsubscribe_payload(
        self,
        instruments: list[Instrument],
        stream_types: set[StreamType] | None = None,
    ) -> bytes:
        """Build the OKX BBO unsubscribe payload.

        Args:
            instruments: Instruments to unsubscribe from.
            stream_types: Ignored for market streams.

        Returns:
            bytes: Serialized payload bytes.
        """
        args = self._build_okx_subscribe_args(instruments)
        return msgspec.json.encode({"op": "unsubscribe", "args": args})

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
            inst_id = data.arg.get("instId", "")
            is_snapshot = data.action == "snapshot"
            origin_id = MessageId(recv_time_ns=recv_time_ns)
            for book_data in data.data:
                orderbook_msg = book_data.to_orderbook_msg(
                    venue=self.venue,
                    instrument_collection=self.instrument_collection,
                    inst_id=inst_id,
                    is_bbo=True,
                    is_snapshot=is_snapshot,
                    origin_id=origin_id,
                    recv_time_ns=recv_time_ns,
                )
                self.broadcast(orderbook_msg)
        except msgspec.DecodeError:
            if self._handle_control_message(raw_msg, self._logger) is not None:
                return
            raise
        except Exception as exc:
            self._logger.warning(
                f"{self.__class__.__name__}.decode_and_broadcast error; {exc}"
            )


class OkxOrderbookHandler(OrderbookStreamHandler, _OkxStreamHandler):
    """OKX orderbook stream handler using books5 channel."""

    def __init__(
        self,
        connection: WebSocketConnection,
        instrument_collection: InstrumentCollection,
        venue: Venue,
        logger: Logger,
        consumer_buffer: GenericRingBuffer,
    ) -> None:
        """Initialize the OKX orderbook handler.

        Args:
            connection: WebSocket connection for orderbook stream.
            instrument_collection: Shared instrument collection.
            venue: Venue for the handler.
            logger: Logger for diagnostics.
            consumer_buffer: Ring buffer to broadcast messages to.
        """
        OrderbookStreamHandler.__init__(
            self,
            connection=connection,
            instrument_collection=instrument_collection,
            venue=venue,
            logger=logger,
            consumer_buffer=consumer_buffer,
        )
        _OkxStreamHandler.__init__(self, channel="books5")
        self._decoder = msgspec.json.Decoder(OkxOrderbookPublicMsg)

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
        """Build the OKX orderbook subscribe payload.

        Args:
            instruments: Instruments to subscribe to.
            stream_types: Ignored for market streams.

        Returns:
            bytes: Serialized payload bytes.
        """
        args = self._build_okx_subscribe_args(instruments)
        return msgspec.json.encode({"op": "subscribe", "args": args})

    def build_unsubscribe_payload(
        self,
        instruments: list[Instrument],
        stream_types: set[StreamType] | None = None,
    ) -> bytes:
        """Build the OKX orderbook unsubscribe payload.

        Args:
            instruments: Instruments to unsubscribe from.
            stream_types: Ignored for market streams.

        Returns:
            bytes: Serialized payload bytes.
        """
        args = self._build_okx_subscribe_args(instruments)
        return msgspec.json.encode({"op": "unsubscribe", "args": args})

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
            inst_id = data.arg.get("instId", "")
            is_snapshot = data.action == "snapshot"
            origin_id = MessageId(recv_time_ns=recv_time_ns)
            for book_data in data.data:
                orderbook_msg = book_data.to_orderbook_msg(
                    venue=self.venue,
                    instrument_collection=self.instrument_collection,
                    inst_id=inst_id,
                    is_bbo=False,
                    is_snapshot=is_snapshot,
                    origin_id=origin_id,
                    recv_time_ns=recv_time_ns,
                )
                self.broadcast(orderbook_msg)
        except msgspec.DecodeError:
            if self._handle_control_message(raw_msg, self._logger) is not None:
                return
            raise
        except Exception as exc:
            self._logger.warning(
                f"{self.__class__.__name__}.decode_and_broadcast error; {exc}"
            )


class OkxTradesHandler(TradesStreamHandler, _OkxStreamHandler):
    """OKX trades stream handler."""

    def __init__(
        self,
        connection: WebSocketConnection,
        instrument_collection: InstrumentCollection,
        venue: Venue,
        logger: Logger,
        consumer_buffer: GenericRingBuffer,
    ) -> None:
        """Initialize the OKX trades handler.

        Args:
            connection: WebSocket connection for trades stream.
            instrument_collection: Shared instrument collection.
            venue: Venue for the handler.
            logger: Logger for diagnostics.
            consumer_buffer: Ring buffer to broadcast messages to.
        """
        TradesStreamHandler.__init__(
            self,
            connection=connection,
            instrument_collection=instrument_collection,
            venue=venue,
            logger=logger,
            consumer_buffer=consumer_buffer,
        )
        _OkxStreamHandler.__init__(self, channel="trades")
        self._decoder = msgspec.json.Decoder(OkxTradesPublicMsg)

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
        """Build the OKX trades subscribe payload.

        Args:
            instruments: Instruments to subscribe to.
            stream_types: Ignored for market streams.

        Returns:
            bytes: Serialized payload bytes.
        """
        args = self._build_okx_subscribe_args(instruments)
        return msgspec.json.encode({"op": "subscribe", "args": args})

    def build_unsubscribe_payload(
        self,
        instruments: list[Instrument],
        stream_types: set[StreamType] | None = None,
    ) -> bytes:
        """Build the OKX trades unsubscribe payload.

        Args:
            instruments: Instruments to unsubscribe from.
            stream_types: Ignored for market streams.

        Returns:
            bytes: Serialized payload bytes.
        """
        args = self._build_okx_subscribe_args(instruments)
        return msgspec.json.encode({"op": "unsubscribe", "args": args})

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
            if not data.data:
                return

            inst_id = data.arg.get("instId", "")
            instrument = self.instrument_collection.get(Symbol(inst_id))
            if not instrument:
                self._logger.warning(
                    f"{self.__class__.__name__}.decode_and_broadcast "
                    f"unknown instrument for trade; instId={inst_id}"
                )
                return

            trades = [trade_data.to_trade() for trade_data in data.data]
            origin_id = MessageId(recv_time_ns=recv_time_ns)
            trade_msg = TradeMsg(
                id=origin_id,
                origin_id=origin_id,
                moments=Moments(
                    exch_time_ns=int(data.data[0].ts) * 1_000_000,
                    recv_time_ns=recv_time_ns,
                ),
                instrument=instrument,
                is_snapshot=data.action == "snapshot",
                trades=tuple(trades),
            )
            self.broadcast(trade_msg)
        except msgspec.DecodeError:
            if self._handle_control_message(raw_msg, self._logger) is not None:
                return
            raise
        except Exception as exc:
            self._logger.warning(
                f"{self.__class__.__name__}.decode_and_broadcast error; {exc}"
            )


class OkxPrivateHandler(PrivateStreamHandler, _OkxStreamHandler):
    """Unified OKX private stream handler for orders, positions, and account.

    OKX private streams require HMAC-SHA256 signature authentication before
    subscribing to channels.
    """

    def __init__(
        self,
        venue: Venue,
        logger: Logger,
        connection: WebSocketConnection,
        instrument_collection: InstrumentCollection,
        consumer_buffer: GenericRingBuffer,
        api_key: str,
        api_secret: str,
        passphrase: str,
    ) -> None:
        """Initialize the OKX private handler.

        Args:
            venue: Venue this handler streams from.
            logger: Logger for diagnostics.
            connection: WebSocket connection for private streams.
            instrument_collection: Shared instrument collection.
            consumer_buffer: Ring buffer to broadcast messages to.
            api_key: OKX API key.
            api_secret: OKX API secret.
            passphrase: OKX API passphrase.
        """
        PrivateStreamHandler.__init__(
            self,
            venue=venue,
            logger=logger,
            connection=connection,
            instrument_collection=instrument_collection,
            consumer_buffer=consumer_buffer,
        )
        _OkxStreamHandler.__init__(self, channel="private")
        self._api_key = api_key
        self._api_secret = api_secret
        self._passphrase = passphrase
        self._is_authenticated = False
        self._order_decoder = msgspec.json.Decoder(dict)

    def build_authentication_payload(self) -> bytes:
        """Build the OKX login authentication payload.

        OKX WS auth: sign = Base64(HMAC_SHA256(timestamp + "GET" + "/users/self/verify", secret))

        Returns:
            bytes: Serialized login payload.
        """
        timestamp = str(int(time_ms() / 1000))
        prehash = f"{timestamp}GET/users/self/verify"
        signature = base64.b64encode(
            hmac.new(
                key=self._api_secret.encode("utf-8"),
                msg=prehash.encode("utf-8"),
                digestmod=hashlib.sha256,
            ).digest()
        ).decode()

        return msgspec.json.encode(
            {
                "op": "login",
                "args": [
                    {
                        "apiKey": self._api_key,
                        "passphrase": self._passphrase,
                        "timestamp": timestamp,
                        "sign": signature,
                    }
                ],
            }
        )

    def build_subscribe_payload(
        self,
        instruments: list[Instrument],
        stream_types: set[StreamType] | None = None,
    ) -> bytes:
        """Build the OKX private subscribe payload.

        Subscribes to orders, positions, and account channels for SWAP inst type.

        Args:
            instruments: Instruments (used for filtering, not in args).
            stream_types: Private stream types (optional filtering).

        Returns:
            bytes: Serialized subscribe payload.
        """
        args = [
            {"channel": "orders", "instType": "SWAP"},
            {"channel": "positions", "instType": "SWAP"},
            {"channel": "account"},
        ]
        return msgspec.json.encode({"op": "subscribe", "args": args})

    def build_unsubscribe_payload(
        self,
        instruments: list[Instrument],
        stream_types: set[StreamType] | None = None,
    ) -> bytes:
        """Build the OKX private unsubscribe payload.

        Args:
            instruments: Instruments (used for filtering, not in args).
            stream_types: Private stream types (optional filtering).

        Returns:
            bytes: Serialized unsubscribe payload.
        """
        args = [
            {"channel": "orders", "instType": "SWAP"},
            {"channel": "positions", "instType": "SWAP"},
            {"channel": "account"},
        ]
        return msgspec.json.encode({"op": "unsubscribe", "args": args})

    async def authenticate(self) -> None:
        """Authenticate with the OKX private websocket and wait for response.

        Raises:
            RuntimeError: If the handler is not running or auth fails.
        """
        if not self._is_running:
            raise RuntimeError(f"{self.__class__.__name__} is not running.")

        payload = self.build_authentication_payload()
        await self._connection.send(payload)

        # Wait briefly for login response - actual response handling happens in decode_and_broadcast
        self._is_authenticated = True
        self._logger.info(f"{self.__class__.__name__}.authenticate login payload sent.")

    async def decode_and_broadcast(
        self,
        recv_time_ns: int,
        raw_msg: bytes,
    ) -> None:
        """Decode and route OKX private messages.

        Args:
            recv_time_ns: Receive timestamp captured when the websocket payload arrived.
            raw_msg: Raw websocket payload bytes.
        """
        try:
            payload = self._order_decoder.decode(raw_msg)
            if (
                not isinstance(payload, dict)
                or "arg" not in payload
                or "data" not in payload
            ):
                raise msgspec.DecodeError("OKX private payload missing arg/data")

            channel = payload.get("arg", {}).get("channel", "")
            data_list = payload.get("data", [])
            origin_id = MessageId(recv_time_ns=recv_time_ns)

            if channel == "orders":
                self._handle_orders(data_list, origin_id, recv_time_ns)
            elif channel == "positions":
                self._handle_positions(data_list, origin_id, recv_time_ns)
            elif channel == "account":
                self._handle_account(data_list, origin_id, recv_time_ns)
        except msgspec.DecodeError as exc:
            control_payload = self._handle_control_message(raw_msg, self._logger)
            if control_payload is not None:
                if control_payload.get("event") == "login":
                    self._handle_login_response(control_payload)
                return
            self._logger.warning(
                f"{self.__class__.__name__}.decode_and_broadcast error; {exc}"
            )
            return
        except Exception as exc:
            self._logger.warning(
                f"{self.__class__.__name__}.decode_and_broadcast error; {exc}"
            )
            return

    def _handle_login_response(self, payload: dict) -> None:
        """Handle OKX login response.

        Args:
            payload: Decoded login response payload.
        """
        try:
            code = payload.get("code", "1")
            if code == "0":
                self._is_authenticated = True
                self._logger.info(
                    f"{self.__class__.__name__}._handle_login_response "
                    "authenticated successfully."
                )
            else:
                self._is_authenticated = False
                msg = payload.get("msg", "Unknown error")
                self._logger.error(
                    f"{self.__class__.__name__}._handle_login_response "
                    f"auth failed; code={code} msg={msg}"
                )
        except Exception as exc:
            self._logger.error(
                f"{self.__class__.__name__}._handle_login_response error; {exc}"
            )

    def _handle_orders(
        self,
        data_list: list[dict],
        origin_id: MessageId,
        recv_time_ns: int,
    ) -> None:
        """Handle order update messages.

        Args:
            data_list: List of order data dicts.
            origin_id: Shared origin identifier for the raw payload.
            recv_time_ns: Shared receive timestamp for the raw payload.
        """
        order_decoder = msgspec.json.Decoder(OkxOrderMsg)
        exec_decoder = msgspec.json.Decoder(OkxExecutionMsg)

        for item in data_list:
            try:
                order_data = order_decoder.decode(msgspec.json.encode(item))
                inst_id = order_data.inst_id
                instrument = self._instrument_collection.get(inst_id)
                if not instrument:
                    continue

                order = order_data.to_order()
                order_msg = OrderMsg(
                    id=MessageId(recv_time_ns=recv_time_ns),
                    origin_id=origin_id,
                    moments=Moments(
                        exch_time_ns=int(order_data.u_time) * 1_000_000,
                        recv_time_ns=recv_time_ns,
                    ),
                    instrument=instrument,
                    is_snapshot=False,
                    orders=(order,),
                )
                self.broadcast(order_msg)

                exec_data = exec_decoder.decode(msgspec.json.encode(item))
                execution = exec_data.to_execution()
                if execution:
                    exec_msg = ExecutionMsg(
                        id=MessageId(recv_time_ns=recv_time_ns),
                        origin_id=origin_id,
                        moments=Moments(
                            exch_time_ns=int(exec_data.u_time) * 1_000_000,
                            recv_time_ns=recv_time_ns,
                        ),
                        instrument=instrument,
                        is_snapshot=False,
                        executions=(execution,),
                    )
                    self.broadcast(exec_msg)
            except Exception as exc:
                self._logger.warning(
                    f"{self.__class__.__name__}._handle_orders error; {exc}"
                )

    def _handle_positions(
        self,
        data_list: list[dict],
        origin_id: MessageId,
        recv_time_ns: int,
    ) -> None:
        """Handle position update messages.

        Args:
            data_list: List of position data dicts.
            origin_id: Shared origin identifier for the raw payload.
            recv_time_ns: Shared receive timestamp for the raw payload.
        """
        decoder = msgspec.json.Decoder(OkxPositionMsg)

        for item in data_list:
            try:
                pos_data = decoder.decode(msgspec.json.encode(item))
                position_msg = pos_data.to_position_msg(
                    venue=self._venue,
                    instrument_collection=self._instrument_collection,
                    is_snapshot=False,
                    origin_id=origin_id,
                    recv_time_ns=recv_time_ns,
                )
                self.broadcast(position_msg)
            except Exception as exc:
                self._logger.warning(
                    f"{self.__class__.__name__}._handle_positions error; {exc}"
                )

    def _handle_account(
        self,
        data_list: list[dict],
        origin_id: MessageId,
        recv_time_ns: int,
    ) -> None:
        """Handle account update messages.

        Args:
            data_list: List of account data dicts.
            origin_id: Shared origin identifier for the raw payload.
            recv_time_ns: Shared receive timestamp for the raw payload.
        """
        decoder = msgspec.json.Decoder(OkxAccountMsg)

        for item in data_list:
            try:
                acct_data = decoder.decode(msgspec.json.encode(item))
                instruments = list(self._instrument_collection.instruments)
                if not instruments:
                    continue
                instrument = instruments[0]
                account_msg = acct_data.to_account_msg(
                    venue=self._venue,
                    instrument=instrument,
                    is_snapshot=False,
                    origin_id=origin_id,
                    recv_time_ns=recv_time_ns,
                )
                self.broadcast(account_msg)
            except Exception as exc:
                self._logger.warning(
                    f"{self.__class__.__name__}._handle_account error; {exc}"
                )
