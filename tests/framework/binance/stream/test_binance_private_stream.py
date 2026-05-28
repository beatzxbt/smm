"""Tests for framework.binance.stream.handlers.BinancePrivateHandler."""

from __future__ import annotations


import msgspec
import pytest

from framework.base.common import InstrumentCollection
from framework.base.stream.connection import WebSocketConnection
from framework.base.stream.models import AccountMsg, ExecutionMsg, PositionMsg
from framework.binance.stream.handlers import BinancePrivateHandler
from framework.binance.trading.exchange import BinanceExchange
from mm_toolbox.logging.standard import Logger
from mm_toolbox.ringbuffer import GenericRingBuffer


class TestBinancePrivateStreamRouting:
    """Layer 3: Private stream message routing."""

    @pytest.mark.asyncio
    async def test_routes_order_and_account_messages(
        self,
        binance_instrument,
    ) -> None:
        """Test ORDER_TRADE_UPDATE and ACCOUNT_UPDATE routing.

        Args:
            binance_instrument: Binance instrument fixture.
        """
        logger = Logger(name="test")
        queue = GenericRingBuffer(16)
        instrument_collection = InstrumentCollection([binance_instrument])
        exchange = BinanceExchange(
            logger=logger,
            load_secrets=False,
            is_usd_margined=True,
        )
        handler = BinancePrivateHandler(
            venue=binance_instrument.venue,
            logger=logger,
            connection=WebSocketConnection("wss://example.test", logger),
            instrument_collection=instrument_collection,
            consumer_buffer=queue,
            exchange=exchange,
            listen_key="listen_key",
        )

        order_update = {
            "e": "ORDER_TRADE_UPDATE",
            "E": 1,
            "T": 2,
            "o": {
                "s": "BTCUSDT",
                "c": "client_1",
                "S": "BUY",
                "o": "LIMIT",
                "f": "GTC",
                "q": "1.0",
                "p": "30000",
                "ap": "30000",
                "z": "0.1",
                "N": "USDT",
                "t": 1,
                "ps": "BOTH",
                "X": "TRADE",
                "T": 2,
                "i": 1,
                "L": "30000",
                "l": "0.1",
                "m": True,
                "n": "0.01",
                "R": False,
            },
        }
        account_update = {
            "e": "ACCOUNT_UPDATE",
            "E": 1,
            "T": 2,
            "a": {
                "B": [{"a": "USDT", "wb": "1000.0", "cw": "1000.0"}],
                "P": [
                    {
                        "s": "BTCUSDT",
                        "pa": "1.0",
                        "ep": "30000",
                        "cr": "0.0",
                        "up": "10.0",
                        "ps": "BOTH",
                    }
                ],
                "m": "1.0",
                "mm": "0.5",
                "u": "10.0",
                "up": "10.0",
            },
        }

        await handler.decode_and_broadcast(
            1,
            msgspec.json.encode(order_update),
        )
        await handler.decode_and_broadcast(
            1,
            msgspec.json.encode(account_update),
        )

        received = []
        while not queue.is_empty():
            received.append(queue.consume())

        assert any(isinstance(msg, ExecutionMsg) for msg in received)
        assert any(isinstance(msg, PositionMsg) for msg in received)
        assert any(isinstance(msg, AccountMsg) for msg in received)
