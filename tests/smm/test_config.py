"""Tests for SMM configuration models and TOML loader.

Layer 1: Tests for primitive config structs (CoreConfig, VolatilityConfig, etc.)
Layer 2: Tests for composite AppConfig
Layer 3: Tests for load_config TOML integration
"""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from framework.base.common import Venue
from smm.config import (
    AppConfig,
    CoreConfig,
    OmsBudgetConfig,
    OmsConfig,
    PlainConfig,
    PricingConfig,
    RateWindow,
    RiskConfig,
    StinkyConfig,
    TraderId,
    VolatilityConfig,
    load_config,
)


def make_core_config(
    *,
    venue: Venue = Venue.BYBIT,
    symbol: str = "SOLUSDT",
    trader: TraderId = TraderId.PLAIN,
) -> CoreConfig:
    """Build a core config while allowing one field to vary in a test."""
    return CoreConfig(venue=venue, symbol=symbol, trader=trader)


def make_pricing_config(**overrides: object) -> PricingConfig:
    """Build a pricing config while allowing selected fields to vary."""
    values: dict[str, object] = {
        "levels": 5,
        "base_spread_bps": 15.0,
        "max_inventory_quote": 500.0,
        "inventory_spread_ladder": [(2.0, 0.5), (3.0, 0.8)],
    }
    values.update(overrides)
    return PricingConfig(**values)  # type: ignore[arg-type]


class TestTraderId:
    """Layer 1: Tests for TraderId enum."""

    def test_plain_value(self) -> None:
        """TraderId.PLAIN has correct string value."""
        assert TraderId.PLAIN == "plain"
        assert TraderId.PLAIN.value == "plain"

    def test_stinky_value(self) -> None:
        """TraderId.STINKY has correct string value."""
        assert TraderId.STINKY == "stinky"
        assert TraderId.STINKY.value == "stinky"


class TestRateWindow:
    """Layer 1: Tests for RateWindow enum."""

    def test_sec_value(self) -> None:
        """RateWindow.SEC has correct string value."""
        assert RateWindow.SEC == "sec"
        assert RateWindow.SEC.value == "sec"

    def test_min_value(self) -> None:
        """RateWindow.MIN has correct string value."""
        assert RateWindow.MIN == "min"
        assert RateWindow.MIN.value == "min"


class TestCoreConfig:
    """Layer 1: Tests for CoreConfig struct."""

    def test_default_values(self, default_core_config: CoreConfig) -> None:
        """CoreConfig has expected default values."""
        assert default_core_config.venue == Venue.BYBIT
        assert default_core_config.symbol == "SOLUSDT"
        assert default_core_config.trader == TraderId.PLAIN

    def test_custom_values(self) -> None:
        """CoreConfig accepts custom values."""
        config = CoreConfig(
            venue=Venue.BINANCE_USDM,
            symbol="BTCUSDT",
            trader=TraderId.STINKY,
        )
        assert config.venue == Venue.BINANCE_USDM
        assert config.symbol == "BTCUSDT"
        assert config.trader == TraderId.STINKY

    def test_empty_symbol_raises(self) -> None:
        """CoreConfig rejects empty symbol."""
        with pytest.raises(ValueError, match="symbol must be non-empty"):
            make_core_config(symbol="")

    def test_whitespace_symbol_raises(self) -> None:
        """CoreConfig rejects whitespace-only symbol."""
        with pytest.raises(ValueError, match="symbol must be non-empty"):
            make_core_config(symbol="   ")


class TestVolatilityConfig:
    """Layer 1: Tests for VolatilityConfig struct."""

    def test_default_values(self, default_volatility_config: VolatilityConfig) -> None:
        """VolatilityConfig has expected default values."""
        assert default_volatility_config.half_life_s == 10.0
        assert default_volatility_config.min_spread_bps == 5.0
        assert default_volatility_config.max_spread_bps == 200.0
        assert default_volatility_config.update_interval_s == 1.0

    def test_custom_values(self) -> None:
        """VolatilityConfig accepts custom values."""
        config = VolatilityConfig(
            half_life_s=30.0,
            min_spread_bps=10.0,
            max_spread_bps=100.0,
            update_interval_s=0.5,
        )
        assert config.half_life_s == 30.0
        assert config.min_spread_bps == 10.0
        assert config.max_spread_bps == 100.0
        assert config.update_interval_s == 0.5

    def test_zero_half_life_raises(self) -> None:
        """VolatilityConfig rejects zero half_life_s."""
        with pytest.raises(ValueError, match="half_life_s must be > 0"):
            VolatilityConfig(half_life_s=0.0)

    def test_negative_half_life_raises(self) -> None:
        """VolatilityConfig rejects negative half_life_s."""
        with pytest.raises(ValueError, match="half_life_s must be > 0"):
            VolatilityConfig(half_life_s=-1.0)

    def test_negative_min_spread_raises(self) -> None:
        """VolatilityConfig rejects negative min_spread_bps."""
        with pytest.raises(ValueError, match="min_spread_bps must be >= 0"):
            VolatilityConfig(min_spread_bps=-1.0)

    def test_zero_max_spread_raises(self) -> None:
        """VolatilityConfig rejects zero max_spread_bps."""
        with pytest.raises(ValueError, match="max_spread_bps must be > 0"):
            VolatilityConfig(max_spread_bps=0.0)

    def test_min_greater_than_max_spread_raises(self) -> None:
        """VolatilityConfig rejects min_spread_bps > max_spread_bps."""
        with pytest.raises(
            ValueError, match="min_spread_bps must be <= max_spread_bps"
        ):
            VolatilityConfig(min_spread_bps=100.0, max_spread_bps=50.0)

    def test_zero_update_interval_raises(self) -> None:
        """VolatilityConfig rejects zero update_interval_s."""
        with pytest.raises(ValueError, match="update_interval_s must be > 0"):
            VolatilityConfig(update_interval_s=0.0)

    def test_boundary_min_spread_zero_allowed(self) -> None:
        """VolatilityConfig allows min_spread_bps of 0."""
        config = VolatilityConfig(min_spread_bps=0.0)
        assert config.min_spread_bps == 0.0

    def test_boundary_min_equals_max_spread(self) -> None:
        """VolatilityConfig allows min_spread_bps == max_spread_bps."""
        config = VolatilityConfig(min_spread_bps=50.0, max_spread_bps=50.0)
        assert config.min_spread_bps == config.max_spread_bps


class TestPricingConfig:
    """Layer 1: Tests for PricingConfig struct."""

    def test_default_values(self, default_pricing_config: PricingConfig) -> None:
        """PricingConfig has expected default values."""
        assert default_pricing_config.levels == 5
        assert default_pricing_config.base_spread_bps == 15.0
        assert default_pricing_config.max_inventory_quote == 500.0
        assert default_pricing_config.inventory_spread_ladder == [
            (2.0, 0.5),
            (3.0, 0.8),
        ]

    def test_custom_values(self) -> None:
        """PricingConfig accepts custom values."""
        config = PricingConfig(
            levels=3,
            base_spread_bps=25.0,
            max_inventory_quote=1000.0,
            inventory_spread_ladder=[(1.5, 0.3), (2.5, 0.7)],
        )
        assert config.levels == 3
        assert config.base_spread_bps == 25.0
        assert config.max_inventory_quote == 1000.0
        assert config.inventory_spread_ladder == [(1.5, 0.3), (2.5, 0.7)]

    def test_zero_levels_raises(self) -> None:
        """PricingConfig rejects zero levels."""
        with pytest.raises(ValueError, match="levels must be > 0"):
            make_pricing_config(levels=0)

    def test_negative_base_spread_raises(self) -> None:
        """PricingConfig rejects negative base_spread_bps."""
        with pytest.raises(ValueError, match="base_spread_bps must be >= 0"):
            make_pricing_config(base_spread_bps=-1.0)

    def test_zero_max_inventory_raises(self) -> None:
        """PricingConfig rejects zero max_inventory_quote."""
        with pytest.raises(ValueError, match="max_inventory_quote must be > 0"):
            make_pricing_config(max_inventory_quote=0.0)

    def test_ladder_entry_wrong_length_raises(self) -> None:
        """PricingConfig rejects ladder entries with wrong length."""
        with pytest.raises(
            ValueError, match="inventory_spread_ladder entries must be length 2"
        ):
            make_pricing_config(inventory_spread_ladder=[(1.5, 0.3, 0.5)])

    def test_ladder_zero_multiplier_raises(self) -> None:
        """PricingConfig rejects ladder with zero multiplier."""
        with pytest.raises(ValueError, match="inventory spread multiplier must be > 0"):
            make_pricing_config(inventory_spread_ladder=[(0.0, 0.5)])

    def test_ladder_negative_utilization_raises(self) -> None:
        """PricingConfig rejects ladder with negative utilization."""
        with pytest.raises(ValueError, match="inventory utilization must be within"):
            make_pricing_config(inventory_spread_ladder=[(1.5, -0.1)])

    def test_ladder_utilization_above_one_raises(self) -> None:
        """PricingConfig rejects ladder with utilization > 1."""
        with pytest.raises(ValueError, match="inventory utilization must be within"):
            make_pricing_config(inventory_spread_ladder=[(1.5, 1.1)])

    def test_ladder_sorted_by_utilization(self) -> None:
        """PricingConfig sorts ladder by utilization."""
        config = make_pricing_config(
            inventory_spread_ladder=[(3.0, 0.9), (1.5, 0.3), (2.0, 0.6)]
        )
        assert config.inventory_spread_ladder == [(1.5, 0.3), (2.0, 0.6), (3.0, 0.9)]

    def test_empty_ladder_allowed(self) -> None:
        """PricingConfig allows empty inventory_spread_ladder."""
        config = make_pricing_config(inventory_spread_ladder=[])
        assert config.inventory_spread_ladder == []


class TestRiskConfig:
    """Layer 1: Tests for RiskConfig struct."""

    def test_default_values(self, default_risk_config: RiskConfig) -> None:
        """RiskConfig has expected default values."""
        assert default_risk_config.max_inventory_quote == 500.0
        assert default_risk_config.max_open_orders == 10
        assert default_risk_config.max_order_distance_pct == 1.0

    def test_custom_values(self) -> None:
        """RiskConfig accepts custom values."""
        config = RiskConfig(
            max_inventory_quote=1000.0,
            max_open_orders=20,
            max_order_distance_pct=2.5,
        )
        assert config.max_inventory_quote == 1000.0
        assert config.max_open_orders == 20
        assert config.max_order_distance_pct == 2.5

    def test_zero_max_inventory_raises(self) -> None:
        """RiskConfig rejects zero max_inventory_quote."""
        with pytest.raises(ValueError, match="max_inventory_quote must be > 0"):
            RiskConfig(max_inventory_quote=0.0)

    def test_zero_max_orders_raises(self) -> None:
        """RiskConfig rejects zero max_open_orders."""
        with pytest.raises(ValueError, match="max_open_orders must be > 0"):
            RiskConfig(max_open_orders=0)

    def test_zero_order_distance_raises(self) -> None:
        """RiskConfig rejects zero max_order_distance_pct."""
        with pytest.raises(ValueError, match="max_order_distance_pct must be > 0"):
            RiskConfig(max_order_distance_pct=0.0)


class TestOmsBudgetConfig:
    """Layer 1: Tests for OmsBudgetConfig struct."""

    def test_default_values(self, default_oms_budget_config: OmsBudgetConfig) -> None:
        """OmsBudgetConfig has expected default values."""
        assert default_oms_budget_config.limit == 10
        assert default_oms_budget_config.per == RateWindow.SEC

    def test_custom_values(self) -> None:
        """OmsBudgetConfig accepts custom values."""
        config = OmsBudgetConfig(limit=60, per=RateWindow.MIN)
        assert config.limit == 60
        assert config.per == RateWindow.MIN

    def test_zero_limit_raises(self) -> None:
        """OmsBudgetConfig rejects zero limit."""
        with pytest.raises(ValueError, match="limit must be > 0"):
            OmsBudgetConfig(limit=0)

    def test_negative_limit_raises(self) -> None:
        """OmsBudgetConfig rejects negative limit."""
        with pytest.raises(ValueError, match="limit must be > 0"):
            OmsBudgetConfig(limit=-5)


class TestOmsConfig:
    """Layer 1: Tests for OmsConfig struct."""

    def test_default_values(self, default_oms_config: OmsConfig) -> None:
        """OmsConfig has expected default values."""
        assert default_oms_config.create.limit == 10
        assert default_oms_config.amend.limit == 10
        assert default_oms_config.cancel.limit == 10
        assert default_oms_config.price_buffer_bps == 5.0

    def test_custom_values(self) -> None:
        """OmsConfig accepts custom nested values."""
        config = OmsConfig(
            create=OmsBudgetConfig(limit=20),
            amend=OmsBudgetConfig(limit=30, per=RateWindow.MIN),
            cancel=OmsBudgetConfig(limit=40),
            price_buffer_bps=10.0,
        )
        assert config.create.limit == 20
        assert config.amend.limit == 30
        assert config.amend.per == RateWindow.MIN
        assert config.cancel.limit == 40
        assert config.price_buffer_bps == 10.0

    def test_negative_price_buffer_raises(self) -> None:
        """OmsConfig rejects negative price_buffer_bps."""
        with pytest.raises(ValueError, match="price_buffer_bps must be >= 0"):
            OmsConfig(price_buffer_bps=-1.0)

    def test_zero_price_buffer_allowed(self) -> None:
        """OmsConfig allows zero price_buffer_bps."""
        config = OmsConfig(price_buffer_bps=0.0)
        assert config.price_buffer_bps == 0.0


class TestPlainConfig:
    """Layer 1: Tests for PlainConfig struct."""

    def test_default_values(self, default_plain_config: PlainConfig) -> None:
        """PlainConfig has expected default values."""
        assert default_plain_config.cloid_prefix == "PLAIN"

    def test_custom_prefix(self) -> None:
        """PlainConfig accepts custom cloid_prefix."""
        config = PlainConfig(cloid_prefix="CUSTOM")
        assert config.cloid_prefix == "CUSTOM"

    def test_empty_prefix_raises(self) -> None:
        """PlainConfig rejects empty cloid_prefix."""
        with pytest.raises(ValueError, match="cloid_prefix must be non-empty"):
            PlainConfig(cloid_prefix="")

    def test_whitespace_prefix_raises(self) -> None:
        """PlainConfig rejects whitespace-only cloid_prefix."""
        with pytest.raises(ValueError, match="cloid_prefix must be non-empty"):
            PlainConfig(cloid_prefix="   ")


class TestStinkyConfig:
    """Layer 1: Tests for StinkyConfig struct."""

    def test_default_values(self, default_stinky_config: StinkyConfig) -> None:
        """StinkyConfig has expected default values."""
        assert default_stinky_config.levels == 6
        assert default_stinky_config.min_spread_bps == 50.0
        assert default_stinky_config.max_spread_bps == 250.0
        assert default_stinky_config.large_fill_threshold_quote == 100.0
        assert default_stinky_config.small_fill_wait_s == 1.0
        assert default_stinky_config.large_fill_wait_s == 5.0
        assert default_stinky_config.cloid_prefix == "STINKY"

    def test_custom_values(self) -> None:
        """StinkyConfig accepts custom values."""
        config = StinkyConfig(
            levels=10,
            min_spread_bps=30.0,
            max_spread_bps=300.0,
            large_fill_threshold_quote=200.0,
            small_fill_wait_s=0.5,
            large_fill_wait_s=10.0,
            cloid_prefix="CUSTOM_STINKY",
        )
        assert config.levels == 10
        assert config.min_spread_bps == 30.0
        assert config.max_spread_bps == 300.0
        assert config.large_fill_threshold_quote == 200.0
        assert config.small_fill_wait_s == 0.5
        assert config.large_fill_wait_s == 10.0
        assert config.cloid_prefix == "CUSTOM_STINKY"

    def test_zero_levels_raises(self) -> None:
        """StinkyConfig rejects zero levels."""
        with pytest.raises(ValueError, match="levels must be > 0"):
            StinkyConfig(levels=0)

    def test_zero_min_spread_raises(self) -> None:
        """StinkyConfig rejects zero min_spread_bps."""
        with pytest.raises(ValueError, match="min_spread_bps must be > 0"):
            StinkyConfig(min_spread_bps=0.0)

    def test_zero_max_spread_raises(self) -> None:
        """StinkyConfig rejects zero max_spread_bps."""
        with pytest.raises(ValueError, match="max_spread_bps must be > 0"):
            StinkyConfig(max_spread_bps=0.0)

    def test_min_greater_than_max_spread_raises(self) -> None:
        """StinkyConfig rejects min_spread_bps > max_spread_bps."""
        with pytest.raises(
            ValueError, match="min_spread_bps must be <= max_spread_bps"
        ):
            StinkyConfig(min_spread_bps=300.0, max_spread_bps=100.0)

    def test_zero_large_fill_threshold_raises(self) -> None:
        """StinkyConfig rejects zero large_fill_threshold_quote."""
        with pytest.raises(ValueError, match="large_fill_threshold_quote must be > 0"):
            StinkyConfig(large_fill_threshold_quote=0.0)

    def test_negative_small_fill_wait_raises(self) -> None:
        """StinkyConfig rejects negative small_fill_wait_s."""
        with pytest.raises(ValueError, match="small_fill_wait_s must be >= 0"):
            StinkyConfig(small_fill_wait_s=-1.0)

    def test_negative_large_fill_wait_raises(self) -> None:
        """StinkyConfig rejects negative large_fill_wait_s."""
        with pytest.raises(ValueError, match="large_fill_wait_s must be >= 0"):
            StinkyConfig(large_fill_wait_s=-1.0)

    def test_empty_prefix_raises(self) -> None:
        """StinkyConfig rejects empty cloid_prefix."""
        with pytest.raises(ValueError, match="cloid_prefix must be non-empty"):
            StinkyConfig(cloid_prefix="")

    def test_zero_wait_times_allowed(self) -> None:
        """StinkyConfig allows zero wait times."""
        config = StinkyConfig(small_fill_wait_s=0.0, large_fill_wait_s=0.0)
        assert config.small_fill_wait_s == 0.0
        assert config.large_fill_wait_s == 0.0


class TestAppConfig:
    """Layer 2: Tests for composite AppConfig struct."""

    def test_default_values(self, default_app_config: AppConfig) -> None:
        """AppConfig has expected default nested configs."""
        assert default_app_config.core.venue == Venue.BYBIT
        assert default_app_config.volatility.half_life_s == 10.0
        assert default_app_config.pricing.levels == 5
        assert default_app_config.risk.max_open_orders == 10
        assert default_app_config.oms.price_buffer_bps == 5.0
        assert default_app_config.plain.cloid_prefix == "PLAIN"
        assert default_app_config.stinky.cloid_prefix == "STINKY"

    def test_custom_nested_configs(self) -> None:
        """AppConfig accepts custom nested configs."""
        config = AppConfig(
            core=make_core_config(symbol="ETHUSDT", trader=TraderId.STINKY),
            pricing=make_pricing_config(levels=3),
            risk=RiskConfig(max_open_orders=5),
        )
        assert config.core.symbol == "ETHUSDT"
        assert config.core.trader == TraderId.STINKY
        assert config.pricing.levels == 3
        assert config.risk.max_open_orders == 5

    def test_partial_override(self) -> None:
        """AppConfig allows partial overrides, defaulting others."""
        config = AppConfig(
            core=make_core_config(symbol="XRPUSDT"),
            pricing=make_pricing_config(),
        )
        assert config.core.symbol == "XRPUSDT"
        assert config.volatility.half_life_s == 10.0
        assert config.pricing.levels == 5


class TestLoadConfig:
    """Layer 3: Tests for load_config TOML integration."""

    def test_load_minimal_config(self) -> None:
        """load_config parses minimal TOML with defaults."""
        toml_content = """\
[core]
venue = "Bybit"
symbol = "BTCUSDT"
trader = "plain"

[pricing]
levels = 5
base_spread_bps = 15.0
max_inventory_quote = 500.0
inventory_spread_ladder = [[2.0, 0.5], [3.0, 0.8]]
"""
        with tempfile.NamedTemporaryFile(suffix=".toml", delete=False, mode="w") as f:
            f.write(toml_content)
            f.flush()
            config = load_config(f.name)

        assert config.core.symbol == "BTCUSDT"
        assert config.core.venue == Venue.BYBIT
        assert config.volatility.half_life_s == 10.0

    def test_load_full_config(self) -> None:
        """load_config parses full TOML with all sections."""
        toml_content = """\
[core]
venue = "BinanceUsdM"
symbol = "ETHUSDT"
trader = "stinky"

[volatility]
half_life_s = 20.0
min_spread_bps = 10.0
max_spread_bps = 150.0
update_interval_s = 0.5

[pricing]
levels = 3
base_spread_bps = 20.0
max_inventory_quote = 1000.0
inventory_spread_ladder = [[1.5, 0.3], [2.5, 0.7]]

[risk]
max_inventory_quote = 1000.0
max_open_orders = 20
max_order_distance_pct = 2.0

[oms]
price_buffer_bps = 8.0

[oms.create]
limit = 15
per = "sec"

[oms.amend]
limit = 25
per = "min"

[oms.cancel]
limit = 30
per = "sec"

[plain]
cloid_prefix = "MYPLAIN"

[stinky]
levels = 8
min_spread_bps = 40.0
max_spread_bps = 200.0
large_fill_threshold_quote = 150.0
small_fill_wait_s = 0.8
large_fill_wait_s = 4.0
cloid_prefix = "MYSTINKY"
"""
        with tempfile.NamedTemporaryFile(suffix=".toml", delete=False, mode="w") as f:
            f.write(toml_content)
            f.flush()
            config = load_config(f.name)

        assert config.core.venue == Venue.BINANCE_USDM
        assert config.core.symbol == "ETHUSDT"
        assert config.core.trader == TraderId.STINKY
        assert config.volatility.half_life_s == 20.0
        assert config.volatility.min_spread_bps == 10.0
        assert config.pricing.levels == 3
        assert config.pricing.inventory_spread_ladder == [(1.5, 0.3), (2.5, 0.7)]
        assert config.risk.max_open_orders == 20
        assert config.oms.create.limit == 15
        assert config.oms.amend.limit == 25
        assert config.oms.amend.per == RateWindow.MIN
        assert config.oms.cancel.limit == 30
        assert config.plain.cloid_prefix == "MYPLAIN"
        assert config.stinky.levels == 8
        assert config.stinky.cloid_prefix == "MYSTINKY"

    def test_load_config_accepts_path_object(self) -> None:
        """load_config accepts Path objects."""
        toml_content = """\
[core]
venue = "Bybit"
symbol = "DOGEUSDT"
trader = "plain"

[pricing]
levels = 5
base_spread_bps = 15.0
max_inventory_quote = 500.0
inventory_spread_ladder = [[2.0, 0.5], [3.0, 0.8]]
"""
        with tempfile.NamedTemporaryFile(suffix=".toml", delete=False, mode="w") as f:
            f.write(toml_content)
            f.flush()
            config = load_config(Path(f.name))

        assert config.core.symbol == "DOGEUSDT"

    def test_repository_config_loads(self) -> None:
        """The checked-in runtime configuration matches the typed schema."""
        config_path = Path(__file__).parents[2] / "smm" / "config.toml"

        config = load_config(config_path)

        assert config.core.venue == Venue.BYBIT
        assert config.core.trader == TraderId.PLAIN

    def test_load_config_file_not_found(self) -> None:
        """load_config raises FileNotFoundError for missing file."""
        with pytest.raises(FileNotFoundError):
            load_config("/nonexistent/path/config.toml")
