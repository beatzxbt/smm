"""Configuration models and TOML loader for the simple market maker.

Usage: edit `smm/config.toml` and load with `load_config()` at startup.
Components: core, volatility, pricing, risk, OMS, and trader-specific configs.
"""

from __future__ import annotations

from enum import StrEnum
from pathlib import Path
import tomllib

import msgspec

from framework.base.common import Symbol, Venue


class TraderId(StrEnum):
    """Supported trader identifiers.

    Attributes:
        PLAIN (str): Plain trader identifier.
        STINKY (str): Stinky trader identifier.
    """

    PLAIN = "plain"
    STINKY = "stinky"


class RateWindow(StrEnum):
    """Window units for OMS budgets.

    Attributes:
        SEC (str): Per-second budget window.
        MIN (str): Per-minute budget window.
    """

    SEC = "sec"
    MIN = "min"


class CoreConfig(msgspec.Struct):
    """Core configuration for venue, symbol, and trader choice.

    Attributes:
        venue (Venue): Exchange venue.
        symbol (str): Exchange symbol string.
        trader (TraderId): Trader identifier.
    """

    venue: Venue
    symbol: Symbol
    trader: TraderId

    def __post_init__(self) -> None:
        """Validate core configuration."""
        if not self.symbol.strip():
            raise ValueError("symbol must be non-empty")


class VolatilityConfig(msgspec.Struct):
    """Volatility model settings for spread adjustments.

    Attributes:
        half_life_s (float): EWMA half-life in seconds.
        min_spread_bps (float): Minimum spread bps clamp.
        max_spread_bps (float): Maximum spread bps clamp.
        update_interval_s (float): Update interval in seconds.
    """

    half_life_s: float = 10.0
    min_spread_bps: float = 5.0
    max_spread_bps: float = 200.0
    update_interval_s: float = 1.0

    def __post_init__(self) -> None:
        """Validate volatility settings."""
        if self.half_life_s <= 0.0:
            raise ValueError("half_life_s must be > 0")
        if self.min_spread_bps < 0.0:
            raise ValueError("min_spread_bps must be >= 0")
        if self.max_spread_bps <= 0.0:
            raise ValueError("max_spread_bps must be > 0")
        if self.min_spread_bps > self.max_spread_bps:
            raise ValueError("min_spread_bps must be <= max_spread_bps")
        if self.update_interval_s <= 0.0:
            raise ValueError("update_interval_s must be > 0")


class PricingConfig(msgspec.Struct):
    """Pricing settings shared by traders.

    Attributes:
        levels (int): Quote levels per side.
        base_spread_bps (float): Base spread in bps.
        max_inventory_quote (float): Max inventory in quote terms.
        inventory_spread_ladder (list[tuple[float, float]]): Spread multipliers by utilization.
    """

    levels: int
    base_spread_bps: float
    max_inventory_quote: float
    inventory_spread_ladder: list[tuple[float, float]]

    def __post_init__(self) -> None:
        """Validate pricing settings."""
        if self.levels <= 0:
            raise ValueError("levels must be > 0")
        if self.base_spread_bps < 0.0:
            raise ValueError("base_spread_bps must be >= 0")
        if self.max_inventory_quote <= 0.0:
            raise ValueError("max_inventory_quote must be > 0")

        ladder: list[tuple[float, float]] = []
        for entry in self.inventory_spread_ladder:
            if len(entry) != 2:
                raise ValueError("inventory_spread_ladder entries must be length 2")
            multiplier, util = float(entry[0]), float(entry[1])
            if multiplier <= 0.0:
                raise ValueError("inventory spread multiplier must be > 0")
            if not (0.0 <= util <= 1.0):
                raise ValueError("inventory utilization must be within [0, 1]")
            ladder.append((multiplier, util))
        self.inventory_spread_ladder = sorted(ladder, key=lambda x: x[1])


class RiskConfig(msgspec.Struct):
    """Risk controls enforced by the risk engine.

    Attributes:
        max_inventory_quote (float): Max inventory in quote terms.
        max_open_orders (int): Max number of live orders.
        max_order_distance_pct (float): Max order distance from mid price.
    """

    max_inventory_quote: float = 500.0
    max_open_orders: int = 10
    max_order_distance_pct: float = 1.0

    def __post_init__(self) -> None:
        """Validate risk settings."""
        if self.max_inventory_quote <= 0.0:
            raise ValueError("max_inventory_quote must be > 0")
        if self.max_open_orders <= 0:
            raise ValueError("max_open_orders must be > 0")
        if self.max_order_distance_pct <= 0.0:
            raise ValueError("max_order_distance_pct must be > 0")


class OmsBudgetConfig(msgspec.Struct):
    """Rate budget configuration for an OMS operation.

    Attributes:
        limit (int): Budgeted operations in the window.
        per (RateWindow): Window unit for the budget.
    """

    limit: int = 10
    per: RateWindow = RateWindow.SEC

    def __post_init__(self) -> None:
        """Validate OMS budget settings."""
        if self.limit <= 0:
            raise ValueError("limit must be > 0")


class OmsConfig(msgspec.Struct):
    """OMS configuration including rate budgets and buffers.

    Attributes:
        create (OmsBudgetConfig): Create order budget.
        amend (OmsBudgetConfig): Amend order budget.
        cancel (OmsBudgetConfig): Cancel order budget.
        price_buffer_bps (float): Price buffer in bps for amendments.
    """

    create: OmsBudgetConfig = msgspec.field(default_factory=OmsBudgetConfig)
    amend: OmsBudgetConfig = msgspec.field(default_factory=OmsBudgetConfig)
    cancel: OmsBudgetConfig = msgspec.field(default_factory=OmsBudgetConfig)
    price_buffer_bps: float = 5.0

    def __post_init__(self) -> None:
        """Validate OMS configuration."""
        if self.price_buffer_bps < 0.0:
            raise ValueError("price_buffer_bps must be >= 0")


class PlainConfig(msgspec.Struct):
    """Plain trader specific settings.

    Attributes:
        cloid_prefix (str): Client order id prefix.
    """

    cloid_prefix: str = "PLAIN"

    def __post_init__(self) -> None:
        """Validate plain trader settings."""
        if not self.cloid_prefix.strip():
            raise ValueError("cloid_prefix must be non-empty")


class StinkyConfig(msgspec.Struct):
    """Stinky trader specific settings.

    Attributes:
        levels (int): Quote levels per side.
        min_spread_bps (float): Minimum spread in bps.
        max_spread_bps (float): Maximum spread in bps.
        large_fill_threshold_quote (float): Quote value for large fills.
        small_fill_wait_s (float): Wait time for small fills.
        large_fill_wait_s (float): Wait time for large fills.
        cloid_prefix (str): Client order id prefix.
    """

    levels: int = 6
    min_spread_bps: float = 50.0
    max_spread_bps: float = 250.0
    large_fill_threshold_quote: float = 100.0
    small_fill_wait_s: float = 1.0
    large_fill_wait_s: float = 5.0
    cloid_prefix: str = "STINKY"

    def __post_init__(self) -> None:
        """Validate stinky trader settings."""
        if self.levels <= 0:
            raise ValueError("levels must be > 0")
        if self.min_spread_bps <= 0.0:
            raise ValueError("min_spread_bps must be > 0")
        if self.max_spread_bps <= 0.0:
            raise ValueError("max_spread_bps must be > 0")
        if self.min_spread_bps > self.max_spread_bps:
            raise ValueError("min_spread_bps must be <= max_spread_bps")
        if self.large_fill_threshold_quote <= 0.0:
            raise ValueError("large_fill_threshold_quote must be > 0")
        if self.small_fill_wait_s < 0.0:
            raise ValueError("small_fill_wait_s must be >= 0")
        if self.large_fill_wait_s < 0.0:
            raise ValueError("large_fill_wait_s must be >= 0")
        if not self.cloid_prefix.strip():
            raise ValueError("cloid_prefix must be non-empty")


class AppConfig(msgspec.Struct):
    """Top-level configuration for the SMM trader runtime.

    Attributes:
        core (CoreConfig): Core configuration.
        volatility (VolatilityConfig): Volatility settings.
        pricing (PricingConfig): Pricing settings.
        risk (RiskConfig): Risk settings.
        oms (OmsConfig): OMS settings.
        plain (PlainConfig): Plain trader overrides.
        stinky (StinkyConfig): Stinky trader overrides.
    """

    core: CoreConfig
    pricing: PricingConfig
    volatility: VolatilityConfig = msgspec.field(default_factory=VolatilityConfig)
    risk: RiskConfig = msgspec.field(default_factory=RiskConfig)
    oms: OmsConfig = msgspec.field(default_factory=OmsConfig)
    plain: PlainConfig = msgspec.field(default_factory=PlainConfig)
    stinky: StinkyConfig = msgspec.field(default_factory=StinkyConfig)


def load_config(path: str | Path) -> AppConfig:
    """Load application configuration from a TOML file.

    Args:
        path (str | Path): Path to the TOML configuration file.

    Returns:
        AppConfig: Parsed application configuration.
    """
    config_path = Path(path)
    with config_path.open("rb") as handle:
        raw = tomllib.load(handle)
    return msgspec.convert(raw, type=AppConfig)
