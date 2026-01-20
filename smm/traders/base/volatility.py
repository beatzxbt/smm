"""EWMA volatility estimator for trade return streams.

Usage: feed TradeMsg updates and read `spread_bps()` for pricing.
Components: VolatilityEstimator with EWMA update logic.
"""

from __future__ import annotations

import math

from mm_toolbox.time import time_s

from framework.base.stream.models import Trade, TradeMsg
from smm.config import VolatilityConfig


class VolatilityEstimator:
    """EWMA volatility estimator based on absolute trade returns."""

    def __init__(self, config: VolatilityConfig) -> None:
        """Initialize the estimator.

        Args:
            config (VolatilityConfig): Volatility configuration settings.
        """
        self._config = config
        self._last_trade_price: float | None = None
        self._last_update_s: float | None = None
        self._pending_returns: list[float] = []
        self._ewma_value: float = 0.0

    def update_trade(self, trade: Trade) -> None:
        """Update the estimator with a single trade.

        Args:
            trade (Trade): Trade to process.
        """
        if self._last_trade_price is None:
            self._last_trade_price = trade.price
            self._last_update_s = trade.time_ms / 1000.0
            return

        abs_return = abs(trade.price / self._last_trade_price - 1.0)
        self._pending_returns.append(abs_return)
        self._last_trade_price = trade.price

        trade_time_s = trade.time_ms / 1000.0
        if self._last_update_s is None:
            self._last_update_s = trade_time_s
            return

        elapsed = trade_time_s - self._last_update_s
        if elapsed < self._config.update_interval_s:
            return

        mean_return = sum(self._pending_returns) / len(self._pending_returns)
        self._pending_returns.clear()
        self._last_update_s = trade_time_s
        self._ewma_value = self._apply_ewma(self._ewma_value, mean_return, elapsed)

    def update_msg(self, msg: TradeMsg) -> None:
        """Update the estimator with a trade message.

        Args:
            msg (TradeMsg): Trade message containing one or more trades.

        Returns:
            None.
        """
        for trade in msg.trades:
            self.update_trade(trade)

    def spread_bps(self) -> float:
        """Return the clamped volatility-derived spread in basis points.

        Returns:
            float: Spread in bps derived from EWMA volatility.
        """
        spread_bps = self._ewma_value * 10_000.0
        return float(
            max(
                self._config.min_spread_bps,
                min(spread_bps, self._config.max_spread_bps),
            )
        )

    def _apply_ewma(self, current: float, sample: float, elapsed_s: float) -> float:
        """Apply a half-life based EWMA update.

        Args:
            current (float): Current EWMA value.
            sample (float): New sample value.
            elapsed_s (float): Seconds since the last update.

        Returns:
            float: Updated EWMA value.
        """
        if elapsed_s <= 0.0:
            return current
        decay = math.log(0.5) / self._config.half_life_s
        alpha = 1.0 - math.exp(decay * elapsed_s)
        return (1.0 - alpha) * current + alpha * sample

    def ensure_fresh(self) -> None:
        """Push an update tick if no trades arrive for a while.

        Returns:
            None.
        """
        if self._last_update_s is None:
            return
        now_s = time_s()
        elapsed = now_s - self._last_update_s
        if elapsed < self._config.update_interval_s:
            return
        self._last_update_s = now_s
        self._ewma_value = self._apply_ewma(self._ewma_value, 0.0, elapsed)
