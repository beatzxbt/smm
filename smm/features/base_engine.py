from abc import ABC, abstractmethod

from framework.tools.orderbook import Orderbook
from framework.base.internal_structs import TradeMsg, OrderbookMsg, TickerMsg

class BaseFeatureEngine(ABC):
    """Base class for feature engines that process market data.
    
    This abstract class defines the interface for feature engines that process
    different types of market data events to calculate trading signals.
    """
    
    def __init__(self, params: dict):
        """Initialize the feature engine.
        
        Args:
            params: Dictionary containing configuration parameters.
        """
        self._params = params

        self._fair_px = 0.0
        self._spread = 0.0

    @abstractmethod
    def update_trade(self, event: TradeMsg):
        """Update the feature engine with a new trade event.
        
        Args:
            event: Trade message containing trade data.
        """
        pass

    @abstractmethod
    def update_orderbook(self, event: OrderbookMsg, orderbook: Orderbook):
        """Update the feature engine with a new orderbook.
        
        Uniquely, both the event and the orderbook are provided so that the features 
        can chose which they want to directly act upon.

        Occasionally, strategies will directly need BBO update information, so this 
        leaves that optionality to the user.
        
        Args:
            event: Orderbook message containing update data.
            orderbook: The full orderbook object after the update.
        """
        pass

    @abstractmethod
    def update_ticker(self, event: TickerMsg):
        """Update the feature engine with a new ticker event.
        
        Args:
            event: Ticker message containing ticker data.
        """
        pass

    def get_fair_px(self) -> float:
        """Get the current fair price calculated by the feature engine.
        
        Returns:
            The current fair price as a float.
        """
        return self._fair_px
    
    def get_spread(self) -> float:
        """Get the current market spread calculated by the feature engine.
        
        Returns:
            The current market spread as a float.
        """
        return self._spread