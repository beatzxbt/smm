"""Behavioral scenarios spanning OKX transports and exchange mapping."""

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
    TradeMsg,
    TickerMsg,
)
from framework.base.trading.exchange import VenueEndpoints
from framework.base.trading.models import (
    AmendOrder,
    CancelOrder,
    CreateOrder,
    OrderTimeInForce,
    is_success,
)
from framework.okx.stream.manager import OkxMarketStreamManager, OkxPrivateStreamManager
from framework.okx.trading.exchange import OkxExchange
from mm_toolbox.ringbuffer import GenericRingBuffer
from tests.framework.support import ScriptedExchangeServer, collect_messages


FIXTURE = Path(__file__).parents[1] / "fixtures" / "okx" / "public_session.jsonl"


def _endpoints(server: ScriptedExchangeServer) -> VenueEndpoints:
    return VenueEndpoints(
        http=server.http_url,
        trading_ws=server.ws_url,
        public_ws=server.ws_url,
        private_ws=server.ws_url,
        time=f"{server.http_url}/api/v5/public/time",
    )


@pytest.mark.asyncio
async def test_public_gateway_session_uses_real_http_client(test_logger) -> None:
    server = ScriptedExchangeServer()
    await server.start()
    server.load_jsonl(FIXTURE)
    exchange = OkxExchange(test_logger, False, endpoints=_endpoints(server))
    try:
        instruments = await exchange.get_instrument_collection()
        assert is_success(instruments)
        instrument = instruments.data.instruments[0]
        ticker, orderbook = await asyncio.gather(
            exchange.get_ticker([instrument]),
            exchange.get_orderbook([instrument]),
        )
        assert is_success(ticker) and ticker.data[0].mark_price == 30000.0
        assert is_success(orderbook) and len(orderbook.data[0].bids) == 2
        assert len(server.http_requests) == 7
    finally:
        await exchange.close_clients()
        await server.close()


@pytest.mark.asyncio
async def test_sustained_public_feed_session(test_logger) -> None:
    server = ScriptedExchangeServer()
    await server.start()
    server.load_jsonl(FIXTURE)
    exchange = OkxExchange(test_logger, False, endpoints=_endpoints(server))
    buffer = GenericRingBuffer(256)
    manager = await OkxMarketStreamManager.create(exchange, test_logger, buffer)
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
        for seq in range(1, 16):
            book = {
                "action": "snapshot",
                "data": [
                    {
                        "asks": [["30001", "2", "0", "1"]],
                        "bids": [["30000", "1", "0", "1"]],
                        "ts": str(1700000000000 + seq),
                    }
                ],
            }
            await server.send_to_subscribers(
                "bbo-tbt:BTC-USDT-SWAP",
                {
                    "arg": {"channel": "bbo-tbt", "instId": "BTC-USDT-SWAP"},
                    **book,
                },
            )
            await server.send_to_subscribers(
                "books5:BTC-USDT-SWAP",
                {
                    "arg": {"channel": "books5", "instId": "BTC-USDT-SWAP"},
                    **book,
                },
            )
            await server.send_to_subscribers(
                "trades:BTC-USDT-SWAP",
                {
                    "arg": {
                        "channel": "trades",
                        "instId": "BTC-USDT-SWAP",
                    },
                    "data": [
                        {
                            "instId": "BTC-USDT-SWAP",
                            "tradeId": str(seq),
                            "px": "30000",
                            "sz": "0.1",
                            "side": "buy",
                            "ts": str(1700000000000 + seq),
                        }
                    ],
                },
            )
        messages = await collect_messages(buffer, 49)
        assert sum(isinstance(msg, OrderbookMsg) for msg in messages) == 30
        assert sum(isinstance(msg, TradeMsg) for msg in messages) == 15
        assert sum(isinstance(msg, DataStreamEventMsg) for msg in messages) == 4
    finally:
        await manager.stop()
        await exchange.close_clients()
        await server.close()


@pytest.mark.asyncio
async def test_ticker_composes_distinct_okx_reference_channels(test_logger) -> None:
    server = ScriptedExchangeServer()
    await server.start()
    server.load_jsonl(FIXTURE)
    exchange = OkxExchange(test_logger, False, endpoints=_endpoints(server))
    buffer = GenericRingBuffer(32)
    manager = await OkxMarketStreamManager.create(exchange, test_logger, buffer)
    try:
        instrument = manager.instrument_collection.instruments[0]
        await manager.start()
        await manager.subscribe([instrument], {MarketDataStreamType.TICKER})
        await server.wait_for_ws_frames(1)
        expected = {
            "tickers:BTC-USDT-SWAP",
            "mark-price:BTC-USDT-SWAP",
            "funding-rate:BTC-USDT-SWAP",
            "open-interest:BTC-USDT-SWAP",
            "index-tickers:BTC-USDT",
        }
        assert server.subscriptions == expected

        pushes = [
            (
                "tickers:BTC-USDT-SWAP",
                "tickers",
                "BTC-USDT-SWAP",
                {
                    "last": "30000",
                    "open24h": "29500",
                    "vol24h": "50000",
                    "ts": "1700000000000",
                },
            ),
            (
                "mark-price:BTC-USDT-SWAP",
                "mark-price",
                "BTC-USDT-SWAP",
                {"markPx": "30000", "ts": "1700000000001"},
            ),
            (
                "funding-rate:BTC-USDT-SWAP",
                "funding-rate",
                "BTC-USDT-SWAP",
                {
                    "fundingRate": "0.0001",
                    "fundingTime": "1700000000000",
                    "nextFundingTime": "1700028800000",
                },
            ),
            (
                "open-interest:BTC-USDT-SWAP",
                "open-interest",
                "BTC-USDT-SWAP",
                {"oi": "1000", "ts": "1700000000002"},
            ),
            (
                "index-tickers:BTC-USDT",
                "index-tickers",
                "BTC-USDT",
                {"idxPx": "29995", "ts": "1700000000003"},
            ),
        ]
        for subscription, channel, inst_id, data in pushes:
            await server.send_to_subscribers(
                subscription,
                {
                    "arg": {"channel": channel, "instId": inst_id},
                    "data": [{"instId": inst_id, **data}],
                },
            )

        messages = await collect_messages(buffer, 3)
        ticker = next(msg for msg in messages if isinstance(msg, TickerMsg))
        assert ticker.is_snapshot
        assert ticker.mark_price == 30000.0
        assert ticker.index_price == 29995.0
        assert ticker.funding_period_min == 480
    finally:
        await manager.stop()
        await exchange.close_clients()
        await server.close()


@pytest.mark.asyncio
async def test_complete_order_lifecycle_uses_real_websocket_client(test_logger) -> None:
    server = ScriptedExchangeServer()
    await server.start()
    server.load_jsonl(FIXTURE)
    server.load_jsonl(
        Path(__file__).parents[1] / "fixtures" / "okx" / "order_lifecycle.jsonl"
    )
    exchange = OkxExchange(test_logger, False, endpoints=_endpoints(server))
    exchange.load_secrets = True
    exchange.http_client.load_secrets = True
    exchange.ws_client.load_secrets = True
    for client in (exchange.http_client, exchange.ws_client):
        setattr(client, "key", "test-key")
        setattr(client, "secret", "test-secret")
        setattr(client, "passphrase", "test-passphrase")
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
        ] == ["login", "order", "amend-order", "cancel-order"]
        requests = [frame for frame in server.ws_frames if frame.get("op") != "login"]
        assert all(request["args"][0]["instIdCode"] == 1001 for request in requests)
    finally:
        await exchange.close_clients()
        await server.close()


@pytest.mark.asyncio
async def test_interleaved_private_feed_session(test_logger) -> None:
    server = ScriptedExchangeServer()
    await server.start()
    server.load_jsonl(FIXTURE)
    server.load_jsonl(
        Path(__file__).parents[1] / "fixtures" / "okx" / "private_session.jsonl"
    )
    exchange = OkxExchange(test_logger, False, endpoints=_endpoints(server))
    for client in (exchange.http_client, exchange.ws_client):
        setattr(client, "key", "test-key")
        setattr(client, "secret", "test-secret")
        setattr(client, "passphrase", "test-passphrase")
    buffer = GenericRingBuffer(64)
    manager = await OkxPrivateStreamManager.create(exchange, test_logger, buffer)
    try:
        instrument = manager.instrument_collection.instruments[0]
        await manager.start()
        await manager.subscribe([instrument], set(PrivateDataStreamType))
        await server.wait_for_ws_frames(2)
        await server.push("order")
        await server.push("position")
        await server.push("account")

        messages = await collect_messages(buffer, 9)
        assert sum(isinstance(msg, DataStreamEventMsg) for msg in messages) == 5
        assert any(isinstance(msg, OrderMsg) for msg in messages)
        assert any(isinstance(msg, ExecutionMsg) for msg in messages)
        assert any(isinstance(msg, PositionMsg) for msg in messages)
        assert any(isinstance(msg, AccountMsg) for msg in messages)
    finally:
        await manager.stop()
        await exchange.close_clients()
        await server.close()
