from typing import Optional
from abc import ABC, abstractmethod


class OrderIdGenerator(ABC):
    """
    Abstract base class for generating order IDs.

    This class provides a framework for generating order IDs with a specified
    length range. Subclasses should implement the `generate_random_str` method
    to define how the random string portion of the order ID is generated.

    Attributes
    ----------
    max_len : int
        The maximum length of the order ID.
    """
    
    def __init__(self, max_len: int) -> None:
        self.max_len = max_len

    @abstractmethod
    def generate_random_str(self, length: int) -> str:
        """
        Generates a random string of the specified length.

        This method must be implemented by subclasses.

        Parameters
        ----------
        length : int
            The length of the random string to generate.

        Returns
        -------
        str
            A random string of the specified length.
        """
        pass
    
    def generate_order_id(self, start: Optional[str]="", end: Optional[str]="") -> str:
        """
        Generates an order ID with optional starting and ending substrings.

        The generated order ID consists of the starting substring, a random
        string of appropriate length, and the ending substring.

        Parameters
        ----------
        start : str, optional
            The starting substring of the order ID (default is "").

        end : str, optional
            The ending substring of the order ID (default is "").

        Returns
        -------
        str
            The generated order ID.
        """
        start_len = len(start)
        end_len = len(end)
        return start + self.generate_random_str(self.max_len - (start_len + end_len)) + end    