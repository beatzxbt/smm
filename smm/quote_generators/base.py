from abc import ABC, abstractmethod
from numpy.typing import NDArray
from typing import List, Tuple, Dict

from smm.sharedstate import SmmSharedState
from frameworks.tools.trading.rounding import round_ceil, round_floor


class QuoteGenerator(ABC):
    """
    A base class for generating quotes for a trading strategy.

    This class provides methods for calculating various trading metrics,
    converting units, and generating single quotes. The abstract method
    `generate_orders` should be implemented by subclasses to generate a 
    list of orders based on specific strategy logic.
    """
    def __init__(self, ss: SmmSharedState) -> None:
        """
        Initializes the QuoteGenerator class with shared state information.

        Parameters
        ----------
        ss : SmmSharedState
            An instance of SmmSharedState containing shared state information.
        """
        self.data = ss.data
        self.params = ss.parameters

    @property
    def mid_price(self) -> float:
        """
        Returns the mid price of the order book.

        Returns
        -------
        float
            The mid price of the order book.
        """
        return self.data["orderbook"].get_mid()

    @property
    def wmid_price(self) -> float:
        """
        Returns the weighted mid price of the order book.

        Returns
        -------
        float
            The weighted mid price of the order book.
        """
        return self.data["orderbook"].get_wmid()

    @property
    def live_best_bid(self) -> NDArray:
        """
        Returns the live best bid from the order book.

        Returns
        -------
        NDArray
            The live best bid from the order book.
        """
        return self.data["orderbook"].bba[0]

    @property
    def live_best_ask(self) -> NDArray:
        """
        Returns the live best ask from the order book.

        Returns
        -------
        NDArray
            The live best ask from the order book.
        """
        return self.data["orderbook"].bba[1]

    @property
    def inventory_delta(self) -> float:
        """
        Returns the inventory delta as a fraction of the maximum position.

        Returns
        -------
        float
            The inventory delta.
        """
        size_to_dollar = (
            self.data["current_position"]["size"] * self.data["current_position"]["price"]
        )
        return size_to_dollar / self.params["max_position"]

    @property
    def total_orders(self) -> int:
        """
        Returns the total number of orders.

        Returns
        -------
        int
            The total number of orders.
        """
        return self.params["total_orders"]

    @property
    def max_position(self) -> float:
        """
        Converts USD position in parameters to quote size.

        Returns
        -------
        float
            The maximum position size in quotes.
        """
        return self.params["max_position"] / self.data["orderbook"].get_mid()

    def bps_to_decimal(self, bps: float) -> float:
        """
        Converts basis points to decimal.

        Parameters
        ----------
        bps : float
            The basis points to convert.

        Returns
        -------
        float
            The equivalent decimal value.
        """
        return bps / 10000

    def bps_offset_to_decimal(self, bps: float) -> float:
        """
        Converts basis points offset from midprice to decimal.

        Parameters
        ----------
        bps : float
            The basis points offset.

        Returns
        -------
        float
            The equivalent decimal price.
        """
        return self.mid_price + (self.mid_price * self.bps_to_decimal(bps))

    def offset_to_decimal(self, offset: float) -> float:
        """
        Converts an offset to decimal price.

        Parameters
        ----------
        offset : float
            The offset to convert.

        Returns
        -------
        float
            The equivalent decimal price.
        """
        return self.mid_price + (self.mid_price * offset)

    def round_bid(self, bid_price: float) -> float:
        """
        Round the bid price down to the nearest multiple of the tick size.

        Parameters
        ----------
        bid_price : float
            The bid price to be rounded.

        Returns
        -------
        float
            The bid price rounded down to the nearest multiple of the tick size.

        Examples
        --------
        >>> self.data["tick_size"] = 0.01
        >>> self.round_bid(10.057)
        10.05
        """
        return round_floor(num=bid_price, step_size=self.data["tick_size"])

    def round_ask(self, ask_price: float) -> float:
        """
        Round the ask price up to the nearest multiple of the tick size.

        Parameters
        ----------
        ask_price : float
            The ask price to be rounded.

        Returns
        -------
        float
            The ask price rounded up to the nearest multiple of the tick size.

        Examples
        --------
        >>> self.data["tick_size"] = 0.01
        >>> self.round_ask(10.057)
        10.06
        """
        return round_ceil(num=ask_price, step_size=self.data["tick_size"])

    def round_size(self, size: float) -> float:
        """
        Round the size up to the nearest multiple of the lot size.

        Parameters
        ----------
        size : float
            The size to be rounded.

        Returns
        -------
        float
            The size rounded up to the nearest multiple of the lot size.

        Examples
        --------
        >>> self.data["lot_size"] = 0.001
        >>> self.round_size(1.2345)
        1.235
        """
        return round_ceil(num=size, step_size=self.data["lot_size"])
  
    def generate_single_quote(
        self, side: float, orderType: float, price: float, size: float
    ) -> Dict:
        """
        Generates a single quote dictionary.

        Parameters
        ----------
        side : float
            The side of the order.
            
        orderType : float
            The type of the order.
            
        price : float
            The price of the order.

        size : float
            The size of the order.


        Returns
        -------
        dict
            A dictionary representing the quote.
        """
        return {
            "side": side,
            "orderType": orderType,
            "price": price,
            "size": size,
        }

    @abstractmethod
    def generate_orders(self, fp_skew: float, vol: float) -> List[Dict]:
        """
        Generates a list of orders based on the strategy.

        This method should be implemented by subclasses to generate a 
        list of orders based on specific strategy logic. The Order Management
        System (OMS) will prioritize orders at the top of the list more,
        so any custom ordering required for the strategy should be implemented here.

        Parameters
        ----------
        fp_skew : float
            The fair price skew.
            
        vol : float
            The volatility.

        Returns
        -------
        List[Dict]
            A list of orders to be placed.
        """
        pass
