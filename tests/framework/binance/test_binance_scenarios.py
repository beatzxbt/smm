"""Behavioral scenarios spanning Binance transports and exchange mapping."""

from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

from framework.base.stream.models import (
    AccountMsg,
    DataStreamEventMsg,
    ExecutionMsg,
    MarketDataStreamType,
    OrderbookMsg,
    PositionMsg,
    PrivateDataStreamType,
    TradeMsg,
)
from framework.base.trading.exchange import VenueEndpoints
from framework.base.trading.models import is_success
from framework.binance.stream.manager import (
    BinanceMarketStreamManager,
    BinancePrivateStreamManager,
)
from framework.binance.trading.exchange import BinanceExchange
from mm_toolbox.ringbuffer import GenericRingBuffer
from tests.framework.support import ScriptedExchangeServer, collect_messages


FIXTURE = Path(__file__).parents[1] / "fixtures" / "binance" / "public_session.jsonl"


def _endpoints(server: ScriptedExchangeServer) -> VenueEndpoints:
    return VenueEndpoints(
        http=server.http_url,
        trading_ws=server.ws_url,
        public_ws=server.ws_url,
        private_ws=server.ws_url,
        time=f"{server.http_url}/v1/time",
    )


@pytest.mark.asyncio
async def test_public_gateway_session_uses_real_http_client(test_logger) -> None:
    server = ScriptedExchangeServer()
    await server.start()
    server.load_jsonl(FIXTURE)
    exchange = BinanceExchange(test_logger, False, True, endpoints=_endpoints(server))
    try:
        instruments = await exchange.get_instrument_collection()
        assert is_success(instruments)
        instrument = instruments.data.instruments[0]
        orderbook, trades = await asyncio.gather(
            exchange.get_orderbook([instrument]),
            exchange.get_trades([instrument]),
        )
        assert is_success(orderbook) and len(orderbook.data[0].asks) == 2
        assert is_success(trades) and len(trades.data[0].trades) == 2
        assert len(server.http_requests) == 3
    finally:
        await exchange.close_clients()
        await server.close()


@pytest.mark.asyncio
async def test_sustained_public_feed_session(test_logger) -> None:
    server = ScriptedExchangeServer()
    await server.start()
    server.load_jsonl(FIXTURE)
    exchange = BinanceExchange(test_logger, False, True, endpoints=_endpoints(server))
    buffer = GenericRingBuffer(256)
    manager = await BinanceMarketStreamManager.create(exchange, test_logger, buffer)
    stream_types = {
        MarketDataStreamType.TOP_OF_ORDERBOOK,
        MarketDataStreamType.FULL_ORDERBOOK,
        MarketDataStreamType.TRADES,
    }
    try:
        instrument = manager.instrument_collection.instruments[0]
        await manager.start()
        await manager.subscribe([instrument], stream_types)
        await server.wait_for_ws_frames(3)
        for seq in range(1, 21):
            await server.send_to_subscribers(
                "btcusdt@bookTicker",
                {
                    "u": seq * 2 - 1,
                    "E": 1700000000000 + seq,
                    "T": 1700000000000 + seq,
                    "s": "BTCUSDT",
                    "b": "30000",
                    "B": "1",
                    "a": "30001",
                    "A": "2",
                },
            )
            await server.send_to_subscribers(
                "btcusdt@depth@100ms",
                {
                    "e": "depthUpdate",
                    "E": 1700000000000 + seq,
                    "T": 1700000000000 + seq,
                    "s": "BTCUSDT",
                    "U": seq * 2,
                    "u": seq * 2,
                    "pu": seq * 2 - 1,
                    "b": [["30000", "1"]],
                    "a": [["30001", "2"]],
                },
            )
            await server.send_to_subscribers(
                "btcusdt@trade",
                {
                    "e": "trade",
                    "E": 1700000000000 + seq,
                    "T": 1700000000000 + seq,
                    "s": "BTCUSDT",
                    "t": seq,
                    "p": "30000",
                    "q": "0.1",
                    "X": "MARKET",
                    "m": False,
                },
            )
        messages = await collect_messages(buffer, 44, settle_turns=20)
        orderbooks = [msg for msg in messages if isinstance(msg, OrderbookMsg)]
        assert 20 <= len(orderbooks) <= 40
        assert any(msg.is_bbo for msg in orderbooks)
        assert any(not msg.is_bbo for msg in orderbooks)
        assert sum(isinstance(msg, TradeMsg) for msg in messages) == 20
        assert sum(isinstance(msg, DataStreamEventMsg) for msg in messages) == 4
    finally:
        await manager.stop()
        await exchange.close_clients()
        await server.close()


@pytest.mark.asyncio
async def test_interleaved_private_feed_session(test_logger) -> None:
    server = ScriptedExchangeServer()
    await server.start()
    server.load_jsonl(FIXTURE)
    server.load_jsonl(
        Path(__file__).parents[1] / "fixtures" / "binance" / "private_session.jsonl"
    )
    exchange = BinanceExchange(test_logger, False, True, endpoints=_endpoints(server))
    exchange.load_secrets = True
    setattr(exchange.http_client, "key", "test-key")
    buffer = GenericRingBuffer(64)
    manager = await BinancePrivateStreamManager.create(exchange, test_logger, buffer)
    try:
        instrument = manager.instrument_collection.instruments[0]
        await manager.start()
        await manager.subscribe([instrument], set(PrivateDataStreamType))
        await server.wait_for_websockets(1)
        await server.push("order")
        await server.push("account")

        messages = await collect_messages(buffer, 8, settle_turns=20)
        assert sum(isinstance(msg, DataStreamEventMsg) for msg in messages) == 5
        assert any(isinstance(msg, ExecutionMsg) for msg in messages)
        assert any(isinstance(msg, PositionMsg) for msg in messages)
        assert any(isinstance(msg, AccountMsg) for msg in messages)
    finally:
        await manager.stop()
        await exchange.close_clients()
        await server.close()
