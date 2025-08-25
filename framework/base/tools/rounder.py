import numpy as np
from msgspec import Struct
from typing import Optional, Self


class RounderConfig(Struct):
    round_bids_down: bool
    round_asks_up: bool
    round_sizes_up: bool

    @classmethod
    def default(self) -> Self:
        return RounderConfig(
            round_bids_down=True, round_asks_up=True, round_sizes_up=True
        )


class Rounder:
    """
    Provides rounding operations on prices and sizes according to specified tick and lot sizes.
    """

    def __init__(
        self, tick_size: float, lot_size: float, config: Optional[RounderConfig] = None
    ):
        if tick_size <= 0.0:
            raise ValueError("Invalid tick_size; must be greater than 0")
        if lot_size <= 0.0:
            raise ValueError("Invalid lot_size; must be greater than 0")

        self.tick_size = tick_size
        self.lot_size = lot_size
        self.config = config if config is not None else RounderConfig.default()

        # Precompute frequently used values
        self._inverse_tick_size = 1.0 / self.tick_size
        self._inverse_lot_size = 1.0 / self.lot_size
        self._tick_rounding_factor = 10.0 ** (np.ceil(-np.log10(self.tick_size)))
        self._lot_rounding_factor = 10.0 ** (np.ceil(-np.log10(self.lot_size)))

    def _round_to(self, num: float, factor: float) -> float:
        """Round a value to a specific decimal precision."""
        return round(num * factor) / factor

    def bid_price(self, price: float) -> float:
        """Round a price down to the nearest tick size multiple."""
        rounding_direction = np.floor if self.config.round_bids_down else np.ceil
        value = self.tick_size * rounding_direction(price * self._inverse_tick_size)
        return self._round_to(value, self._tick_rounding_factor)

    def ask_price(self, price: float) -> float:
        """Round a price up to the nearest tick size multiple."""
        rounding_direction = np.ceil if self.config.round_asks_up else np.floor
        value = self.tick_size * rounding_direction(price * self._inverse_tick_size)
        return self._round_to(value, self._tick_rounding_factor)

    def size(self, size: float) -> float:
        """Round a size down to the nearest lot size multiple."""
        rounding_direction = np.floor if self.config.round_sizes_up else np.ceil
        value = self.lot_size * rounding_direction(size * self._inverse_lot_size)
        return self._round_to(value, self._lot_rounding_factor)

    def bid_prices(self, prices: np.ndarray[float]) -> np.ndarray[float]:
        """Round an array of prices down to the nearest tick size multiple (bids)."""
        rounding_direction = np.floor if self.config.round_bids_down else np.ceil
        values = self.tick_size * rounding_direction(prices * self._inverse_tick_size)
        return (
            np.round(values * self._tick_rounding_factor) / self._tick_rounding_factor
        )

    def ask_prices(self, prices: np.ndarray[float]) -> np.ndarray[float]:
        """Round an array of prices up to the nearest tick size multiple (asks)."""
        rounding_direction = np.ceil if self.config.round_asks_up else np.floor
        values = self.tick_size * rounding_direction(prices * self._inverse_tick_size)
        return (
            np.round(values * self._tick_rounding_factor) / self._tick_rounding_factor
        )

    def sizes(self, sizes: np.ndarray[float]) -> np.ndarray[float]:
        """Round an array of sizes down to the nearest lot size multiple."""
        rounding_direction = np.floor if self.config.round_sizes_up else np.ceil
        values = self.lot_size * rounding_direction(sizes * self._inverse_lot_size)
        return np.round(values * self._lot_rounding_factor) / self._lot_rounding_factor
