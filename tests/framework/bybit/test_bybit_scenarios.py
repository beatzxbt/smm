"""Behavioral scenarios spanning Bybit transports, adapters, and models."""

from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

from framework.base.common import ClientOrderId
from framework.base.stream.models import (
    AccountMsg,
    DataStreamEventMsg,
    ExecutionMsg,
    MarketDataStreamType,
    OrderMsg,
    OrderbookMsg,
    PositionMsg,
    PrivateDataStreamType,
    TickerMsg,
    TradeMsg,
)
from framework.base.trading.exchange import VenueEndpoints
from framework.base.trading.models import (
    AmendOrder,
    CancelOrder,
    CreateOrder,
    OrderTimeInForce,
    is_success,
)
from framework.bybit.stream.manager import (
    BybitMarketStreamManager,
    BybitPrivateStreamManager,
)
from framework.bybit.trading.exchange import BybitExchange
from mm_toolbox.ringbuffer import GenericRingBuffer
from tests.framework.support import ScriptedExchangeServer, collect_messages


FIXTURES = Path(__file__).parents[1] / "fixtures" / "bybit"


def _endpoints(server: ScriptedExchangeServer) -> VenueEndpoints:
    return VenueEndpoints(
        http=server.http_url,
        trading_ws=server.ws_url,
        public_ws=server.ws_url,
        private_ws=server.ws_url,
        time=f"{server.http_url}/v5/market/time",
    )


@pytest.mark.asyncio
async def test_public_gateway_session_uses_real_http_client(test_logger) -> None:
    server = ScriptedExchangeServer()
    await server.start()
    server.load_jsonl(FIXTURES / "public_session.jsonl")
    exchange = BybitExchange(
        logger=test_logger,
        load_secrets=False,
        endpoints=_endpoints(server),
    )
    try:
        instruments = await exchange.get_instrument_collection()
        assert is_success(instruments)
        instrument = instruments.data.instruments[0]

        ticker, orderbook, trades = await asyncio.gather(
            exchange.get_ticker([instrument]),
            exchange.get_orderbook([instrument]),
            exchange.get_trades([instrument]),
        )

        assert is_success(ticker) and ticker.data[0].mark_price == 30000.0
        assert is_success(orderbook) and len(orderbook.data[0].bids) == 2
        assert is_success(trades) and len(trades.data[0].trades) == 2
        assert {request["path"] for request in server.http_requests} == {
            "/v5/market/instruments-info",
            "/v5/market/tickers",
            "/v5/market/orderbook",
            "/v5/market/recent-trade",
        }
    finally:
        await exchange.close_clients()
        await server.close()


@pytest.mark.asyncio
async def test_sustained_public_feed_session(test_logger) -> None:
    server = ScriptedExchangeServer()
    await server.start()
    server.load_jsonl(FIXTURES / "public_session.jsonl")
    exchange = BybitExchange(
        logger=test_logger,
        load_secrets=False,
        endpoints=_endpoints(server),
    )
    buffer = GenericRingBuffer(512)
    manager = await BybitMarketStreamManager.create(exchange, test_logger, buffer)
    try:
        instrument = manager.instrument_collection.instruments[0]
        stream_types = set(MarketDataStreamType)
        await manager.start()
        await manager.subscribe([instrument], stream_types)
        await server.wait_for_ws_frames(4)
        assert server.subscriptions == {
            "tickers.BTCUSDT",
            "orderbook.1.BTCUSDT",
            "orderbook.1000.BTCUSDT",
            "publicTrade.BTCUSDT",
        }

        await server.send_to_subscribers("publicTrade.BTCUSDT", b"not-json")

        for seq in range(1, 26):
            ticker_data = {
                "symbol": "BTCUSDT",
                "markPrice": "30000.0",
            }
            if seq == 1:
                ticker_data.update(
                    {
                        "tickDirection": "PlusTick",
                        "price24hPcnt": "0.01",
                        "lastPrice": "30000.0",
                        "prevPrice24h": "29700.0",
                        "highPrice24h": "30500.0",
                        "lowPrice24h": "29500.0",
                        "prevPrice1h": "29900.0",
                        "indexPrice": "29995.0",
                        "openInterest": "1000.0",
                        "openInterestValue": "30000000.0",
                        "turnover24h": "1500000000.0",
                        "volume24h": "50000.0",
                        "fundingIntervalHour": "8",
                        "nextFundingTime": "1700003600000",
                        "fundingRate": "0.0001",
                    }
                )
            await server.send_to_subscribers(
                "tickers.BTCUSDT",
                {
                    "topic": "tickers.BTCUSDT",
                    "type": "snapshot" if seq == 1 else "delta",
                    "ts": 1700000000000 + seq,
                    "data": ticker_data,
                },
            )
            await server.send_to_subscribers(
                "orderbook.1.BTCUSDT",
                {
                    "topic": "orderbook.1.BTCUSDT",
                    "type": "snapshot",
                    "ts": 1700000000000 + seq,
                    "data": {
                        "s": "BTCUSDT",
                        "b": [["30000.0", "1.0"]],
                        "a": [["30001.0", "2.0"]],
                        "u": seq,
                        "seq": seq,
                    },
                },
            )
            await server.send_to_subscribers(
                "orderbook.1000.BTCUSDT",
                {
                    "topic": "orderbook.1000.BTCUSDT",
                    "type": "snapshot",
                    "ts": 1700000000000 + seq,
                    "data": {
                        "s": "BTCUSDT",
                        "b": [["29999.0", "3.0"], ["30000.0", "1.0"]],
                        "a": [["30001.0", "2.0"], ["30002.0", "4.0"]],
                        "u": seq,
                        "seq": seq,
                    },
                },
            )
            await server.send_to_subscribers(
                "publicTrade.BTCUSDT",
                {
                    "topic": "publicTrade.BTCUSDT",
                    "type": "snapshot",
                    "ts": 1700000000000 + seq,
                    "data": [
                        {
                            "T": 1700000000000 + seq,
                            "s": "BTCUSDT",
                            "S": "Buy",
                            "v": "0.1",
                            "p": "30000.0",
                            "i": f"trade-{seq}",
                            "seq": seq,
                        }
                    ],
                },
            )

        await server.send_to_subscribers(
            "publicTrade.BTCUSDT",
            {
                "topic": "publicTrade.BTCUSDT",
                "type": "snapshot",
                "ts": 1700000000100,
                "data": [
                    {
                        "T": 1700000000025,
                        "s": "BTCUSDT",
                        "S": "Buy",
                        "v": "0.1",
                        "p": "30000.0",
                        "i": "trade-25",
                        "seq": 25,
                    }
                ],
            },
        )

        messages = await collect_messages(buffer, 105)
        assert sum(isinstance(msg, TickerMsg) for msg in messages) == 25
        assert sum(isinstance(msg, OrderbookMsg) for msg in messages) == 50
        assert sum(isinstance(msg, TradeMsg) for msg in messages) == 25
        assert sum(isinstance(msg, DataStreamEventMsg) for msg in messages) == 5

        await manager.unsubscribe([instrument], stream_types)
        await manager.stop()
        assert not manager.is_running
    finally:
        await manager.stop()
        await exchange.close_clients()
        await server.close()


@pytest.mark.asyncio
async def test_complete_order_lifecycle_uses_real_websocket_client(test_logger) -> None:
    server = ScriptedExchangeServer()
    await server.start()
    server.load_jsonl(FIXTURES / "public_session.jsonl")
    server.load_jsonl(FIXTURES / "order_lifecycle.jsonl")
    exchange = BybitExchange(
        logger=test_logger,
        load_secrets=False,
        endpoints=_endpoints(server),
    )
    exchange.load_secrets = True
    exchange.http_client.load_secrets = True
    exchange.ws_client.load_secrets = True
    setattr(exchange.http_client, "key", "test-key")
    setattr(exchange.ws_client, "key", "test-key")
    setattr(exchange.http_client, "secret", "test-secret")
    setattr(exchange.ws_client, "secret", "test-secret")
    try:
        instruments = await exchange.get_instrument_collection()
        assert is_success(instruments)
        instrument = instruments.data.instruments[0]
        await exchange.connect_ws_client()

        created = await exchange.create_order(
            CreateOrder(
                instrument=instrument,
                size=1.0,
                is_buy=True,
                price=30000.0,
                is_maker=True,
                tif=OrderTimeInForce.GTC,
                reduce_only=False,
                client_order_id=ClientOrderId("client-1"),
            )
        )
        assert is_success(created) and created.data.order_id == "order-1"

        amended = await exchange.amend_order(
            AmendOrder(
                instrument=instrument,
                size=2.0,
                price=30010.0,
                order_id=created.data.order_id,
            )
        )
        assert is_success(amended) and amended.data.order_id == "order-1"

        cancelled = await exchange.cancel_order(
            CancelOrder(instrument=instrument, order_id=amended.data.order_id)
        )
        assert is_success(cancelled) and cancelled.data.order_id == "order-1"
        assert [
            frame.get("op") for frame in server.ws_frames if isinstance(frame, dict)
        ] == ["auth", "order.create", "order.amend", "order.cancel"]
    finally:
        await exchange.close_clients()
        await server.close()


@pytest.mark.asyncio
async def test_gateway_recovers_after_exchange_rejection(test_logger) -> None:
    server = ScriptedExchangeServer()
    await server.start()
    server.load_jsonl(FIXTURES / "failure_recovery.jsonl")
    server.load_jsonl(FIXTURES / "public_session.jsonl")
    exchange = BybitExchange(test_logger, False, endpoints=_endpoints(server))
    try:
        instruments = await exchange.get_instrument_collection()
        assert is_success(instruments)
        instrument = instruments.data.instruments[0]

        rejected = await exchange.get_ticker([instrument])
        recovered = await exchange.get_ticker([instrument])

        assert not is_success(rejected)
        assert "invalid request" in rejected.err_msg
        assert is_success(recovered)
        assert recovered.data[0].mark_price == 30000.0
    finally:
        await exchange.close_clients()
        await server.close()


@pytest.mark.asyncio
async def test_interleaved_private_feed_session(test_logger) -> None:
    server = ScriptedExchangeServer()
    await server.start()
    server.load_jsonl(FIXTURES / "public_session.jsonl")
    server.load_jsonl(FIXTURES / "private_session.jsonl")
    exchange = BybitExchange(test_logger, False, endpoints=_endpoints(server))
    setattr(exchange.http_client, "key", "test-key")
    setattr(exchange.http_client, "secret", "test-secret")
    buffer = GenericRingBuffer(64)
    manager = await BybitPrivateStreamManager.create(exchange, test_logger, buffer)
    try:
        instrument = manager.instrument_collection.instruments[0]
        stream_types = set(PrivateDataStreamType)
        await manager.start()
        await manager.subscribe([instrument], stream_types)
        await server.wait_for_ws_frames(2)
        assert server.subscriptions == {"order", "position", "execution", "wallet"}

        await server.push("order")
        await server.push("execution")
        await server.push("position")
        await server.push("wallet")

        messages = await collect_messages(buffer, 9)
        assert sum(isinstance(msg, DataStreamEventMsg) for msg in messages) == 5
        assert sum(isinstance(msg, OrderMsg) for msg in messages) == 1
        assert sum(isinstance(msg, ExecutionMsg) for msg in messages) == 1
        assert sum(isinstance(msg, PositionMsg) for msg in messages) == 1
        assert sum(isinstance(msg, AccountMsg) for msg in messages) == 1
        order = next(msg for msg in messages if isinstance(msg, OrderMsg))
        execution = next(msg for msg in messages if isinstance(msg, ExecutionMsg))
        position = next(msg for msg in messages if isinstance(msg, PositionMsg))
        account = next(msg for msg in messages if isinstance(msg, AccountMsg))
        assert order.orders[0].order_id == "order-1"
        assert execution.executions[0].order_id == "order-1"
        assert position.size == 1.0 and position.is_long
        assert next(iter(account.balances.values())).amount == 10000.0
    finally:
        await manager.stop()
        await exchange.close_clients()
        await server.close()


@pytest.mark.asyncio
async def test_feed_reconnects_and_resubscribes(test_logger) -> None:
    server = ScriptedExchangeServer()
    await server.start()
    server.load_jsonl(FIXTURES / "public_session.jsonl")
    exchange = BybitExchange(test_logger, False, endpoints=_endpoints(server))
    buffer = GenericRingBuffer(32)
    manager = await BybitMarketStreamManager.create(exchange, test_logger, buffer)
    stream_types = {MarketDataStreamType.TOP_OF_ORDERBOOK}

    def book(seq: int) -> dict:
        return {
            "topic": "orderbook.1.BTCUSDT",
            "type": "snapshot",
            "ts": 1700000000000 + seq,
            "data": {
                "s": "BTCUSDT",
                "b": [["30000.0", "1.0"]],
                "a": [["30001.0", "2.0"]],
                "u": seq,
                "seq": seq,
            },
        }

    try:
        instrument = manager.instrument_collection.instruments[0]
        await manager.start()
        await manager.subscribe([instrument], stream_types)
        await server.wait_for_ws_frames(1)
        assert server.subscriptions == {"orderbook.1.BTCUSDT"}
        await server.send_to_subscribers("orderbook.1.BTCUSDT", book(1))
        initial = await collect_messages(buffer, 3)
        initial_books = [msg for msg in initial if isinstance(msg, OrderbookMsg)]
        assert len(initial_books) == 1

        await server.disconnect_websockets()
        await server.wait_for_ws_frames(2, timeout_s=3.0)
        await server.send_to_subscribers("orderbook.1.BTCUSDT", book(2))
        recovered = await collect_messages(buffer, 1, timeout_s=2.0)
        assert isinstance(recovered[0], OrderbookMsg)
        assert recovered[0].moments.exch_time_ns > initial_books[0].moments.exch_time_ns
    finally:
        await manager.stop()
        await exchange.close_clients()
        await server.close()
