# this is a highly modified version of the mm_toolbox v1.0, which isnt out yet
# so we need to keep it here for now. upon release, this should be 
# in the files to simply import 'from mm_toolbox.rounding import *'

import numpy as np

class Round:
    """
    Provides rounding operations on prices and sizes according to specified tick and lot sizes.
    """

    def __init__(self, tick_sz: float, lot_sz: float):
        """
        Initialize the Round class with given tick and lot sizes.

        Args:
            tick_sz (float): The minimum price increment.
            lot_sz (float): The minimum size increment.

        Raises:
            ValueError: If either tick_sz or lot_sz is <= 0.
        """
        if tick_sz <= 0.0:
            raise ValueError("Invalid tick_sz; must be greater than 0")
        if lot_sz <= 0.0:
            raise ValueError("Invalid lot_sz; must be greater than 0")

        self.tick_sz = tick_sz
        self.lot_sz = lot_sz

        # Precompute frequently used values
        self._inverse_tick_sz = 1.0 / self.tick_sz
        self._inverse_lot_sz = 1.0 / self.lot_sz
        self._tick_rounding_factor = 10.0 ** (np.ceil(-np.log10(self.tick_sz)))
        self._lot_rounding_factor = 10.0 ** (np.ceil(-np.log10(self.lot_sz)))

    def _round_to(self, num: float, factor: float) -> float:
        """
        Round a value to a specific decimal precision.

        Args:
            num (float): The value to round.
            factor (float): The rounding factor (10^decimals).

        Returns:
            float: The rounded value.
        """
        return round(num * factor) / factor

    def bid(self, px: float) -> float:
        """
        Round a price down to the nearest tick size multiple.

        Args:
            px (float): The price to be rounded down.

        Returns:
            float: The rounded (bid) price.
        """
        value = self.tick_sz * np.floor(px * self._inverse_tick_sz)
        return self._round_to(value, self._tick_rounding_factor)

    def ask(self, px: float) -> float:
        """
        Round a price up to the nearest tick size multiple.

        Args:
            px (float): The price to be rounded up.

        Returns:
            float: The rounded (ask) price.
        """
        value = self.tick_sz * np.ceil(px * self._inverse_tick_sz)
        return self._round_to(value, self._tick_rounding_factor)

    def sz(self, sz: float) -> float:
        """
        Round a size down to the nearest lot size multiple.

        Args:
            sz (float): The size to be rounded down.

        Returns:
            float: The rounded size.
        """
        value = self.lot_sz * np.floor(sz * self._inverse_lot_sz)
        return self._round_to(value, self._lot_rounding_factor)

    def bids(self, pxs: np.ndarray) -> np.ndarray:
        """
        Round an array of prices down to the nearest tick size multiple (bids).

        Args:
            pxs (np.ndarray): An array of prices to be rounded.

        Returns:
            np.ndarray: A new array containing rounded bid prices.
        """
        # Local copies of instance variables for faster access in the loop
        tick_sz = self.tick_sz
        inverse_tick_sz = self._inverse_tick_sz
        tick_rounding_factor = self._tick_rounding_factor
        
        # Vectorized operation
        values = tick_sz * np.floor(pxs * inverse_tick_sz)
        return np.round(values * tick_rounding_factor) / tick_rounding_factor

    def asks(self, pxs: np.ndarray) -> np.ndarray:
        """
        Round an array of prices up to the nearest tick size multiple (asks).

        Args:
            pxs (np.ndarray): An array of prices to be rounded.

        Returns:
            np.ndarray: A new array containing rounded ask prices.
        """
        # Local copies of instance variables for faster access in the loop
        tick_sz = self.tick_sz
        inverse_tick_sz = self._inverse_tick_sz
        tick_rounding_factor = self._tick_rounding_factor
        
        # Vectorized operation
        values = tick_sz * np.ceil(pxs * inverse_tick_sz)
        return np.round(values * tick_rounding_factor) / tick_rounding_factor

    def szs(self, szs: np.ndarray) -> np.ndarray:
        """
        Round an array of sizes down to the nearest lot size multiple.

        Args:
            szs (np.ndarray): An array of sizes to be rounded.

        Returns:
            np.ndarray: A new array containing rounded sizes.
        """
        # Local copies of instance variables for faster access in the loop
        lot_sz = self.lot_sz
        inverse_lot_sz = self._inverse_lot_sz
        lot_rounding_factor = self._lot_rounding_factor
        
        # Vectorized operation
        values = lot_sz * np.floor(szs * inverse_lot_sz)
        return np.round(values * lot_rounding_factor) / lot_rounding_factor
