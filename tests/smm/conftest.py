"""SMM-specific test fixtures.

Provides fixtures for testing SMM configuration and trader components.
"""

from __future__ import annotations

import pytest
import pytest_asyncio

from framework.base.common import Instrument, Symbol, Venue
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


@pytest_asyncio.fixture
async def scripted_exchange(test_logger):
    """Start a scripted exchange server and build a Bybit exchange against it.

    The exchange is configured with test credentials and a scripted auth
    response so WebSocket operations can flow without live services. The
    public session transcript is loaded so instrument collection requests
    made during trader construction resolve deterministically.

    Returns:
        tuple[ScriptedExchangeServer, BybitExchange]: Server and exchange pair.
    """
    from pathlib import Path

    from framework.base.trading.exchange import VenueEndpoints
    from framework.bybit.trading.exchange import BybitExchange
    from tests.framework.support import ScriptedExchangeServer

    public_session = (
        Path(__file__).resolve().parents[1]
        / "framework"
        / "fixtures"
        / "bybit"
        / "public_session.jsonl"
    )
    server = ScriptedExchangeServer()
    await server.start()
    server.load_jsonl(public_session)
    server.add_http_response(
        "GET",
        "/v5/market/time",
        {"retCode": 0, "retMsg": "OK", "result": {"timeMs": "1700000000000"}},
    )
    server.add_ws_response("auth", {"retCode": 0, "retMsg": "OK", "op": "auth"})
    exchange = BybitExchange(
        logger=test_logger,
        load_secrets=False,
        endpoints=VenueEndpoints(
            http=server.http_url,
            trading_ws=server.ws_url,
            public_ws=server.ws_url,
            private_ws=server.ws_url,
            time=f"{server.http_url}/v5/market/time",
        ),
    )
    exchange.load_secrets = True
    exchange.http_client.load_secrets = True
    exchange.ws_client.load_secrets = True
    setattr(exchange.http_client, "key", "test-key")
    setattr(exchange.ws_client, "key", "test-key")
    setattr(exchange.http_client, "secret", "test-secret")
    setattr(exchange.ws_client, "secret", "test-secret")
    try:
        yield server, exchange
    finally:
        await exchange.close_clients()
        await server.close()


@pytest.fixture
def make_trader(test_logger):
    """Build a trader wired to a scripted-exchange dependency graph.

    Returns:
        Callable: Async factory building a trader from a server/exchange pair.
    """
    from framework.bybit.stream.manager import (
        BybitMarketStreamManager,
        BybitPrivateStreamManager,
    )
    from mm_toolbox.ringbuffer import GenericRingBuffer
    from mm_toolbox.rounding import Rounder, RounderConfig

    from tests.smm.support import make_instrument

    async def _make_trader(
        server,
        exchange,
        trader_cls,
        config: AppConfig,
        *,
        buffer: GenericRingBuffer | None = None,
        instrument: Instrument | None = None,
    ):
        if instrument is None:
            instrument = make_instrument()
        buffer = buffer or GenericRingBuffer(256)
        rounder = Rounder(
            RounderConfig.default(
                tick_size=instrument.tick_size, lot_size=instrument.lot_size
            )
        )
        market_data = await BybitMarketStreamManager.create(
            exchange, test_logger, buffer
        )
        private_data = await BybitPrivateStreamManager.create(
            exchange, test_logger, buffer
        )
        return trader_cls(
            config=config,
            logger=test_logger,
            exchange=exchange,
            instrument=instrument,
            rounder=rounder,
            market_data=market_data,
            private_data=private_data,
            producer_buffer=buffer,
        )

    return _make_trader


@pytest.fixture
def plain_app_config() -> AppConfig:
    """Provide a plain trader config with high order budgets.

    Uses a max inventory quote of 300000 so a 30000 mid produces 1.0 base
    units per level, keeping expected values readable.

    Returns:
        AppConfig: Plain trader configuration.
    """
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
            inventory_spread_ladder=[(2.0, 0.5), (3.0, 0.8)],
        ),
        risk=RiskConfig(max_inventory_quote=300_000.0),
        oms=_high_budget_oms(),
        plain=PlainConfig(),
    )


@pytest.fixture
def plain_one_level_config() -> AppConfig:
    """Provide a single-level plain config with high order budgets.

    Used by the boot test where a minimal quote set keeps wire assertions
    tractable.

    Returns:
        AppConfig: Single-level plain trader configuration.
    """
    return AppConfig(
        core=CoreConfig(
            venue=Venue.BYBIT,
            symbol=Symbol("BTCUSDT"),
            trader=TraderId.PLAIN,
        ),
        pricing=PricingConfig(
            levels=1,
            base_spread_bps=15.0,
            max_inventory_quote=300_000.0,
            inventory_spread_ladder=[],
        ),
        oms=_high_budget_oms(),
        plain=PlainConfig(),
    )


@pytest.fixture
def stinky_app_config() -> AppConfig:
    """Provide a stinky trader config with high order budgets.

    Uses a max inventory quote of 360000 so a 30000 mid produces 1.0 base
    units per level, keeping expected values readable.

    Returns:
        AppConfig: Stinky trader configuration.
    """
    return AppConfig(
        core=CoreConfig(
            venue=Venue.BYBIT,
            symbol=Symbol("BTCUSDT"),
            trader=TraderId.STINKY,
        ),
        pricing=PricingConfig(
            levels=6,
            base_spread_bps=15.0,
            max_inventory_quote=360_000.0,
            inventory_spread_ladder=[],
        ),
        risk=RiskConfig(
            max_inventory_quote=360_000.0,
            max_open_orders=12,
            max_order_distance_pct=5.0,
        ),
        oms=_high_budget_oms(),
        stinky=StinkyConfig(),
    )


def _high_budget_oms() -> OmsConfig:
    """Build an OMS config with effectively unbounded rate budgets.

    Returns:
        OmsConfig: OMS config with 1000 ops/sec per operation.
    """
    budget = OmsBudgetConfig(limit=1000, per=RateWindow.SEC)
    return OmsConfig(create=budget, amend=budget, cancel=budget)
