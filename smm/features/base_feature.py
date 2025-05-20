from abc import ABC, abstractmethod

class BaseFeature(ABC):
    """Base class for all features that process market data.
    
    This abstract class defines the interface for features that process
    different types of market data events to calculate trading signals.
    """

    def __init__(self):
        """Initialize the feature.
        
        This constructor initializes the feature with a default value of 0.0.
        """
        self._value = 0.0

    @abstractmethod
    def update(self, **kwargs):
        """Update the feature with new data.
        
        Args:
            **kwargs: Additional keyword arguments.
        """
        pass

    def get_value(self) -> float:
        """Get the current value of the feature.
        
        Returns:
            The current value of the feature as a float.
        """
        return self._value