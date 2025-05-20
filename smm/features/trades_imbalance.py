from collections import deque

from smm.features.base_feature import BaseFeature

class TradesTickImbalance(BaseFeature):
    """Measures the imbalance between buy and sell trade volume over a fixed number of trades.
    
    This feature calculates the ratio of buy volume to sell volume over a specified number
    of recent trades. It provides insight into the directional pressure in the market by
    comparing the monetary value (price * size) of buy trades versus sell trades.
    
    A value greater than 1.0 indicates more buying pressure (buy volume exceeds sell volume),
    while a value less than 1.0 indicates more selling pressure (sell volume exceeds buy volume).
    A value of exactly 1.0 represents a perfectly balanced market.
    
    This feature can be used to:
    1. Identify potential short-term price trends
    2. Detect accumulation or distribution patterns
    3. Gauge market sentiment and order flow imbalances
    4. Identify potential reversal points when combined with price action
    
    The feature uses a tick-based window approach, tracking a fixed number of recent trades.
    
    Args:
        window (int): Number of recent trades to consider for the imbalance calculation.
                     Default is 100 trades.
    """
    def __init__(self, window: int = 100):
        super().__init__()
        self._window = window
        self._trades = deque(maxlen=window)

        self._buy_value = 0.0
        self._sell_value = 0.0

    def update(self, time: float, is_buy: bool, px: float, sz: float) -> float:
        """Process a new trade and update the imbalance ratio.
        
        Args:
            time (float): Timestamp of the trade.
            is_buy (bool): Whether the trade was a buy (True) or sell (False).
            px (float): Price of the trade.
            sz (float): Size/quantity of the trade.
            
        Returns:
            float: The updated imbalance ratio.
        """
        if is_buy:
            self._buy_value += sz * px
        else:
            self._sell_value += sz * px

        if len(self._trades) == self._window:
            _, old_is_buy, old_px, old_sz = self._trades.popleft()
            if old_is_buy:
                self._buy_value -= old_sz * old_px
            else:
                self._sell_value -= old_sz * old_px

        self._trades.append((time, is_buy, px, sz))

        self._value = self._buy_value / self._sell_value
        return self._value
    

class TradesTimeImbalance:
    """Measures the imbalance between buy and sell trade volume over a time window.
    
    Similar to TradesTickImbalance, this feature calculates the ratio of buy volume to sell volume,
    but uses a time-based window instead of a tick-based window. It compares the monetary value
    (price * size) of buy trades versus sell trades over a specified time period.
    
    A value greater than 1.0 indicates more buying pressure (buy volume exceeds sell volume),
    while a value less than 1.0 indicates more selling pressure (sell volume exceeds buy volume).
    A value of exactly 1.0 represents a perfectly balanced market.
    
    This feature can be used to:
    1. Identify potential short-term price trends
    2. Detect accumulation or distribution patterns
    3. Gauge market sentiment and order flow imbalances
    4. Identify potential reversal points when combined with price action
    
    The time-based approach can be more responsive to sudden changes in market conditions
    compared to the tick-based approach, especially in markets with variable trading frequency.
    
    Args:
        window (float): Duration in seconds for the time window. Default is 60.0 seconds.
    """
    def __init__(self, window: float = 60.0):
        self._window = window
        self._trades = deque()
        
        self._buy_value = 0.0
        self._sell_value = 0.0
        
    def update(self, time: float, is_buy: bool, px: float, sz: float) -> float:
        """Process a new trade and update the imbalance ratio.
        
        Args:
            time (float): Timestamp of the trade.
            is_buy (bool): Whether the trade was a buy (True) or sell (False).
            px (float): Price of the trade.
            sz (float): Size/quantity of the trade.
            
        Returns:
            float: The updated imbalance ratio.
        """
        self._trades.append((time, is_buy, px, sz))
        
        if is_buy:
            self._buy_value += sz * px
        else:
            self._sell_value += sz * px
        
        while self._trades and (time - self._trades[0][0]) > self._window:
            old_time, old_is_buy, old_px, old_sz = self._trades.popleft()
            if old_is_buy:
                self._buy_value -= old_sz * old_px
            else:
                self._sell_value -= old_sz * old_px
        
        if self._sell_value > 0:
            self._value = self._buy_value / self._sell_value
        else:
            self._value = float('inf') if self._buy_value > 0 else 0.0
            
        return self._value
    