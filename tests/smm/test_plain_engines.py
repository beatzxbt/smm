"""Isolated tests for the plain trader pricing and risk engines.

Verifies exact desired-state output, inventory asymmetry, spread laddering,
and the risk approval matrix.
"""

from __future__ import annotations

import math

import pytest

from framework.base.common import Instrument
from mm_toolbox.rounding import Rounder, RounderConfig
from smm.config import PlainConfig, PricingConfig, RiskConfig, VolatilityConfig
from smm.traders.base.types import DesiredOrder, DesiredState
from smm.traders.base.volatility import VolatilityEstimator
from smm.traders.plain.pricing import PlainPricingEngine
from smm.traders.plain.risk import PlainRiskEngine
from tests.smm.support import (
    expected_plain_prices,
    make_empty_book,
    make_instrument,
    make_orderbook,
    make_position,
    make_trade_msg,
)

MID = 30_000.0
TICK = 0.01
LOT = 0.001
BASE_SPREAD_BPS = 15.0
MAX_INVENTORY_QUOTE = 300_000.0
NOW_S = 1_700_000_000.0
NOW_MS = int(NOW_S * 1000)


def _pricing(
    levels: int = 5,
    base_spread_bps: float = BASE_SPREAD_BPS,
    max_inventory_quote: float = MAX_INVENTORY_QUOTE,
    ladder: list[tuple[float, float]] | None = None,
    volatility_config: VolatilityConfig | None = None,
) -> PlainPricingEngine:
    """Build a plain pricing engine with deterministic defaults."""
    instrument = make_instrument(TICK, LOT)
    config = PricingConfig(
        levels=levels,
        base_spread_bps=base_spread_bps,
        max_inventory_quote=max_inventory_quote,
        inventory_spread_ladder=ladder or [],
    )
    volatility = VolatilityEstimator(volatility_config or VolatilityConfig())
    rounder = Rounder(RounderConfig.default(tick_size=TICK, lot_size=LOT))
    return PlainPricingEngine(
        instrument=instrument,
        config=config,
        plain_config=PlainConfig(),
        rounder=rounder,
        volatility=volatility,
    )


def _feed_book(engine: PlainPricingEngine, mid: float = MID) -> None:
    """Feed a symmetric book at the given mid price."""
    engine.consume_msg(make_orderbook(engine.instrument, mid=mid))


def _feed_position(engine: PlainPricingEngine, size: float) -> None:
    """Feed a long position of the given size."""
    engine.consume_msg(make_position(engine.instrument, size=size))


class TestPlainPricingQuotes:
    """Verify exact desired-state output for a flat inventory book."""

    def test_flat_inventory_produces_symmetric_ladder(self) -> None:
        engine = _pricing()
        _feed_book(engine)
        desired = engine.generate_desired_state()

        expected = expected_plain_prices(MID, 5, BASE_SPREAD_BPS)
        assert len(desired.bids) == 5
        assert len(desired.asks) == 5
        for level, (bid_price, ask_price) in enumerate(expected):
            assert desired.bids[level].price == bid_price
            assert desired.asks[level].price == ask_price
            assert desired.bids[level].size == pytest.approx(1.0)
            assert desired.asks[level].size == pytest.approx(1.0)
            assert desired.bids[level].client_order_id == f"PLAIN{level:02d}B"
            assert desired.asks[level].client_order_id == f"PLAIN{level:02d}S"

    def test_quote_per_level_splits_inventory_budget_evenly(self) -> None:
        engine = _pricing(max_inventory_quote=120_000.0, levels=2)
        _feed_book(engine)
        desired = engine.generate_desired_state()

        assert desired.bids[0].size == pytest.approx(120_000.0 / (2 * 2) / MID)

    def test_no_book_produces_no_quotes(self) -> None:
        engine = _pricing()
        desired = engine.generate_desired_state()

        assert desired.bids == []
        assert desired.asks == []

    def test_empty_book_leaves_mid_unchanged(self) -> None:
        engine = _pricing()
        _feed_book(engine)
        engine.consume_msg(make_empty_book(engine.instrument))

        expected = expected_plain_prices(MID, 5, BASE_SPREAD_BPS)
        assert engine.generate_desired_state().bids[0].price == expected[0][0]


class TestPlainPricingInventoryBias:
    """Verify inventory reduces the innermost reduce-side quote."""

    def test_long_position_shrinks_only_level_zero_bid(self) -> None:
        engine = _pricing()
        _feed_book(engine)
        _feed_position(engine, size=5.0)
        desired = engine.generate_desired_state()

        assert desired.bids[0].size == pytest.approx(0.5)
        assert desired.asks[0].size == pytest.approx(1.0)
        assert desired.bids[1].size == pytest.approx(1.0)
        assert desired.asks[1].size == pytest.approx(1.0)

    def test_full_utilization_drops_level_zero_bid(self) -> None:
        engine = _pricing()
        _feed_book(engine)
        _feed_position(engine, size=10.0)
        desired = engine.generate_desired_state()

        assert len(desired.bids) == 4
        assert desired.bids[0].client_order_id == "PLAIN01B"
        assert len(desired.asks) == 5

    def test_short_position_shrinks_level_zero_ask(self) -> None:
        engine = _pricing()
        _feed_book(engine)
        engine.consume_msg(make_position(engine.instrument, size=5.0, is_long=False))
        desired = engine.generate_desired_state()

        assert desired.bids[0].size == pytest.approx(1.0)
        assert desired.asks[0].size == pytest.approx(0.5)


class TestPlainPricingSpreadLadder:
    """Verify the inventory spread ladder applies the highest matched step."""

    def test_utilization_below_first_threshold_keeps_base_spread(self) -> None:
        engine = _pricing(ladder=[(2.0, 0.5), (3.0, 0.8)])
        _feed_book(engine)
        _feed_position(engine, size=3.0)
        desired = engine.generate_desired_state()

        expected = expected_plain_prices(MID, 5, BASE_SPREAD_BPS)
        assert desired.bids[0].price == expected[0][0]

    def test_utilization_mid_threshold_doubles_spread(self) -> None:
        engine = _pricing(ladder=[(2.0, 0.5), (3.0, 0.8)])
        _feed_book(engine)
        _feed_position(engine, size=6.0)
        desired = engine.generate_desired_state()

        expected = expected_plain_prices(MID, 5, BASE_SPREAD_BPS, multiplier=2.0)
        assert desired.bids[0].price == expected[0][0]

    def test_utilization_high_threshold_triples_spread(self) -> None:
        engine = _pricing(ladder=[(2.0, 0.5), (3.0, 0.8)])
        _feed_book(engine)
        _feed_position(engine, size=9.0)
        desired = engine.generate_desired_state()

        expected = expected_plain_prices(MID, 5, BASE_SPREAD_BPS, multiplier=3.0)
        assert desired.bids[0].price == expected[0][0]

    def test_ladder_thresholds_are_utilization_fractions(self) -> None:
        engine = _pricing(ladder=[(4.0, 0.25)])
        _feed_book(engine)
        _feed_position(engine, size=7.5)
        desired = engine.generate_desired_state()

        expected = expected_plain_prices(MID, 5, BASE_SPREAD_BPS, multiplier=4.0)
        assert desired.bids[0].price == expected[0][0]


class TestPlainPricingVolatility:
    """Verify volatility widens the spread above the configured base."""

    def test_volatile_trades_increase_spread_beyond_base(self, monkeypatch) -> None:
        import smm.traders.base.volatility as volatility_module

        monkeypatch.setattr(volatility_module, "time_s", lambda: NOW_S)
        engine = _pricing(
            volatility_config=VolatilityConfig(
                half_life_s=1.0,
                min_spread_bps=5.0,
                max_spread_bps=200.0,
                update_interval_s=0.5,
            )
        )
        _feed_book(engine)
        engine.consume_msg(
            make_trade_msg(engine.instrument, price=30_000.0, time_ms=NOW_MS - 600)
        )
        engine.consume_msg(
            make_trade_msg(engine.instrument, price=30_300.0, time_ms=NOW_MS - 100)
        )
        desired = engine.generate_desired_state()

        decay = math.log(0.5) / 1.0
        alpha = 1.0 - math.exp(decay * 0.5)
        expected_spread_bps = max(15.0, alpha * 0.01 * 10_000.0)
        expected = expected_plain_prices(MID, 5, expected_spread_bps)
        assert desired.bids[0].price == expected[0][0]

    def test_quiet_book_keeps_base_spread(self) -> None:
        engine = _pricing()
        _feed_book(engine)
        desired = engine.generate_desired_state()

        expected = expected_plain_prices(MID, 5, BASE_SPREAD_BPS)
        assert desired.bids[0].price == expected[0][0]


class TestPlainRiskApproval:
    """Verify the risk engine approval matrix."""

    def _engine(self, **overrides) -> PlainRiskEngine:
        return PlainRiskEngine(RiskConfig(**overrides))

    def _desired(self, instrument: Instrument, prices: list[float]) -> DesiredState:
        desired = DesiredState.empty(instrument)
        for price in prices:
            order = DesiredOrder(
                price=price,
                is_buy=True,
                size=1.0,
                is_maker=True,
                reduce_only=False,
            )
            desired.bids.append(order)
        return desired

    def test_fresh_engine_rejects_without_mid(self) -> None:
        instrument = make_instrument(TICK, LOT)
        engine = self._engine()
        assert not engine.try_approve_desired_state(
            self._desired(instrument, [29_955.0])
        )

    def test_force_bypasses_mid_readiness(self) -> None:
        instrument = make_instrument(TICK, LOT)
        engine = self._engine()
        assert engine.try_approve_desired_state(
            self._desired(instrument, [29_955.0]), force=True
        )

    def test_approves_valid_orders_with_mid(self) -> None:
        instrument = make_instrument(TICK, LOT)
        engine = self._engine()
        engine.consume_msg(make_orderbook(instrument, mid=MID))
        assert engine.try_approve_desired_state(
            self._desired(instrument, [29_955.0, 30_045.0])
        )

    def test_rejects_when_open_order_count_exceeds_limit(self) -> None:
        instrument = make_instrument(TICK, LOT)
        engine = self._engine(max_open_orders=2)
        engine.consume_msg(make_orderbook(instrument, mid=MID))
        assert not engine.try_approve_desired_state(
            self._desired(instrument, [29_955.0, 29_910.0, 30_045.0])
        )

    def test_rejects_order_beyond_max_distance(self) -> None:
        instrument = make_instrument(TICK, LOT)
        engine = self._engine()
        engine.consume_msg(make_orderbook(instrument, mid=MID))
        assert not engine.try_approve_desired_state(
            self._desired(instrument, [MID * 1.011])
        )

    def test_rejects_when_net_inventory_exceeds_budget(self) -> None:
        instrument = make_instrument(TICK, LOT)
        engine = self._engine()
        engine.consume_msg(make_orderbook(instrument, mid=MID))
        engine.consume_msg(make_position(instrument, size=20.0))
        assert not engine.try_approve_desired_state(
            self._desired(instrument, [29_955.0])
        )

    def test_approves_with_small_inventory(self) -> None:
        instrument = make_instrument(TICK, LOT)
        engine = self._engine()
        engine.consume_msg(make_orderbook(instrument, mid=MID))
        engine.consume_msg(make_position(instrument, size=0.01))
        assert engine.try_approve_desired_state(
            self._desired(instrument, [29_955.0, 30_045.0])
        )


class TestDesiredOrderValidation:
    """Verify construction-time invariants of desired orders."""

    def test_maker_order_requires_positive_price(self) -> None:
        with pytest.raises(ValueError):
            DesiredOrder(
                price=0.0,
                is_buy=True,
                size=1.0,
                is_maker=True,
                reduce_only=False,
            )

    def test_order_requires_positive_size(self) -> None:
        with pytest.raises(ValueError):
            DesiredOrder(
                price=30_000.0,
                is_buy=True,
                size=0.0,
                is_maker=False,
                reduce_only=False,
            )

    def test_market_order_allows_zero_price(self) -> None:
        order = DesiredOrder(
            price=0.0,
            is_buy=True,
            size=1.0,
            is_maker=False,
            reduce_only=True,
        )
        assert order.size == 1.0
