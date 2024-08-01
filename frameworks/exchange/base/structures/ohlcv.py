import numpy as np
from dataclasses import dataclass
from typing import Dict, List, Any, Union
from numpy_ringbuffer import RingBuffer


@dataclass
class OHLCV:
    timestamp: float
    open: float
    high: float
    low: float
    close: float
    volume: float

    @staticmethod
    def from_array(arr: Union[List, np.ndarray]) -> 'OHLCV':
        return OHLCV(
            timestamp=arr[0],
            open=arr[1],
            high=arr[2],
            low=arr[3],
            close=arr[4],
            volume=arr[5]
        )
    
    def to_dict(self) -> Dict[str, float]:
        return {
            "timestamp": self.timestamp,
            "open": self.open,
            "high": self.high,
            "low": self.low,
            "close": self.close,
            "volume": self.volume
        }

class Candles:
    """
    A class to manage a collection of OHLCV candles using a ring buffer.

    Attributes
    ----------
    length : int
        The maximum number of candles to store.

    _rb_ : RingBuffer
        The ring buffer to store candles.
    """

    def __init__(self, length: int = 1000) -> None:
        """
        Initializes the Candles object with a given buffer length.

        Parameters
        ----------
        length : int, optional
            The maximum number of candles to store (default is 1000).
        """
        self.length = length
        self._rb_ = RingBuffer(self.length, dtype=(np.float64, 6))
        self._latest_timestamp_ = 0

    def reset(self) -> None:
        """
        Resets the ring buffer, removing all stored candles.
        """
        self._rb_ = RingBuffer(self.length, dtype=(np.float64, 6))
        self._latest_timestamp_ = 0

    def add_single(self, candle: OHLCV) -> None:
        """
        Adds a single candle to the ring buffer.

        Parameters
        ----------
        candle : OHLCV
            The candle to add to the ring buffer.
        """
        if candle.timestamp > self._latest_timestamp_:
            self._latest_timestamp_ = candle.timestamp
        else:
            self._rb_.pop()

        self._rb_.append(
            np.array(
                [
                    candle.timestamp,
                    candle.open,
                    candle.high,
                    candle.low,
                    candle.close,
                    candle.volume,
                ],
                dtype=np.float64,
            )
        )

    def add_many(self, candles: List[OHLCV]) -> None:
        """
        Adds multiple candles to the ring buffer.

        Parameters
        ----------
        candles : List[OHLCV]
            A list of candles to add to the ring buffer.
        """
        for candle in candles:
            self.add_single(candle)

    def unwrap(self) -> np.ndarray:
        """
        Unwraps the ring buffer into a NumPy array.

        Returns
        -------
        np.ndarray
            A NumPy array representation of the ring buffer.
        """
        return self._rb_._unwrap()

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
            OHLCV.from_array(ohlcv).to_dict()
            for ohlcv in self._rb_
        ]

    def __eq__(self, other: Union['Candles', Any]) -> bool:
        if isinstance(other, Candles):
            return np.array_equal(self.unwrap(), other.unwrap())
        return False

    def __len__(self) -> int:
        return self._rb_.__len__()
    
    def __getitem__(self, idx: int) -> np.ndarray:
        return self.unwrap()[idx]
    
    def __repr__(self) -> str:
        return f"Candles(length={self.length}, candles={self.unwrap()})"
