"""
Tests for OKX stream handlers.

Validates mixin methods, market handler decoding, and private handler auth/routing.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable

import msgspec
import pytest

from framework.base.common import (
    Asset,
    Instrument,
    InstrumentCollection,
    InstrumentType,
    Symbol,
    Venue,
)
from framework.base.stream.models import (
    OrderbookMsg,
    TickerMsg,
    TradeMsg,
)
from framework.okx.stream.handlers import (
    OkxBBOHandler,
    OkxOrderbookHandler,
    OkxPrivateHandler,
    OkxTickerHandler,
    OkxTradesHandler,
    _OkxStreamHandler,
)
from mm_toolbox.logging.standard import Logger
from mm_toolbox.ringbuffer import GenericRingBuffer


class DummyConnection:
    """Connection stub for handler tests."""

    def __init__(self) -> None:
        """Initialize the dummy connection."""
        self.sent: list[bytes] = []
        self.connected = False
        self.url = "wss://example/ws"
        self._callbacks: list[Callable[[], Awaitable[None]]] = []

    async def connect(self) -> None:
        """Mark the connection as established."""
        if self.connected:
            return
        self.connected = True

    async def disconnect(self) -> None:
        """Mark the connection as closed."""
        if not self.connected:
            return
        self.connected = False

    async def send(self, data: bytes) -> None:
        """Capture outbound payloads.

        Args:
            data: Serialized payload bytes.

        Raises:
            ConnectionError: If the websocket is not connected.
        """
        if not self.connected:
            raise ConnectionError("WebSocket is not connected.")
        self.sent.append(data)

    def add_reconnect_callback(self, callback: Callable[[], Awaitable[None]]) -> None:
        """Register reconnect callbacks.

        Args:
            callback: Callback to invoke on reconnect.
        """
        self._callbacks.append(callback)

    def set_url(self, url: str) -> None:
        """Update the websocket URL.

        Args:
            url: New websocket URL.

        Raises:
            ValueError: If the URL is empty.
        """
        if not url:
            raise ValueError("Invalid url; expected non-empty string.")
        self.url = url


class ConcreteOkxHandler(_OkxStreamHandler):
    """Concrete implementation of mixin for testing."""

    def __init__(self, channel: str = "test") -> None:
        """Initialize the concrete handler.

        Args:
            channel: Channel name for testing.
        """
        super().__init__(channel=channel)


def make_collection() -> InstrumentCollection:
    """Create an OKX instrument collection fixture.

    Returns:
        InstrumentCollection: Collection containing an OKX instrument.
    """
    instrument = Instrument(
        venue=Venue.OKX,
        base=Asset("BTC"),
        quote=Asset("USDT"),
        symbol=Symbol("BTC-USDT-SWAP"),
        code=0,
        instrument_type=InstrumentType.PERPETUAL,
        tick_size=0.01,
        lot_size=0.001,
    )
    return InstrumentCollection([instrument])


class TestOkxStreamHandlerMixin:
    """Layer 1: Tests for _OkxStreamHandler mixin methods."""

    def test_handle_control_message_subscribe(self) -> None:
        """Test subscribe acknowledgements are recognized."""
        handler = ConcreteOkxHandler()
        msg = b'{"event": "subscribe", "arg": {"channel": "tickers"}}'
        payload = handler._handle_control_message(msg, Logger(name="test"))
        assert payload is not None
        assert payload["event"] == "subscribe"

    def test_handle_control_message_error(self) -> None:
        """Test error acknowledgements are recognized."""
        handler = ConcreteOkxHandler()
        msg = b'{"event": "error", "code": "60001", "msg": "Invalid"}'
        payload = handler._handle_control_message(msg, Logger(name="test"))
        assert payload is not None
        assert payload["event"] == "error"

    def test_handle_control_message_login(self) -> None:
        """Test login acknowledgements are recognized."""
        handler = ConcreteOkxHandler()
        msg = b'{"event": "login", "code": "0", "msg": ""}'
        payload = handler._handle_control_message(msg, Logger(name="test"))
        assert payload is not None
        assert payload["event"] == "login"

    def test_handle_control_message_ignores_data(self) -> None:
        """Test data messages are not treated as control acknowledgements."""
        handler = ConcreteOkxHandler()
        msg = b'{"arg": {"channel": "tickers"}, "data": [{}]}'
        assert handler._handle_control_message(msg, Logger(name="test")) is None

    def test_build_okx_subscribe_args(self) -> None:
        """Test subscription args builder."""
        handler = ConcreteOkxHandler(channel="tickers")
        collection = make_collection()
        instruments = list(collection.instruments)
        args = handler._build_okx_subscribe_args(instruments)
        assert len(args) == 1
        assert args[0]["channel"] == "tickers"
        assert args[0]["instId"] == "BTC-USDT-SWAP"


class TestOkxTickerHandler:
    """Layer 2: OKX ticker handler behavior."""

    @pytest.mark.asyncio
    async def test_ticker_decoding(self) -> None:
        """Test ticker messages decode to TickerMsg."""
        queue = GenericRingBuffer(16)
        collection = make_collection()
        handler = OkxTickerHandler(
            connection=DummyConnection(),  # type: ignore[arg-type]
            instrument_collection=collection,
            venue=Venue.OKX,
            logger=Logger(name="test"),
            consumer_buffer=queue,
        )
        messages = [
            (
                "tickers",
                "BTC-USDT-SWAP",
                {
                    "last": "30000.5",
                    "open24h": "29000",
                    "vol24h": "100000",
                    "ts": "1597026383085",
                },
            ),
            (
                "mark-price",
                "BTC-USDT-SWAP",
                {"markPx": "30000.0", "ts": "1597026383085"},
            ),
            (
                "funding-rate",
                "BTC-USDT-SWAP",
                {
                    "fundingRate": "0.0001",
                    "fundingTime": "1596998400000",
                    "nextFundingTime": "1597027200000",
                },
            ),
            (
                "open-interest",
                "BTC-USDT-SWAP",
                {"oi": "100000.5", "ts": "1597026383085"},
            ),
            ("index-tickers", "BTC-USDT", {"idxPx": "29995.25", "ts": "1597026383085"}),
        ]
        for channel, inst_id, data in messages:
            payload = {
                "arg": {"channel": channel, "instId": inst_id},
                "data": [{"instId": inst_id, **data}],
            }
            await handler.decode_and_broadcast(1, msgspec.json.encode(payload))
        msg = queue.consume()
        assert isinstance(msg, TickerMsg)
        assert msg.mark_price == 30000.0
        assert msg.funding_rate == 0.0001

    @pytest.mark.asyncio
    async def test_ticker_ack_is_skipped(self) -> None:
        """Test ACK messages are handled without error."""
        queue = GenericRingBuffer(16)
        collection = make_collection()
        handler = OkxTickerHandler(
            connection=DummyConnection(),  # type: ignore[arg-type]
            instrument_collection=collection,
            venue=Venue.OKX,
            logger=Logger(name="test"),
            consumer_buffer=queue,
        )
        ack_payload = b'{"event": "subscribe", "arg": {"channel": "tickers"}}'
        await handler.decode_and_broadcast(1, ack_payload)
        assert queue.is_empty()

    def test_build_subscribe_payload(self) -> None:
        """Test subscribe payload format."""
        collection = make_collection()
        handler = OkxTickerHandler(
            connection=DummyConnection(),  # type: ignore[arg-type]
            instrument_collection=collection,
            venue=Venue.OKX,
            logger=Logger(name="test"),
            consumer_buffer=GenericRingBuffer(1),
        )
        instruments = list(collection.instruments)
        payload = handler.build_subscribe_payload(instruments)
        decoded = msgspec.json.decode(payload)
        assert decoded["op"] == "subscribe"
        assert len(decoded["args"]) == 5
        assert {arg["channel"] for arg in decoded["args"]} == {
            "tickers",
            "mark-price",
            "funding-rate",
            "open-interest",
            "index-tickers",
        }


class TestOkxBBOHandler:
    """Layer 2: OKX BBO handler behavior."""

    @pytest.mark.asyncio
    async def test_bbo_decoding(self) -> None:
        """Test BBO messages decode to OrderbookMsg with is_bbo=True."""
        queue = GenericRingBuffer(16)
        collection = make_collection()
        handler = OkxBBOHandler(
            connection=DummyConnection(),  # type: ignore[arg-type]
            instrument_collection=collection,
            venue=Venue.OKX,
            logger=Logger(name="test"),
            consumer_buffer=queue,
        )
        payload = {
            "arg": {"channel": "bbo-tbt", "instId": "BTC-USDT-SWAP"},
            "action": "snapshot",
            "data": [
                {
                    "asks": [["30001.0", "1.5", "0", "3"]],
                    "bids": [["30000.0", "1.0", "0", "2"]],
                    "ts": "1597026383085",
                    "checksum": 123456789,
                }
            ],
        }
        await handler.decode_and_broadcast(1, msgspec.json.encode(payload))
        msg = queue.consume()
        assert isinstance(msg, OrderbookMsg)
        assert msg.is_bbo is True
        assert msg.is_snapshot is True


class TestOkxOrderbookHandler:
    """Layer 2: OKX orderbook handler behavior."""

    @pytest.mark.asyncio
    async def test_orderbook_decoding(self) -> None:
        """Test orderbook messages decode to OrderbookMsg with is_bbo=False."""
        queue = GenericRingBuffer(16)
        collection = make_collection()
        handler = OkxOrderbookHandler(
            connection=DummyConnection(),  # type: ignore[arg-type]
            instrument_collection=collection,
            venue=Venue.OKX,
            logger=Logger(name="test"),
            consumer_buffer=queue,
        )
        payload = {
            "arg": {"channel": "books5", "instId": "BTC-USDT-SWAP"},
            "action": "update",
            "data": [
                {
                    "asks": [
                        ["30001.0", "1.5", "0", "3"],
                        ["30002.0", "2.0", "0", "5"],
                    ],
                    "bids": [
                        ["30000.0", "1.0", "0", "2"],
                        ["29999.0", "3.0", "0", "4"],
                    ],
                    "ts": "1597026383085",
                    "checksum": 123456789,
                }
            ],
        }
        await handler.decode_and_broadcast(1, msgspec.json.encode(payload))
        msg = queue.consume()
        assert isinstance(msg, OrderbookMsg)
        assert msg.is_bbo is False
        assert msg.is_snapshot is False
        assert len(msg.asks) == 2
        assert len(msg.bids) == 2


class TestOkxTradesHandler:
    """Layer 2: OKX trades handler behavior."""

    @pytest.mark.asyncio
    async def test_trades_decoding(self) -> None:
        """Test trade messages decode to TradeMsg."""
        queue = GenericRingBuffer(16)
        collection = make_collection()
        handler = OkxTradesHandler(
            connection=DummyConnection(),  # type: ignore[arg-type]
            instrument_collection=collection,
            venue=Venue.OKX,
            logger=Logger(name="test"),
            consumer_buffer=queue,
        )
        payload = {
            "arg": {"channel": "trades", "instId": "BTC-USDT-SWAP"},
            "data": [
                {
                    "instId": "BTC-USDT-SWAP",
                    "tradeId": "123456789",
                    "px": "30000.5",
                    "sz": "1.0",
                    "side": "buy",
                    "ts": "1597026383085",
                }
            ],
        }
        await handler.decode_and_broadcast(1, msgspec.json.encode(payload))
        msg = queue.consume()
        assert isinstance(msg, TradeMsg)
        assert len(msg.trades) == 1
        assert msg.trades[0].price == 30000.5
        assert msg.trades[0].is_buy is True


class TestOkxPrivateHandler:
    """Layer 2: OKX private handler behavior."""

    def test_build_authentication_payload(self) -> None:
        """Test authentication payload format."""
        collection = make_collection()
        handler = OkxPrivateHandler(
            venue=Venue.OKX,
            logger=Logger(name="test"),
            connection=DummyConnection(),  # type: ignore[arg-type]
            instrument_collection=collection,
            consumer_buffer=GenericRingBuffer(1),
            api_key="test_key",
            api_secret="test_secret",
            passphrase="test_passphrase",
        )
        payload = handler.build_authentication_payload()
        decoded = msgspec.json.decode(payload)
        assert decoded["op"] == "login"
        assert len(decoded["args"]) == 1
        assert decoded["args"][0]["apiKey"] == "test_key"
        assert decoded["args"][0]["passphrase"] == "test_passphrase"
        assert "timestamp" in decoded["args"][0]
        assert "sign" in decoded["args"][0]

    def test_build_subscribe_payload(self) -> None:
        """Test private subscribe payload format."""
        collection = make_collection()
        handler = OkxPrivateHandler(
            venue=Venue.OKX,
            logger=Logger(name="test"),
            connection=DummyConnection(),  # type: ignore[arg-type]
            instrument_collection=collection,
            consumer_buffer=GenericRingBuffer(1),
            api_key="test_key",
            api_secret="test_secret",
            passphrase="test_passphrase",
        )
        payload = handler.build_subscribe_payload([], None)
        decoded = msgspec.json.decode(payload)
        assert decoded["op"] == "subscribe"
        channels = [arg["channel"] for arg in decoded["args"]]
        assert "orders" in channels
        assert "positions" in channels
        assert "account" in channels

    @pytest.mark.asyncio
    async def test_login_response_handling(self) -> None:
        """Test login response is properly handled."""
        collection = make_collection()
        handler = OkxPrivateHandler(
            venue=Venue.OKX,
            logger=Logger(name="test"),
            connection=DummyConnection(),  # type: ignore[arg-type]
            instrument_collection=collection,
            consumer_buffer=GenericRingBuffer(1),
            api_key="test_key",
            api_secret="test_secret",
            passphrase="test_passphrase",
        )
        login_response = b'{"event": "login", "code": "0", "msg": ""}'
        await handler.decode_and_broadcast(1, login_response)
        assert handler._is_authenticated is True

    @pytest.mark.asyncio
    async def test_login_failure_handling(self) -> None:
        """Test login failure is properly handled."""
        collection = make_collection()
        logger = Logger(name="test")
        error_calls: list[str] = []

        def _error(msg: str) -> None:
            error_calls.append(msg)

        logger.error = _error  # type: ignore[method-assign]

        handler = OkxPrivateHandler(
            venue=Venue.OKX,
            logger=logger,
            connection=DummyConnection(),  # type: ignore[arg-type]
            instrument_collection=collection,
            consumer_buffer=GenericRingBuffer(1),
            api_key="test_key",
            api_secret="test_secret",
            passphrase="test_passphrase",
        )
        login_response = b'{"event": "login", "code": "60001", "msg": "Invalid key"}'
        await handler.decode_and_broadcast(1, login_response)
        assert handler._is_authenticated is False
        assert len(error_calls) == 1
        assert "auth failed" in error_calls[0]
