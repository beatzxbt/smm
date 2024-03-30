import numpy as np
from numpy.typing import NDArray
from numpy_ringbuffer import RingBuffer

class TickCandles:
    """
    A class to accumulate trade ticks into candlestick (OHLCV) data using fixed-sized buckets.

    Parameters
    ----------
    bucket_size : int
        The number of ticks to accumulate before creating a new candlestick entry.

    Attributes
    ----------
    bucket_size : int
        Stores the size of the bucket, i.e., how many ticks constitute a single candle.

    _latest_timestamp_ : float
        The timestamp of the last processed trade.

    _open_timestamp_ : float
        The timestamp at which the current bucket started.

    _open_ : float
        The opening price for the current bucket.

    _high_ : float
        The highest price encountered in the current bucket.

    _low_ : float
        The lowest price encountered in the current bucket.

    _close_ : float
        The closing price for the current bucket.

    _volume_ : float
        The accumulated volume of trades in the current bucket.

    _ticks_in_bucket_ : int
        The number of ticks processed in the current bucket.

    _arr_ : RingBuffer
        A ring buffer to store the accumulated candlestick data in TOHLCV format.

    Methods
    -------
    array(self) -> NDArray
        Returns the internal ring buffer as an NDArray of candlestick data.

    _reset_bucket_vars_(self)
        Resets the variables used for accumulating a bucket's data.

    _process_single_tick_(self, trade: NDArray)
        Processes a single tick and updates the current bucket or creates a new one.

    initialize(self, trades: RingBuffer)
        Initializes the candlestick data with a series of trades.

    update(self, trades: RingBuffer)
        Updates the candlestick data with new trades.
    """
    def __init__(self, bucket_size: int):
        self.bucket_size = bucket_size
        
        self._latest_timestamp_ = 0
        self._open_timestamp_ = 0
        self._open_ = 0
        self._high_ = 0
        self._low_ = 0
        self._close_ = 0
        self._volume_ = 0
        self._ticks_in_bucket_ = 0

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
        self._volume_ = 0
        self._ticks_in_bucket_ = 0

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

        if self._ticks_in_bucket_ >= self.bucket_size:
            candle = np.array([
                self._open_timestamp_,
                self._open_,
                self._high_,
                self._low_,
                self._close_,
                self._volume_,
            ])
            self._arr_.append(candle)
            self._reset_bucket_vars_()

        else:
            if self._ticks_in_bucket_ == 0:
                self._open_timestamp_ = time
                self._open_ = price
                self._high_ = price
                self._low_ = price
                self._close_ = price
                self._volume_ = size

            else:
                self._high_ = max(price, self._high_)
                self._low_ = min(price, self._low_)

                self._close_ = price 
                self._volume_ += size

            self._ticks_in_bucket_ += 1
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