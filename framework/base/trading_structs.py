import numpy as np
from numba.experimental import jitclass
from numba.types import uint32, int32, float64, Array
from typing import Dict, List, Union, Any, Optional
from dataclasses import dataclass
from numpy_ringbuffer import RingBuffer
from numba.experimental import jitclass


@jitclass
class Orderbook:
    """
    An orderbook class, maintaining separate arrays for bid and
    ask orders with functionality to initialize, update, and sort
    the orders.

    Attributes
    ----------
    size : int
        The maximum number of bid/ask pairs the order book will hold.

    asks : Array
        Array to store ask orders, each with price and quantity.

    bids : Array
        Array to store bid orders, each with price and quantity.

    bba : Array
        Array to store best bid and ask, each with price and quantity.
    """

    size: uint32
    asks: float64[:, :]
    bids: float64[:, :]
    bba: float64[:, :]
    seq_id: int32

    def __init__(self, size: int) -> None:
        """
        Constructs all the necessary attributes for the orderbook object.

        Parameters
        ----------
        size : int
            Size of the order book (number of orders to store).
        """
        self.size: int = size
        self.asks: np.ndarray = np.zeros((self.size, 2), dtype=float64)
        self.bids: np.ndarray = np.zeros((self.size, 2), dtype=float64)
        self.bba: np.ndarray = np.zeros((2, 2), dtype=float64)
        self.seq_id: int = 0
    
    def reset(self) -> None:
        """
        Sets all attribute values back to 0 
        """
        self.asks.fill(0)
        self.bids.fill(0)
        self.bba.fill(0)
        self.seq_id = 0

    def recordable(self) -> Dict[str, Union[float, np.ndarray]]:
        """
        Unwraps the internal structures into widely-used Python structures
        for easy recordability (databases, logging, debugging etc). 

        Returns
        -------
        Dict
            A dict containing the current state of the orderbook.
        """
        return {
            "seq_id": np.float64(self.seq_id),
        }


class Order:
    """
    A class to represent an order.

    Attributes
    ----------
    symbol : str
        The trading symbol of the order.

    side : float
        The side of the order (buy/sell).

    orderType : float
        The type of the order.

    timeInForce : float
        The time in force for the order.

    size : float
        The size of the order.

    price : Optional[float]
        The price of the order.

    orderId : Optional[str]
        The order ID.

    clientOrderId : Optional[str]
        The client order ID.
    """

    def __init__(
        self,
        symbol: str = None,
        side: float = None,
        orderType: float = None,
        timeInForce: float = None,
        size: float = None,
        price: Optional[float] = None,
        orderId: Optional[str] = None,
        clientOrderId: Optional[str] = None,
    ) -> None:
        self._symbol = symbol
        self._side = side
        self._orderType = orderType
        self._timeInForce = timeInForce
        self._size = size


class Position:
    def __init__(
        self,
        symbol: str = None,
        side: float = None,
        price: float = None,
        size: float = None,
        uPnl: float = None,
    ) -> None:
        self._symbol = symbol
        self._side = side
        self._price = price
        self._size = size
        self._uPnl = uPnl

    @property
    def symbol(self) -> str:
        return self._symbol

    @property
    def side(self) -> float:
        return self._side

    @property
    def price(self) -> float:
        return self._price

    @property
    def size(self) -> float:
        return self._size

    @property
    def uPnl(self) -> float:
        return self._uPnl

    @property
    def is_empty(self) -> bool:
        return isinstance(self._size, float) and self._size == 0.0

    @property
    def in_profit(self) -> bool:
        return isinstance(self._uPnl, float) and self._uPnl > 0.0

    def __bool__(self) -> bool:
        return any(
            attr is not None
            for attr in [self._symbol, self._side, self._price, self._size, self._uPnl]
        )


class Ticker:
    def __init__(
        self,
        fundingTime: float = None,
        fundingRate: float = None,
        markPrice: float = None,
        indexPrice: float = None,
    ) -> None:
        self._fundingTime = fundingTime
        self._fundingRate = fundingRate
        self._markPrice = markPrice
        self._indexPrice = indexPrice

    @property
    def fundingTime(self) -> float:
        return self._fundingTime

    @property
    def fundingRate(self) -> float:
        return self._fundingRate

    @property
    def markPrice(self) -> float:
        return self._markPrice

    @property
    def indexPrice(self) -> float:
        return self._indexPrice

    @property
    def fundingRateBps(self) -> float:
        return self._fundingRate * 10_000.0

    def __bool__(self) -> bool:
        return any(
            attr is not None
            for attr in [
                self._fundingTime,
                self._fundingRate,
                self._markPrice,
                self._indexPrice,
            ]
        )

    def __repr__(self) -> str:
        return (
            f"Ticker(fundingTime={self.fundingTime}, fundingRate={self.fundingRate}, "
            f"markPrice={self.markPrice}, indexPrice={self.indexPrice})"
        )


@dataclass
class Trade:
    timestamp: float
    side: float
    price: float
    size: float

    @staticmethod
    def from_array(arr: Union[List, np.ndarray]) -> 'Trade':
        return Trade(
            timestamp=arr[0],
            side=arr[1],
            price=arr[2],
            size=arr[3]
        )
    
    def to_dict(self) -> Dict[str, float]:
        return {
            "timestamp": self.timestamp,
            "side": self.side,
            "price": self.price,
            "size": self.size
        }


class Trades:
    """
    A class to manage a collection of trades using a ring buffer.

    Attributes
    ----------
    length : int
        The maximum number of trades to store.

    _rb_ : RingBuffer
        The ring buffer to store trades.
    """

    def __init__(self, length: int = 1000) -> None:
        """
        Initializes the Trades object with a given buffer length.

        Parameters
        ----------
        length : int, optional
            The maximum number of trades to store (default is 1000).
        """
        self.length = length
        self._rb_ = RingBuffer(self.length, dtype=(np.float64, 4))

    def reset(self) -> None:
        """
        Resets the ring buffer, removing all stored trades.
        """
        self._rb_ = RingBuffer(self.length, dtype=(np.float64, 4))

    def recordable(self) -> List[Dict]:
        """
        Unwraps the internal structures into widely-used Python structures
        for easy recordability (databases, logging, debugging etc). 

        Returns
        -------
        List[Dict]
            A list of OHLCV candles.
        """
        return [
            Trade.from_array(trade).to_dict()
            for trade in self._rb_
        ]
    
    def add_single(self, trade: Trade) -> None:
        """
        Adds a single trade to the ring buffer.

        Parameters
        ----------
        trade : Trade
            The trade to add to the ring buffer.
        """
        self._rb_.append(
            np.array(
                [trade.timestamp, trade.side, trade.price, trade.size], dtype=np.float64
            )
        )
