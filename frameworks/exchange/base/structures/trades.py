import numpy as np
from dataclasses import dataclass
from typing import Dict, List, Union, Any
from numpy_ringbuffer import RingBuffer


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

    def add_many(self, trades: List[Trade]) -> None:
        """
        Adds multiple trades to the ring buffer.

        Parameters
        ----------
        trades : List[Trade]
            A list of trades to add to the ring buffer.
        """
        for trade in trades:
            self.add_single(trade)

    def unwrap(self) -> np.ndarray:
        """
        Unwraps the ring buffer into a NumPy array.

        Returns
        -------
        np.ndarray
            A NumPy array representation of the ring buffer.
        """
        return self._rb_._unwrap()

    def __eq__(self, other: Union['Trades', Any]) -> bool:
        if isinstance(other, Trades):
            return np.array_equal(self.unwrap(), other.unwrap())
        return False
    
    def __getitem__(self, idx: int) -> np.ndarray:
        return self.unwrap()[idx]

    def __len__(self) -> int:
        return len(self._rb_)
    
    def __repr__(self) -> str:
        return f"Trades(length={self.length}, trades={self.unwrap()})"
