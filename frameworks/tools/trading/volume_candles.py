import numpy as np
from numpy.typing import NDArray
from numpy_ringbuffer import RingBuffer


class VolumeCandles:
    """
    Each candle represents aggregated trade information until the cumulative trade size reaches 
    or exceeds a specified `bucket_size`. This method provides insights into market behavior 
    based on trade volume, which can be crucial for volume-based trading strategies.
    
    Attributes
    ----------
    bucket_size : int
        The target cumulative trade size for each candle.

    _latest_timestamp_ : int
        Timestamp of the latest trade processed.

    _open_timestamp_ : int
        Timestamp of the first trade in the current bucket.

    _open_ : float
        Opening price of the current bucket.

    _high_ : float
        Highest price encountered in the current bucket.

    _low_ : float
        Lowest price encountered in the current bucket.

    _close_ : float
        Closing price of the current bucket.

    _size_in_bucket_ : float
        Cumulative size of trades processed in the current bucket.

    _arr_ : RingBuffer
        Ring buffer storing the OHLCV data for each completed candle.

    
    Methods
    -------
    array(self) -> NDArray
        Returns the internal ring buffer as an NDArray of candlestick data.

    _reset_bucket_vars_(self)
        Resets the variables used for accumulating a bucket's data.

    _process_single_tick_(self, trade: NDArray) -> None
        Processes a single trade tick and updates the current candle or starts a new one.

    initialize(self, trades: RingBuffer) -> None
        Initializes the order book with a series of trade ticks.

    update(self, trades: RingBuffer) -> None
        Updates the order book with new trade ticks.
    """
    def __init__(self, bucket_size: int):
        self.bucket_size = bucket_size
        
        self._latest_timestamp_ = 0
        self._open_timestamp_ = 0
        self._open_ = 0
        self._high_ = 0
        self._low_ = 0
        self._close_ = 0
        self._size_in_bucket_ = 0

        self._arr_ = RingBuffer((self.bucket_size, 6), dtype=(np.float64, 6)) # TOHLCV

    @property
    def array(self) -> NDArray:
        """
        Returns the accumulated candlestick data as a numpy array.
        
        Returns
        -------
        NDArray
            The candlestick data accumulated in the ring buffer, unwrapped as an NDArray.
        """
        return self._arr_._unwrap()
    
    def _reset_bucket_vars_(self) -> None:
        """
        Resets the variables used to accumulate the data for a single bucket.
        """
        self._open_timestamp_ = 0
        self._open_ = 0
        self._high_ = 0
        self._low_ = 0
        self._close_ = 0
        self._size_in_bucket_ = 0

    def _process_single_tick_(self, trade: NDArray) -> None:
        """
        Processes a single trade tick and updates or creates a bucket accordingly.
        
        Parameters
        ----------
        trade : NDArray
            A numpy array representing a single trade tick, expected to contain:
            [time, side, price, size].
        """
        time, _, price, size = trade

        if self._size_in_bucket_ >= self.bucket_size:
            candle = np.array([
                self._open_timestamp_,
                self._open_,
                self._high_,
                self._low_,
                self._close_,
                self._size_in_bucket_
            ])
            self._arr_.append(candle)
            self._reset_bucket_vars_()

        else:
            if self._size_in_bucket_ == 0:
                self._open_timestamp_ = time
                self._open_ = price
                self._high_ = price
                self._low_ = price
                self._close_ = price

            else:
                self._high_ = max(price, self._high_)
                self._low_ = min(price, self._low_)
                self._close_ = price 

            self._size_in_bucket_ += size
            self._latest_timestamp_ = time
        
    def initialize(self, trades: RingBuffer) -> None:
        """
        Initializes the candlestick data with a series of trades.
        
        Parameters
        ----------
        trades : RingBuffer
            A ring buffer containing the trades to initialize the candlestick data with.
        """
        self._reset_bucket_vars_()
        for trade in trades._unwrap():
            self._process_single_tick_(trade)

    def update(self, trades: RingBuffer) -> None:
        """
        Updates the candlestick data with new trades.
        
        Parameters
        ----------
        trades : RingBuffer
            A ring buffer containing new trades to update the candlestick data with.
        """
        new_trades = trades._unwrap()[trades._unwrap()[:, 0] > self._latest_timestamp_]
        if len(new_trades) > 0:
            for trade in new_trades:
                self._process_single_tick_(trade)