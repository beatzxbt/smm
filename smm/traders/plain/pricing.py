"""Plain pricing engine for mid-price following quotes.

Usage: instantiated by PlainTrader to generate desired quotes.
Components: mid-price tracking, volatility spreads, inventory adjustments.
"""

from __future__ import annotations

from framework.base.common import ClientOrderId, Instrument
from framework.base.stream.models import (
    DataMsg,
    OrderbookMsg,
    PositionMsg,
    TickerMsg,
    TradeMsg,
)
from mm_toolbox.rounding import Rounder

from smm.config import PlainConfig, PricingConfig
from smm.traders.base.pricing import BasePricingEngine
from smm.traders.base.types import DesiredOrder, DesiredState
from smm.traders.base.volatility import VolatilityEstimator


class PlainPricingEngine(BasePricingEngine):
    """Pricing engine that builds symmetric quotes around the mid price.

    Attributes:
        _plain_config (PlainConfig): Plain-specific settings.
        _rounder (Rounder): Price/size rounder.
        _volatility (VolatilityEstimator): Volatility estimator.
    """

    def __init__(
        self,
        instrument: Instrument,
        config: PricingConfig,
        plain_config: PlainConfig,
        rounder: Rounder,
        volatility: VolatilityEstimator,
    ) -> None:
        """Initialize the plain pricing engine.

        Args:
            instrument (Instrument): Instrument being traded.
            config (PricingConfig): Pricing configuration settings.
            plain_config (PlainConfig): Plain-specific configuration.
            rounder (Rounder): Price and size rounder.
            volatility (VolatilityEstimator): Volatility estimator for spreads.
        """
        super().__init__(instrument=instrument, config=config)
        self._plain_config = plain_config
        self._rounder = rounder
        self._volatility = volatility

        self._mid_price: float = 0.0
        self._position_size: float = 0.0

    def consume_msg(self, msg: DataMsg) -> None:
        """Consume a pricing-relevant stream message.

        Args:
            msg (DataMsg): Stream message consumed by pricing.

        """
        match msg:
            case TradeMsg():
                self._volatility.update_msg(msg)
            case OrderbookMsg():
                if not msg.bids or not msg.asks:
                    return
                best_bid = msg.bids[-1].price
                best_ask = msg.asks[0].price
                self._mid_price = (best_bid + best_ask) / 2.0
            case TickerMsg():
                return
            case PositionMsg():
                self._position_size = msg.size if msg.is_long else -msg.size

    def generate_desired_state(self) -> DesiredState:
        """Generate the desired state for plain quoting.

        Returns:
            DesiredState: Desired state with bid and ask orders.
        """
        self._volatility.ensure_fresh()
        desired = DesiredState.empty(self.instrument)
        if self._mid_price <= 0.0:
            return desired

        levels = self.config.levels
        quote_per_level = self.config.max_inventory_quote / (2.0 * levels)
        base_spread_bps = max(
            self.config.base_spread_bps, self._volatility.spread_bps()
        )
        spread_multiplier = self._inventory_spread_multiplier()
        spread_bps = base_spread_bps * spread_multiplier

        inventory_util = self._inventory_utilization()
        reduce_buy = self._position_size > 0.0
        reduce_sell = self._position_size < 0.0

        for level in range(levels):
            level_spread = (level + 1) * (spread_bps / 10_000.0)
            bid_price = self._rounder.bid(self._mid_price * (1.0 - level_spread))
            ask_price = self._rounder.ask(self._mid_price * (1.0 + level_spread))

            size_quote = quote_per_level
            size_base = self._rounder.size(size_quote / self._mid_price)
            bid_size = size_base
            ask_size = size_base
            if level == 0 and inventory_util > 0.0:
                scale = max(0.0, 1.0 - inventory_util)
                if reduce_buy:
                    bid_size = self._rounder.size(size_base * scale)
                elif reduce_sell:
                    ask_size = self._rounder.size(size_base * scale)

            if bid_size > 0.0:
                desired.bids.append(
                    DesiredOrder(
                        price=bid_price,
                        is_buy=True,
                        size=bid_size,
                        is_maker=True,
                        reduce_only=False,
                        client_order_id=ClientOrderId(
                            f"{self._plain_config.cloid_prefix}{level:02d}B"
                        ),
                    )
                )
            if ask_size > 0.0:
                desired.asks.append(
                    DesiredOrder(
                        price=ask_price,
                        is_buy=False,
                        size=ask_size,
                        is_maker=True,
                        reduce_only=False,
                        client_order_id=ClientOrderId(
                            f"{self._plain_config.cloid_prefix}{level:02d}S"
                        ),
                    )
                )

        return desired

    def _inventory_utilization(self) -> float:
        """Calculate inventory utilization as a fraction of max.

        Returns:
            float: Utilization in [0, 1].
        """
        if self._mid_price <= 0.0:
            return 0.0
        inventory_quote = abs(self._position_size) * self._mid_price
        return min(1.0, inventory_quote / self.config.max_inventory_quote)

    def _inventory_spread_multiplier(self) -> float:
        """Return the spread multiplier based on inventory ladder.

        Returns:
            float: Spread multiplier for current inventory utilization.
        """
        util = self._inventory_utilization()
        multiplier = 1.0
        for entry_multiplier, threshold in self.config.inventory_spread_ladder:
            if util >= threshold:
                multiplier = entry_multiplier
        return multiplier
