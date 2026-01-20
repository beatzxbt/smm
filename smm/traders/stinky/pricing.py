"""Stinky pricing engine with wide linear spreads.

Usage: instantiated by StinkyTrader to generate wide quotes.
Components: mid-price tracking, linear spread ladder, quote sizing.
"""

from __future__ import annotations

from framework.base.common import Instrument
from framework.base.stream.models import OrderbookMsg, PositionMsg, TickerMsg, TradeMsg
from mm_toolbox.rounding import Rounder

from smm.config import PricingConfig, StinkyConfig
from smm.traders.base.pricing import BasePricingEngine
from smm.traders.base.types import DesiredOrder, DesiredState
from smm.traders.base.volatility import VolatilityEstimator


class StinkyPricingEngine(BasePricingEngine):
    """Pricing engine that places wide linear quotes.

    Attributes:
        _stinky_config (StinkyConfig): Stinky-specific settings.
        _rounder (Rounder): Price/size rounder.
        _volatility (VolatilityEstimator): Volatility estimator.
    """

    def __init__(
        self,
        instrument: Instrument,
        config: PricingConfig,
        stinky_config: StinkyConfig,
        rounder: Rounder,
        volatility: VolatilityEstimator,
    ) -> None:
        """Initialize the stinky pricing engine.

        Args:
            instrument (Instrument): Instrument being traded.
            config (PricingConfig): Shared pricing configuration.
            stinky_config (StinkyConfig): Stinky-specific configuration.
            rounder (Rounder): Price and size rounder.
            volatility (VolatilityEstimator): Volatility estimator for future use.
        """
        super().__init__(instrument=instrument, config=config)
        self._stinky_config = stinky_config
        self._rounder = rounder
        self._volatility = volatility

        self._mid_price: float = 0.0

    def consume_trade(self, msg: TradeMsg) -> None:
        """Consume a trade message.

        Args:
            msg (TradeMsg): Trade message.

        Returns:
            None.
        """
        self._volatility.update_msg(msg)

    def consume_orderbook(self, msg: OrderbookMsg) -> None:
        """Consume an orderbook message.

        Args:
            msg (OrderbookMsg): Orderbook message.

        Returns:
            None.
        """
        if not msg.bids or not msg.asks:
            return
        best_bid = msg.bids[-1].price
        best_ask = msg.asks[0].price
        self._mid_price = (best_bid + best_ask) / 2.0

    def consume_ticker(self, msg: TickerMsg) -> None:
        """Consume a ticker message.

        Args:
            msg (TickerMsg): Ticker message.

        Returns:
            None.
        """
        return

    def consume_position(self, msg: PositionMsg) -> None:
        """Consume a position message.

        Args:
            msg (PositionMsg): Position message.

        Returns:
            None.
        """
        return

    def generate_desired_state(self) -> DesiredState:
        """Generate the desired state for stinky quoting.

        Returns:
            DesiredState: Desired state with bid and ask orders.
        """
        desired = DesiredState.empty(self.instrument)
        if self._mid_price <= 0.0:
            return desired

        levels = self._stinky_config.levels or self.config.levels
        quote_per_level = self.config.max_inventory_quote / (2.0 * levels)
        spread_range = (
            self._stinky_config.max_spread_bps - self._stinky_config.min_spread_bps
        )

        for level in range(levels):
            if levels == 1:
                level_spread_bps = self._stinky_config.min_spread_bps
            else:
                level_spread_bps = self._stinky_config.min_spread_bps + (
                    spread_range * (level / (levels - 1))
                )
            level_spread = level_spread_bps / 10_000.0
            bid_price = self._rounder.bid(self._mid_price * (1.0 - level_spread))
            ask_price = self._rounder.ask(self._mid_price * (1.0 + level_spread))

            size_base = self._rounder.size(quote_per_level / self._mid_price)
            if size_base <= 0.0:
                continue

            desired.bids.append(
                DesiredOrder(
                    price=bid_price,
                    is_buy=True,
                    size=size_base,
                    is_maker=True,
                    reduce_only=False,
                    client_order_id=f"{self._stinky_config.cloid_prefix}{level:02d}B",
                )
            )
            desired.asks.append(
                DesiredOrder(
                    price=ask_price,
                    is_buy=False,
                    size=size_base,
                    is_maker=True,
                    reduce_only=False,
                    client_order_id=f"{self._stinky_config.cloid_prefix}{level:02d}S",
                )
            )

        return desired
