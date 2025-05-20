from collections import deque

from smm.features.base_feature import BaseFeature

class TradesTickExcitement(BaseFeature):
    """Measures unusual trading activity by comparing recent volume to historical volume.
    
    This feature detects periods of heightened market activity by comparing the volume
    in a short-term window to the volume in a longer-term window. When the short-term
    volume is disproportionately high compared to what would be expected based on the
    long-term volume, it indicates potential market excitement or unusual activity.
    
    The excitement level is calculated as the ratio of:
    (actual short-term/long-term volume ratio) / (expected short-term/long-term volume ratio)
    
    When this ratio exceeds 1.0, it indicates higher than normal trading activity,
    which could signal:
    1. Breaking news or market events
    2. Large institutional orders being executed
    3. Potential price breakouts or trend changes
    4. Increased market volatility
    
    The feature uses a tick-based window approach, tracking a fixed number of recent trades.
    
    Args:
        short_window (int): Number of recent trades to consider for short-term volume.
                           Default is 100 trades.
        long_window (int): Number of recent trades to consider for long-term volume.
                          Default is 1000 trades.
        buffer (float): Multiplier applied to the expected ratio to account for normal
                       volume fluctuations. Default is 2.0, meaning the short-term volume
                       needs to be at least twice the expected amount to register excitement.
    """
    def __init__(self, short_window: int = 100, long_window: int = 1000, buffer: float = 2.0):
        super().__init__()

        self._short_window = short_window
        self._long_window = long_window
        
        # Calculate the expected volume ratio based on the short and long windows.
        # Buffer is the multiplier for the expected volume ratio to allow for 
        # small random fluctuations in volume without any underlying changes.
        self._expected_ratio = (short_window / long_window) * buffer

        self._sw_volume = 0.0
        self._lw_volume = 0.0
        
        self._short_trades = deque(maxlen=short_window)
        self._long_trades = deque(maxlen=long_window)
        
        self._value = 1.0

    def _update_short_window(self, time: float, is_buy: bool, px: float, sz: float) -> float:
        """Update the short window with a new trade.
        
        Args:
            time (float): Timestamp of the trade.
            is_buy (bool): Whether the trade was a buy (True) or sell (False).
            px (float): Price of the trade.
            sz (float): Size/quantity of the trade.
            
        Returns:
            float: The updated short window volume.
        """
        trade_volume = px * sz
        self._short_trades.append((time, is_buy, px, sz))
        self._sw_volume += trade_volume
        
        if len(self._short_trades) == self._short_window:
            _, _, sw_old_px, sw_old_sz = self._short_trades.popleft()
            sw_old_volume = sw_old_px * sw_old_sz
            self._sw_volume -= sw_old_volume

    def _update_long_window(self, time: float, is_buy: bool, px: float, sz: float) -> float:
        """Update the long window with a new trade.
        
        Args:
            time (float): Timestamp of the trade.
            is_buy (bool): Whether the trade was a buy (True) or sell (False).
            px (float): Price of the trade.
            sz (float): Size/quantity of the trade.
            
        Returns:
            float: The updated long window volume.
        """
        trade_volume = px * sz
        self._long_trades.append((time, is_buy, px, sz))
        self._lw_volume += trade_volume

        if len(self._long_trades) == self._long_window:
            _, _, lw_old_px, lw_old_sz = self._long_trades.popleft()
            lw_old_volume = lw_old_px * lw_old_sz
            self._lw_volume -= lw_old_volume

    def update(self, time: float, is_buy: bool, px: float, sz: float) -> float:
        """Process a new trade and update the excitement level.
        
        Args:
            time (float): Timestamp of the trade.
            is_buy (bool): Whether the trade was a buy (True) or sell (False).
            px (float): Price of the trade.
            sz (float): Size/quantity of the trade.
            
        Returns:
            float: The updated excitement level.
        """
        self._update_short_window(time, is_buy, px, sz)
        self._update_long_window(time, is_buy, px, sz)

        if self._lw_volume > 0:
            actual_volume_ratio = self._sw_volume / self._lw_volume
            
            if actual_volume_ratio > self._expected_ratio:
                self._value = actual_volume_ratio / self._expected_ratio
            else:
                self._value = 1.0
        
        return self._value


class TradesTimeExcitement:
    """Measures unusual trading activity by comparing recent volume to historical volume over time windows.
    
    Similar to TradesTickExcitement, this feature detects periods of heightened market activity,
    but uses time-based windows instead of tick-based windows. It compares the trading volume
    in a short time period (e.g., last 60 seconds) to the volume in a longer time period
    (e.g., last 10 minutes) to identify unusual spikes in activity.
    
    The excitement level is calculated as the ratio of:
    (actual short-term/long-term volume ratio) / (expected short-term/long-term volume ratio)
    
    When this ratio exceeds 1.0, it indicates higher than normal trading activity,
    which could signal:
    1. Breaking news or market events
    2. Large institutional orders being executed
    3. Potential price breakouts or trend changes
    4. Increased market volatility
    
    The time-based approach can be more responsive to sudden changes in market conditions
    compared to the tick-based approach, especially in markets with variable trading frequency.
    
    Args:
        short_window (float): Duration in seconds for the short-term window.
                             Default is 60.0 seconds.
        long_window (float): Duration in seconds for the long-term window.
                            Default is 600.0 seconds (10 minutes).
        buffer (float): Multiplier applied to the expected ratio to account for normal
                       volume fluctuations. Default is 2.0, meaning the short-term volume
                       needs to be at least twice the expected amount to register excitement.
    """
    def __init__(self, short_window: float = 60.0, long_window: float = 600.0, buffer: float = 2.0):
        self._short_window = short_window
        self._long_window = long_window
        
        # Calculate the expected volume ratio based on the short and long windows.
        # Buffer is the multiplier for the expected volume ratio to allow for 
        # small random fluctuations in volume without any underlying changes.
        self._expected_ratio = (short_window / long_window) * buffer

        self._sw_volume = 0.0
        self._lw_volume = 0.0
        
        self._short_trades = deque()
        self._long_trades = deque()
        
        self._value = 1.0

    def _update_short_window(self, time: float, is_buy: bool, px: float, sz: float) -> None:
        """Update the short time window with a new trade and remove expired trades.
        
        Args:
            time (float): Timestamp of the trade.
            is_buy (bool): Whether the trade was a buy (True) or sell (False).
            px (float): Price of the trade.
            sz (float): Size/quantity of the trade.
        """
        trade_volume = px * sz
        self._short_trades.append((time, is_buy, px, sz))
        self._sw_volume += trade_volume
        
        while self._short_trades and (time - self._short_trades[0][0]) > self._short_window:
            old_time, _, sw_old_px, sw_old_sz = self._short_trades.popleft()
            sw_old_volume = sw_old_px * sw_old_sz
            self._sw_volume -= sw_old_volume

    def _update_long_window(self, time: float, is_buy: bool, px: float, sz: float) -> None:
        """Update the long time window with a new trade and remove expired trades.
        
        Args:
            time (float): Timestamp of the trade.
            is_buy (bool): Whether the trade was a buy (True) or sell (False).
            px (float): Price of the trade.
            sz (float): Size/quantity of the trade.
        """
        trade_volume = px * sz
        self._long_trades.append((time, is_buy, px, sz))
        self._lw_volume += trade_volume

        while self._long_trades and (time - self._long_trades[0][0]) > self._long_window:
            old_time, _, lw_old_px, lw_old_sz = self._long_trades.popleft()
            lw_old_volume = lw_old_px * lw_old_sz
            self._lw_volume -= lw_old_volume

    def update(self, time: float, is_buy: bool, px: float, sz: float) -> float:
        """Process a new trade and update the excitement level.
        
        Args:
            time (float): Timestamp of the trade.
            is_buy (bool): Whether the trade was a buy (True) or sell (False).
            px (float): Price of the trade.
            sz (float): Size/quantity of the trade.
            
        Returns:
            float: The updated excitement level.
        """
        self._update_short_window(time, is_buy, px, sz)
        self._update_long_window(time, is_buy, px, sz)

        if self._lw_volume > 0:
            actual_volume_ratio = self._sw_volume / self._lw_volume
            
            if actual_volume_ratio > self._expected_ratio:
                self._value = actual_volume_ratio / self._expected_ratio
            else:
                self._value = 1.0
        
        return self._value
