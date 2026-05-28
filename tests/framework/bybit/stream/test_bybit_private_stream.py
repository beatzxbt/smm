"""Tests for framework.bybit.stream.handlers.BybitPrivateHandler."""

from __future__ import annotations


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
from framework.base.stream.connection import WebSocketConnection
from framework.base.stream.models import AccountMsg, ExecutionMsg, OrderMsg, PositionMsg
from framework.bybit.stream.handlers import BybitPrivateHandler
from mm_toolbox.logging.standard import Logger
from mm_toolbox.ringbuffer import GenericRingBuffer


def make_instrument() -> Instrument:
    """Create a standard Bybit instrument for tests.

    Returns:
        Instrument: BTCUSDT perpetual contract.
    """
    return Instrument(
        venue=Venue.BYBIT,
        symbol=Symbol("BTCUSDT"),
        base=Asset("BTC"),
        quote=Asset("USDT"),
        code=0,
        instrument_type=InstrumentType.PERPETUAL,
        tick_size=0.01,
        lot_size=0.001,
    )


class TestBybitPrivateStream:
    """Layer 3: Private stream message handling."""

    @pytest.mark.asyncio
    async def test_stream_order_broadcasts_order_msg(self, bybit_payloads) -> None:
        """Test order stream broadcasts OrderMsg.

        Args:
            bybit_payloads: Payload factory namespace fixture.
        """
        queue = GenericRingBuffer(16)
        logger = Logger(name="test")
        instrument = make_instrument()
        instrument_collection = InstrumentCollection([instrument])
        handler = BybitPrivateHandler(
            venue=instrument.venue,
            logger=logger,
            connection=WebSocketConnection("wss://example.test", logger),
            instrument_collection=instrument_collection,
            consumer_buffer=queue,
            api_key="k",
            api_secret="s",
        )

        payload = bybit_payloads.make_bybit_private_order_message()
        await handler.decode_and_broadcast(1, msgspec.json.encode(payload))

        msg = queue.consume()
        assert isinstance(msg, OrderMsg)

    @pytest.mark.asyncio
    async def test_stream_position_broadcasts_position_msg(
        self, bybit_payloads
    ) -> None:
        """Test position stream broadcasts PositionMsg.

        Args:
            bybit_payloads: Payload factory namespace fixture.
        """
        queue = GenericRingBuffer(16)
        logger = Logger(name="test")
        instrument = make_instrument()
        instrument_collection = InstrumentCollection([instrument])
        handler = BybitPrivateHandler(
            venue=instrument.venue,
            logger=logger,
            connection=WebSocketConnection("wss://example.test", logger),
            instrument_collection=instrument_collection,
            consumer_buffer=queue,
            api_key="k",
            api_secret="s",
        )

        payload = bybit_payloads.make_bybit_private_position_message()
        await handler.decode_and_broadcast(1, msgspec.json.encode(payload))

        msg = queue.consume()
        assert isinstance(msg, PositionMsg)

    @pytest.mark.asyncio
    async def test_stream_execution_broadcasts_execution_msg(
        self, bybit_payloads
    ) -> None:
        """Test execution stream broadcasts ExecutionMsg.

        Args:
            bybit_payloads: Payload factory namespace fixture.
        """
        queue = GenericRingBuffer(16)
        logger = Logger(name="test")
        instrument = make_instrument()
        instrument_collection = InstrumentCollection([instrument])
        handler = BybitPrivateHandler(
            venue=instrument.venue,
            logger=logger,
            connection=WebSocketConnection("wss://example.test", logger),
            instrument_collection=instrument_collection,
            consumer_buffer=queue,
            api_key="k",
            api_secret="s",
        )

        payload = bybit_payloads.make_bybit_private_execution_message()
        await handler.decode_and_broadcast(1, msgspec.json.encode(payload))

        msg = queue.consume()
        assert isinstance(msg, ExecutionMsg)

    @pytest.mark.asyncio
    async def test_stream_account_broadcasts_account_msg(self, bybit_payloads) -> None:
        """Test wallet stream broadcasts AccountMsg.

        Args:
            bybit_payloads: Payload factory namespace fixture.
        """
        queue = GenericRingBuffer(16)
        logger = Logger(name="test")
        instrument = make_instrument()
        instrument_collection = InstrumentCollection([instrument])
        handler = BybitPrivateHandler(
            venue=instrument.venue,
            logger=logger,
            connection=WebSocketConnection("wss://example.test", logger),
            instrument_collection=instrument_collection,
            consumer_buffer=queue,
            api_key="k",
            api_secret="s",
        )

        payload = bybit_payloads.make_bybit_private_wallet_message()
        await handler.decode_and_broadcast(1, msgspec.json.encode(payload))

        msg = queue.consume()
        assert isinstance(msg, AccountMsg)
