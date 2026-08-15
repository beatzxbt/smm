"""Isolated tests for the stinky trader pricing engine and OMS.

Verifies the linear spread ladder, fill lot classification, and liquidation
timing anchored on local receive time.
"""

from __future__ import annotations

import pytest

from framework.base.common import ClientOrderId, Instrument
from mm_toolbox.rounding import Rounder, RounderConfig
from smm.config import OmsConfig, PricingConfig, StinkyConfig, VolatilityConfig
from smm.traders.base.types import DesiredState
from smm.traders.base.volatility import VolatilityEstimator
from smm.traders.stinky.oms import StinkyOrderManagementSystem
from smm.traders.stinky.pricing import StinkyPricingEngine
from tests.smm.support import (
    expected_stinky_prices,
    make_execution_msg,
    make_instrument,
    make_orderbook,
)

MID = 30_000.0
TICK = 0.01
LOT = 0.001
NOW_S = 1_700_000_000.0
NOW_MS = int(NOW_S * 1000)
NOW_NS = int(NOW_S * 1_000_000_000)


def _pricing(
    levels: int = 6,
    min_spread_bps: float = 50.0,
    max_spread_bps: float = 250.0,
    max_inventory_quote: float = 360_000.0,
) -> StinkyPricingEngine:
    """Build a stinky pricing engine with deterministic defaults."""
    instrument = make_instrument(TICK, LOT)
    config = PricingConfig(
        levels=levels,
        base_spread_bps=15.0,
        max_inventory_quote=max_inventory_quote,
        inventory_spread_ladder=[],
    )
    stinky = StinkyConfig(
        levels=levels,
        min_spread_bps=min_spread_bps,
        max_spread_bps=max_spread_bps,
    )
    volatility = VolatilityEstimator(VolatilityConfig())
    rounder = Rounder(RounderConfig.default(tick_size=TICK, lot_size=LOT))
    return StinkyPricingEngine(
        instrument=instrument,
        config=config,
        stinky_config=stinky,
        rounder=rounder,
        volatility=volatility,
    )


def _oms(
    exchange,
    instrument: Instrument | None = None,
    logger=None,
) -> StinkyOrderManagementSystem:
    """Build a stinky OMS with default budgets."""
    return StinkyOrderManagementSystem(
        instrument=instrument or make_instrument(TICK, LOT),
        exchange=exchange,
        logger=logger,
        config=OmsConfig(),
        stinky_config=StinkyConfig(),
    )


class _RecordingExchange:
    """Exchange stub that records submitted liquidation orders."""

    def __init__(self) -> None:
        """Initialize the stub with an empty record."""
        self.submitted = []

    async def create_order(self, order) -> None:
        """Record a submitted create order."""
        self.submitted.append(order)

    def generate_cloid(self, prefix=None, suffix=None) -> ClientOrderId:
        """Return a deterministic client order id for the stub."""
        return ClientOrderId(f"{prefix}-{len(self.submitted)}")


class TestStinkyPricing:
    """Verify the linear spread ladder and quote sizing."""

    def test_ladder_interpolates_spread_from_min_to_max(self) -> None:
        engine = _pricing()
        instrument = engine.instrument
        engine.consume_msg(make_orderbook(instrument, mid=MID))
        desired = engine.generate_desired_state()

        expected = expected_stinky_prices(MID, 6, 50.0, 250.0)
        assert len(desired.bids) == 6
        assert len(desired.asks) == 6
        for level, (bid_price, ask_price) in enumerate(expected):
            assert desired.bids[level].price == bid_price
            assert desired.asks[level].price == ask_price
            assert desired.bids[level].size == pytest.approx(1.0)
            assert desired.bids[level].client_order_id == f"STINKY{level:02d}B"
            assert desired.asks[level].client_order_id == f"STINKY{level:02d}S"

    def test_single_level_uses_min_spread(self) -> None:
        engine = _pricing(levels=1)
        instrument = engine.instrument
        engine.consume_msg(make_orderbook(instrument, mid=MID))
        desired = engine.generate_desired_state()

        expected = expected_stinky_prices(MID, 1, 50.0, 250.0)
        assert len(desired.bids) == 1
        assert desired.bids[0].price == expected[0][0]
        assert desired.asks[0].price == expected[0][1]

    def test_no_book_produces_no_quotes(self) -> None:
        engine = _pricing()
        desired = engine.generate_desired_state()

        assert desired.bids == []
        assert desired.asks == []

    def test_quote_per_level_splits_inventory_budget_evenly(self) -> None:
        engine = _pricing(levels=4, max_inventory_quote=240_000.0)
        instrument = engine.instrument
        engine.consume_msg(make_orderbook(instrument, mid=MID))
        desired = engine.generate_desired_state()

        assert desired.bids[0].size == pytest.approx(240_000.0 / (2 * 4) / MID)


class TestStinkyOmsFillTracking:
    """Verify execution fills become tracked inventory lots."""

    def test_small_fill_tracks_signed_size(self, test_logger) -> None:
        exchange = _RecordingExchange()
        oms = _oms(exchange, logger=test_logger)
        instrument = oms.instrument
        oms.consume_msg(
            make_execution_msg(
                instrument,
                exec_time_ms=NOW_MS,
                price=10_000.0,
                size=0.005,
                is_buy=True,
            )
        )

        assert len(oms._inventory_positions) == 1
        lot = oms._inventory_positions[0]
        assert lot.size == pytest.approx(0.005)
        assert not lot.is_large
        assert lot.remaining_size == pytest.approx(0.005)

    def test_large_fill_classified_by_quote_value(self, test_logger) -> None:
        exchange = _RecordingExchange()
        oms = _oms(exchange, logger=test_logger)
        instrument = oms.instrument
        oms.consume_msg(
            make_execution_msg(
                instrument,
                exec_time_ms=NOW_MS,
                price=30_000.0,
                size=0.01,
                is_buy=True,
            )
        )

        assert oms._inventory_positions[0].is_large

    def test_short_fill_tracks_negative_size(self, test_logger) -> None:
        exchange = _RecordingExchange()
        oms = _oms(exchange, logger=test_logger)
        instrument = oms.instrument
        oms.consume_msg(
            make_execution_msg(
                instrument,
                exec_time_ms=NOW_MS,
                price=30_000.0,
                size=0.02,
                is_buy=False,
            )
        )

        assert oms._inventory_positions[0].size == pytest.approx(-0.02)


class TestStinkyOmsLiquidationTiming:
    """Verify liquidation waits anchor on local receive time.

    Exchange execution timestamps may lag local receive time, so the wait must
    be measured from the message's local receive timestamp rather than the
    exchange-provided timestamp.
    """

    @pytest.mark.asyncio
    async def test_fill_liquidates_after_local_recv_wait(
        self, test_logger, monkeypatch
    ) -> None:
        import smm.traders.stinky.oms as oms_module

        monkeypatch.setattr(oms_module, "time_s", lambda: NOW_S)
        exchange = _RecordingExchange()
        oms = _oms(exchange, logger=test_logger)
        instrument = oms.instrument
        recv_ns = NOW_NS - 6 * 1_000_000_000
        oms.consume_msg(
            make_execution_msg(
                instrument,
                exec_time_ms=NOW_MS,
                price=30_000.0,
                size=0.01,
                is_buy=True,
                recv_ns=recv_ns,
            )
        )

        desired = DesiredState.empty(instrument)
        await oms.try_update_state(desired)

        assert len(exchange.submitted) == 1
        order = exchange.submitted[0]
        assert order.is_buy is False
        assert order.reduce_only is True
        assert order.is_maker is False


class TestStinkyOmsLiquidationOrder:
    """Verify the liquidation order shape for an elapsed lot."""

    @pytest.mark.asyncio
    async def test_elapsed_fill_submits_reduce_only_market_order(
        self, test_logger, monkeypatch
    ) -> None:
        import smm.traders.stinky.oms as oms_module

        monkeypatch.setattr(oms_module, "time_s", lambda: NOW_S)
        exchange = _RecordingExchange()
        oms = _oms(exchange, logger=test_logger)
        instrument = oms.instrument
        oms.consume_msg(
            make_execution_msg(
                instrument,
                exec_time_ms=NOW_MS - 10_000,
                price=30_000.0,
                size=0.02,
                is_buy=True,
                recv_ns=NOW_NS - 10 * 1_000_000_000,
            )
        )

        desired = DesiredState.empty(instrument)
        await oms.try_update_state(desired)

        assert len(exchange.submitted) == 1
        order = exchange.submitted[0]
        assert order.is_buy is False
        assert order.size == pytest.approx(0.02)
        assert order.reduce_only is True
        assert order.is_maker is False
        assert str(order.client_order_id).startswith("STINKYL")
