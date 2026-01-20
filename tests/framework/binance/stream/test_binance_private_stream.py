"""Tests for framework.binance.stream.private.BinancePrivateDataStream."""

from __future__ import annotations

import asyncio

import msgspec
import pytest

from framework.base.common import Instrument, InstrumentType, Venue
from framework.base.stream.models import (
    AccountMsg,
    ExecutionMsg,
    PositionMsg,
    PrivateDataStreamType,
)
from framework.binance.stream.private import BinancePrivateDataStream
from framework.binance.trading.exchange import ENDPOINT_POST_LISTEN_KEY
from mm_toolbox.logging.standard import Logger


class TestBinancePrivateStreamRouting:
    """Layer 3: Private stream message routing."""

    @pytest.mark.asyncio
    async def test_routes_order_and_account_messages(
        self,
        binance_exchange_mocked,
        binance_http_router: dict,
        binance_payloads,
        monkeypatch,
    ) -> None:
        """Test ORDER_TRADE_UPDATE and ACCOUNT_UPDATE routing.

        Args:
            binance_exchange_mocked: Binance exchange fixture with stubbed clients.
            binance_http_router: HTTP router fixture for response control.
            binance_payloads: Payload builder namespace for Binance responses.
            monkeypatch: Pytest monkeypatch fixture.
        """
        binance_http_router["responses"][ENDPOINT_POST_LISTEN_KEY] = (
            binance_payloads.make_binance_listen_key_response("listen_key")
        )

        order_update = {
            "e": "ORDER_TRADE_UPDATE",
            "E": 1,
            "T": 2,
            "o": {
                "s": "BTCUSDT",
                "X": "TRADE",
                "T": 2,
                "i": 1,
                "L": "30000",
                "S": "BUY",
                "l": "0.1",
                "m": True,
                "n": "0.01",
                "c": "client_1",
            },
        }
        account_update = {
            "e": "ACCOUNT_UPDATE",
            "E": 1,
            "T": 2,
            "a": {
                "B": [{"a": "USDT", "wb": "1000.0"}],
                "P": [{"s": "BTCUSDT", "pa": "1.0", "ep": "30000"}],
                "m": "1.0",
                "mm": "0.5",
                "up": "10.0",
            },
        }
        encoded_messages = [
            msgspec.json.encode(order_update),
            msgspec.json.encode(account_update),
        ]

        class FakeWsSingle:
            """Async iterable yielding a fixed set of websocket messages."""

            def __init__(self, _config) -> None:
                """Initialize the fake websocket iterator.

                Args:
                    _config: Websocket configuration (unused).
                """
                self._messages = list(encoded_messages)

            async def __aenter__(self):
                """Enter the async context manager.

                Returns:
                    FakeWsSingle: Instance for async iteration.
                """
                return self

            async def __aexit__(self, exc_type, exc, tb):
                """Exit the async context manager.

                Args:
                    exc_type: Exception type, if raised.
                    exc: Exception instance, if raised.
                    tb: Traceback, if raised.

                Returns:
                    bool: False to propagate exceptions.
                """
                return False

            def __aiter__(self):
                """Return async iterator.

                Returns:
                    FakeWsSingle: Iterator instance.
                """
                return self

            async def __anext__(self):
                """Return next websocket message.

                Returns:
                    bytes: Encoded websocket message payload.

                Raises:
                    StopAsyncIteration: When messages are exhausted.
                """
                if not self._messages:
                    raise StopAsyncIteration
                return self._messages.pop(0)

        async def _fast_heartbeat(self, _stream_type, _interval_s: int = 60) -> None:
            """No-op heartbeat to keep the test bounded.

            Args:
                _stream_type: Stream type placeholder.
                _interval_s: Interval placeholder.
            """
            return None

        monkeypatch.setattr("framework.binance.stream.private.WsSingle", FakeWsSingle)
        monkeypatch.setattr(
            BinancePrivateDataStream,
            "broadcast_heartbeat",
            _fast_heartbeat,
        )

        queue = asyncio.Queue()
        stream = BinancePrivateDataStream(
            exchange_client=binance_exchange_mocked,
            logger=Logger(name="test"),
            consumer_queues=[queue],
        )
        instruments = [
            Instrument(
                venue=Venue.BINANCE_USDM,
                symbol="BTCUSDT",
                base="BTC",
                quote="USDT",
                code=0,
                instrument_type=InstrumentType.PERPETUAL,
            )
        ]

        await stream.run(
            instruments=instruments,
            stream_types={
                PrivateDataStreamType.ORDER,
                PrivateDataStreamType.EXECUTION,
                PrivateDataStreamType.POSITION,
                PrivateDataStreamType.ACCOUNT,
            },
        )

        received = []
        while not queue.empty():
            received.append(queue.get_nowait())

        assert len(received) >= 3
        assert any(isinstance(msg, ExecutionMsg) for msg in received)
        assert any(isinstance(msg, PositionMsg) for msg in received)
        assert any(isinstance(msg, AccountMsg) for msg in received)
