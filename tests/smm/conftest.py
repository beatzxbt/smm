"""SMM-specific test fixtures.

Provides fixtures for testing SMM configuration and trader components.
"""

from __future__ import annotations

import pytest

from framework.base.common import Symbol, Venue
from smm.config import (
    AppConfig,
    CoreConfig,
    OmsBudgetConfig,
    OmsConfig,
    PlainConfig,
    PricingConfig,
    RiskConfig,
    StinkyConfig,
    TraderId,
    VolatilityConfig,
)


@pytest.fixture
def default_core_config() -> CoreConfig:
    """Provide default core configuration for tests.

    Returns:
        CoreConfig: Default core configuration.
    """
    return CoreConfig(
        venue=Venue.BYBIT,
        symbol=Symbol("SOLUSDT"),
        trader=TraderId.PLAIN,
    )


@pytest.fixture
def default_volatility_config() -> VolatilityConfig:
    """Provide default volatility configuration for tests.

    Returns:
        VolatilityConfig: Default volatility configuration.
    """
    return VolatilityConfig()


@pytest.fixture
def default_pricing_config() -> PricingConfig:
    """Provide default pricing configuration for tests.

    Returns:
        PricingConfig: Default pricing configuration.
    """
    return PricingConfig(
        levels=5,
        base_spread_bps=15.0,
        max_inventory_quote=500.0,
        inventory_spread_ladder=[(2.0, 0.5), (3.0, 0.8)],
    )


@pytest.fixture
def default_risk_config() -> RiskConfig:
    """Provide default risk configuration for tests.

    Returns:
        RiskConfig: Default risk configuration.
    """
    return RiskConfig()


@pytest.fixture
def default_oms_budget_config() -> OmsBudgetConfig:
    """Provide default OMS budget configuration for tests.

    Returns:
        OmsBudgetConfig: Default OMS budget configuration.
    """
    return OmsBudgetConfig()


@pytest.fixture
def default_oms_config() -> OmsConfig:
    """Provide default OMS configuration for tests.

    Returns:
        OmsConfig: Default OMS configuration.
    """
    return OmsConfig()


@pytest.fixture
def default_plain_config() -> PlainConfig:
    """Provide default plain trader configuration for tests.

    Returns:
        PlainConfig: Default plain trader configuration.
    """
    return PlainConfig()


@pytest.fixture
def default_stinky_config() -> StinkyConfig:
    """Provide default stinky trader configuration for tests.

    Returns:
        StinkyConfig: Default stinky trader configuration.
    """
    return StinkyConfig()


@pytest.fixture
def default_app_config(
    default_core_config: CoreConfig,
    default_pricing_config: PricingConfig,
) -> AppConfig:
    """Provide default application configuration for tests.

    Returns:
        AppConfig: Default application configuration.
    """
    return AppConfig(
        core=default_core_config,
        pricing=default_pricing_config,
    )
