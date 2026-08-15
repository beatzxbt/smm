"""Trader-level behavioral scenarios for the plain and stinky strategies.

Scenarios enter at the producer buffer (messages flow through the real
pricing/risk/OMS stack) and assert the exact order traffic emitted on the
scripted exchange wire.
"""

from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

from framework.base.stream.models import ALL_MARKET_DATA_STREAM_TYPES, OrderbookMsg
from framework.bybit.stream.manager import (
    BybitMarketStreamManager,
    BybitPrivateStreamManager,
)
from mm_toolbox.ringbuffer import GenericRingBuffer
from smm.config import AppConfig
from smm.traders.plain.trader import PlainTrader
from smm.traders.stinky.trader import StinkyTrader
from tests.smm.support import (
    expected_plain_prices,
    expected_stinky_prices,
    fresh_recv_ns,
    make_execution_msg,
    make_heartbeat,
    make_order_msg,
    make_orderbook,
    make_position,
    op_args,
    op_count,
)

BYBIT_FIXTURES = Path(__file__).parents[1] / "framework" / "fixtures" / "bybit"

NOW_S = 1_700_000_000.0
NOW_MS = int(NOW_S * 1000)
NOW_NS = int(NOW_S * 1_000_000_000)


def _plain_prices(mid: float) -> list[tuple[str, str]]:
    """Return expected (bid, ask) price strings for the plain ladder."""
    return [(str(bid), str(ask)) for bid, ask in expected_plain_prices(mid, 5, 15.0)]


def _plain_flat_config() -> AppConfig:
    """Build a plain config without an inventory spread ladder.

    Keeps order distances inside the risk limit when inventory is at full
    utilization, isolating the inventory-bias cancel behavior.

    Returns:
        AppConfig: Plain trader configuration with no spread ladder.
    """
    from framework.base.common import Symbol, Venue
    from smm.config import (
        CoreConfig,
        OmsBudgetConfig,
        OmsConfig,
        PricingConfig,
        RateWindow,
        RiskConfig,
        TraderId,
    )

    budget = OmsBudgetConfig(limit=1000, per=RateWindow.SEC)
    return AppConfig(
        core=CoreConfig(
            venue=Venue.BYBIT,
            symbol=Symbol("BTCUSDT"),
            trader=TraderId.PLAIN,
        ),
        pricing=PricingConfig(
            levels=5,
            base_spread_bps=15.0,
            max_inventory_quote=300_000.0,
            inventory_spread_ladder=[],
        ),
        risk=RiskConfig(max_inventory_quote=300_000.0),
        oms=OmsConfig(create=budget, amend=budget, cancel=budget),
    )


def _stinky_prices(mid: float) -> list[tuple[str, str]]:
    """Return expected (bid, ask) price strings for the stinky ladder."""
    return [
        (str(bid), str(ask)) for bid, ask in expected_stinky_prices(mid, 6, 50.0, 250.0)
    ]


def _seed_responses(server, op: str, count: int, ret_code: int = 0) -> None:
    """Queue success (or failure) wire responses for an operation."""
    for _ in range(count):
        server.add_ws_response(
            op,
            {
                "retCode": ret_code,
                "retMsg": "OK",
                "op": op,
                "result": {"orderId": "order-1", "orderLinkId": "client-1"},
            },
        )


async def _connect(server, exchange) -> None:
    """Open the exchange WebSocket client against the scripted server."""
    await exchange.connect_ws_client()


async def _await_book(buffer) -> OrderbookMsg:
    """Consume the next orderbook message from the producer buffer.

    Stream lifecycle events share the buffer, so skip them until the
    expected market data arrives.

    Args:
        buffer: Producer ring buffer fed by the stream manager.

    Returns:
        OrderbookMsg: Next orderbook message from the buffer.
    """
    async with asyncio.timeout(2.0):
        while True:
            while not buffer.is_empty():
                message = buffer.consume()
                if isinstance(message, OrderbookMsg):
                    return message
            await asyncio.sleep(0)


async def _populate_live_orders(trader, prices: list[tuple[str, float, bool]]) -> None:
    """Feed order messages so the OMS tracks the placed quotes as live."""
    for cloid, price, is_buy in prices:
        await trader.consume_msg(
            make_order_msg(
                trader.instrument,
                cloid=cloid,
                price=price,
                is_buy=is_buy,
                recv_ns=fresh_recv_ns(),
            )
        )


def _plain_live_prices() -> list[tuple[str, float, bool]]:
    """Return (cloid, price, is_buy) triples for a placed plain ladder."""
    pairs = []
    for level, (bid, ask) in enumerate(_plain_prices(30_000.0)):
        pairs.append((f"PLAIN{level:02d}B", float(bid), True))
        pairs.append((f"PLAIN{level:02d}S", float(ask), False))
    return pairs


class TestTraderBoot:
    """Verify the trader wiring works through real stream components."""

    @pytest.mark.asyncio
    async def test_full_pipeline_consumes_stream_and_places_orders(
        self,
        scripted_exchange,
        make_trader,
        plain_one_level_config,
        test_logger,
    ) -> None:
        server, exchange = scripted_exchange
        server.load_jsonl(BYBIT_FIXTURES / "public_session.jsonl")
        server.load_jsonl(BYBIT_FIXTURES / "order_lifecycle.jsonl")
        _seed_responses(server, "order.create", 1)

        collection = await exchange.get_instrument_collection()
        instrument = collection.data.instruments[0]

        buffer = GenericRingBuffer(512)
        market_data = await BybitMarketStreamManager.create(
            exchange, test_logger, buffer
        )
        private_data = await BybitPrivateStreamManager.create(
            exchange, test_logger, buffer
        )
        trader = await make_trader(
            server,
            exchange,
            PlainTrader,
            plain_one_level_config,
            buffer=buffer,
            instrument=instrument,
        )

        await _connect(server, exchange)
        await market_data.start()
        await market_data.subscribe([instrument], set(ALL_MARKET_DATA_STREAM_TYPES))
        async with asyncio.timeout(2.0):
            while "orderbook.1.BTCUSDT" not in server.subscriptions:
                await asyncio.sleep(0)

        await server.send_to_subscribers(
            "orderbook.1.BTCUSDT",
            {
                "topic": "orderbook.1.BTCUSDT",
                "type": "snapshot",
                "ts": 1_700_000_000_000,
                "data": {
                    "s": "BTCUSDT",
                    "b": [["29999", "1"]],
                    "a": [["30001", "2"]],
                    "u": 1,
                    "seq": 1,
                },
            },
        )
        book = await _await_book(buffer)

        await trader.consume_msg(book)
        await trader.update_state()

        creates = op_args(server, "order.create")
        assert len(creates) == 2
        by_cloid = {arg["orderLinkId"]: arg for [arg] in creates}
        expected = expected_plain_prices(
            30_000.0,
            1,
            15.0,
            tick_size=instrument.tick_size,
            lot_size=instrument.lot_size,
        )
        assert by_cloid["PLAIN00B"]["price"] == str(expected[0][0])
        assert by_cloid["PLAIN00B"]["side"] == "Buy"
        assert by_cloid["PLAIN00S"]["price"] == str(expected[0][1])
        assert by_cloid["PLAIN00S"]["side"] == "Sell"

        await market_data.stop()
        await private_data.stop()


class TestPlainTraderScenarios:
    """Verify plain quote placement, amendment, and cancellation on the wire."""

    @pytest.mark.asyncio
    async def test_initial_quote_placement(
        self, scripted_exchange, make_trader, plain_app_config
    ) -> None:
        server, exchange = scripted_exchange
        _seed_responses(server, "order.create", 10)
        trader = await make_trader(server, exchange, PlainTrader, plain_app_config)
        await _connect(server, exchange)

        await trader.consume_msg(
            make_orderbook(trader.instrument, mid=30_000.0, recv_ns=fresh_recv_ns())
        )
        await trader.update_state()

        creates = op_args(server, "order.create")
        assert len(creates) == 10
        by_cloid = {arg["orderLinkId"]: arg for [arg] in creates}
        for level, (bid_price, ask_price) in enumerate(_plain_prices(30_000.0)):
            bid = by_cloid[f"PLAIN{level:02d}B"]
            ask = by_cloid[f"PLAIN{level:02d}S"]
            assert bid["price"] == bid_price
            assert bid["side"] == "Buy"
            assert ask["price"] == ask_price
            assert ask["side"] == "Sell"
            assert bid["qty"] == "1.0"
            assert bid["orderType"] == "Limit"

    @pytest.mark.asyncio
    async def test_amends_when_mid_moves_beyond_buffer(
        self, scripted_exchange, make_trader, plain_app_config
    ) -> None:
        server, exchange = scripted_exchange
        _seed_responses(server, "order.create", 10)
        _seed_responses(server, "order.amend", 10)
        trader = await make_trader(server, exchange, PlainTrader, plain_app_config)
        await _connect(server, exchange)

        await trader.consume_msg(
            make_orderbook(trader.instrument, mid=30_000.0, recv_ns=fresh_recv_ns())
        )
        await trader.update_state()
        await _populate_live_orders(trader, _plain_live_prices())

        await trader.consume_msg(
            make_orderbook(trader.instrument, mid=30_030.0, recv_ns=fresh_recv_ns())
        )
        await trader.update_state()

        amends = op_args(server, "order.amend")
        assert len(amends) == 10
        by_cloid = {arg["orderLinkId"]: arg for [arg] in amends}
        assert by_cloid["PLAIN00B"]["price"] == _plain_prices(30_030.0)[0][0]
        assert by_cloid["PLAIN04S"]["price"] == _plain_prices(30_030.0)[4][1]

        await trader.consume_msg(
            make_orderbook(trader.instrument, mid=30_020.0, recv_ns=fresh_recv_ns())
        )
        await trader.update_state()

        assert op_count(server, "order.amend") == 10

    @pytest.mark.asyncio
    async def test_cancels_quote_dropped_by_inventory_bias(
        self, scripted_exchange, make_trader
    ) -> None:
        server, exchange = scripted_exchange
        _seed_responses(server, "order.create", 10)
        _seed_responses(server, "order.cancel", 1)
        trader = await make_trader(server, exchange, PlainTrader, _plain_flat_config())
        await _connect(server, exchange)

        await trader.consume_msg(
            make_orderbook(trader.instrument, mid=30_000.0, recv_ns=fresh_recv_ns())
        )
        await trader.update_state()
        await _populate_live_orders(trader, _plain_live_prices())

        await trader.consume_msg(
            make_position(trader.instrument, size=10.0, recv_ns=fresh_recv_ns())
        )
        await trader.update_state()

        cancels = op_args(server, "order.cancel")
        assert len(cancels) == 1
        assert cancels[0][0]["orderLinkId"] == "PLAIN00B"

    @pytest.mark.asyncio
    async def test_risk_rejection_blocks_and_recovers(
        self, scripted_exchange, make_trader, plain_app_config
    ) -> None:
        server, exchange = scripted_exchange
        _seed_responses(server, "order.create", 10)
        trader = await make_trader(server, exchange, PlainTrader, plain_app_config)
        await _connect(server, exchange)

        await trader.consume_msg(
            make_orderbook(trader.instrument, mid=30_000.0, recv_ns=fresh_recv_ns())
        )
        await trader.consume_msg(
            make_position(trader.instrument, size=20.0, recv_ns=fresh_recv_ns())
        )
        await trader.update_state()

        assert op_count(server, "order.create") == 0

        await trader.consume_msg(
            make_position(trader.instrument, size=0.0, recv_ns=fresh_recv_ns())
        )
        await trader.update_state()

        assert op_count(server, "order.create") == 10

    @pytest.mark.asyncio
    async def test_retries_create_rejected_by_exchange(
        self, scripted_exchange, make_trader, plain_app_config
    ) -> None:
        server, exchange = scripted_exchange
        _seed_responses(server, "order.create", 1, ret_code=10001)
        _seed_responses(server, "order.create", 9)
        trader = await make_trader(server, exchange, PlainTrader, plain_app_config)
        await _connect(server, exchange)

        await trader.consume_msg(
            make_orderbook(trader.instrument, mid=30_000.0, recv_ns=fresh_recv_ns())
        )
        await trader.update_state()
        await trader.update_state()

        assert op_count(server, "order.create") == 11

    @pytest.mark.asyncio
    async def test_kill_switch_cancels_all_live_orders(
        self, scripted_exchange, make_trader, plain_app_config
    ) -> None:
        server, exchange = scripted_exchange
        _seed_responses(server, "order.create", 10)
        _seed_responses(server, "order.cancel", 10)
        trader = await make_trader(server, exchange, PlainTrader, plain_app_config)
        await _connect(server, exchange)

        await trader.consume_msg(
            make_orderbook(trader.instrument, mid=30_000.0, recv_ns=fresh_recv_ns())
        )
        await trader.update_state()
        await _populate_live_orders(trader, _plain_live_prices())

        await trader.oms.kill_switch()

        cancels = op_args(server, "order.cancel")
        assert len(cancels) == 10
        assert {arg["orderLinkId"] for [arg] in cancels} == {
            cloid for cloid, _, _ in _plain_live_prices()
        }


class TestStinkyTraderScenarios:
    """Verify stinky ladder placement and fill-driven liquidation."""

    @pytest.mark.asyncio
    async def test_initial_ladder_placement(
        self, scripted_exchange, make_trader, stinky_app_config
    ) -> None:
        server, exchange = scripted_exchange
        _seed_responses(server, "order.create", 12)
        trader = await make_trader(server, exchange, StinkyTrader, stinky_app_config)
        await _connect(server, exchange)

        await trader.consume_msg(
            make_orderbook(trader.instrument, mid=30_000.0, recv_ns=fresh_recv_ns())
        )
        await trader.update_state()

        creates = op_args(server, "order.create")
        assert len(creates) == 12
        by_cloid = {arg["orderLinkId"]: arg for [arg] in creates}
        for level, (bid_price, ask_price) in enumerate(_stinky_prices(30_000.0)):
            bid = by_cloid[f"STINKY{level:02d}B"]
            ask = by_cloid[f"STINKY{level:02d}S"]
            assert bid["price"] == bid_price
            assert ask["price"] == ask_price
            assert bid["qty"] == "1.0"

    @pytest.mark.asyncio
    async def test_fill_liquidates_after_local_recv_wait(
        self, scripted_exchange, make_trader, stinky_app_config, monkeypatch
    ) -> None:
        import smm.traders.stinky.oms as oms_module

        monkeypatch.setattr(oms_module, "time_s", lambda: NOW_S)
        server, exchange = scripted_exchange
        _seed_responses(server, "order.create", 13)
        trader = await make_trader(server, exchange, StinkyTrader, stinky_app_config)
        await _connect(server, exchange)

        await trader.consume_msg(
            make_orderbook(trader.instrument, mid=30_000.0, recv_ns=fresh_recv_ns())
        )
        await trader.update_state()

        # The fill is received locally now, but the OMS clock has advanced past
        # the liquidation wait. The wait is anchored on the local receive time,
        # so the elapsed wait (not the exchange timestamp) triggers liquidation.
        recv_ns = fresh_recv_ns()
        monkeypatch.setattr(
            oms_module, "time_s", lambda: recv_ns / 1_000_000_000.0 + 6.0
        )
        await trader.consume_msg(
            make_execution_msg(
                trader.instrument,
                exec_time_ms=NOW_MS,
                price=30_000.0,
                size=0.01,
                is_buy=True,
                recv_ns=recv_ns,
            )
        )
        await trader.update_state()

        creates = op_args(server, "order.create")
        liquidation = [
            args[0]
            for args in creates
            if args[0].get("orderType") == "Market" and args[0].get("reduceOnly")
        ]
        assert len(liquidation) == 1
        assert liquidation[0]["side"] == "Sell"
        assert op_count(server, "order.create") == 13


class TestTraderStalenessAndHeartbeat:
    """Verify stale message filtering and heartbeat failure handling."""

    @pytest.mark.asyncio
    async def test_stale_messages_are_dropped(
        self, scripted_exchange, make_trader, plain_app_config
    ) -> None:
        server, exchange = scripted_exchange
        _seed_responses(server, "order.create", 10)
        trader = await make_trader(server, exchange, PlainTrader, plain_app_config)
        await _connect(server, exchange)

        stale = make_orderbook(
            trader.instrument,
            mid=30_000.0,
            recv_ns=fresh_recv_ns() - 200_000_000,
        )
        await trader.consume_msg(stale)
        await trader.update_state()

        assert op_count(server, "order.create") == 0

        fresh = make_orderbook(trader.instrument, mid=30_000.0, recv_ns=fresh_recv_ns())
        await trader.consume_msg(fresh)
        await trader.update_state()

        assert op_count(server, "order.create") == 10

    @pytest.mark.asyncio
    async def test_past_heartbeat_next_check_rejected(
        self, scripted_exchange, make_trader, plain_app_config, monkeypatch
    ) -> None:
        import smm.traders.base.trader as trader_module

        monkeypatch.setattr(trader_module, "time_s", lambda: NOW_S)
        server, exchange = scripted_exchange
        trader = await make_trader(server, exchange, PlainTrader, plain_app_config)

        heartbeat = make_heartbeat(time_next_check_ms=int((NOW_S - 1) * 1000))
        with pytest.raises(ValueError):
            await trader._track_heartbeat(heartbeat)

    @pytest.mark.asyncio
    async def test_heartbeat_stall_raises_connection_error(
        self, scripted_exchange, make_trader, plain_app_config, monkeypatch
    ) -> None:
        import smm.traders.base.trader as trader_module

        async def _noop_sleep(*args, **kwargs) -> None:
            return None

        monkeypatch.setattr(trader_module, "time_s", lambda: NOW_S)
        monkeypatch.setattr(trader_module.asyncio, "sleep", _noop_sleep)
        server, exchange = scripted_exchange
        trader = await make_trader(server, exchange, PlainTrader, plain_app_config)

        heartbeat = make_heartbeat(time_next_check_ms=int((NOW_S + 2) * 1000))
        with pytest.raises(ConnectionError):
            await trader._track_heartbeat(heartbeat)
