import sys
import os

# Get the project root directory
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..', '..', '..'))

# Add the project root directory to the Python path
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# -------------------------------------------- #

import unittest
import numpy as np
from numpy_ringbuffer import RingBuffer

from frameworks.exchange.base.structures.ohlcv import OHLCV, Candles

class TestCandles(unittest.TestCase):
    def setUp(self):
        self.candles = Candles(length=1000)
        self.candle = OHLCV(
            timestamp=1622470400.0,
            open=35000.0,
            high=35500.0,
            low=34500.0,
            close=35200.0,
            volume=100.0
        )

    def test_candles_initialization(self):
        self.assertEqual(self.candles.length, 1000)
        self.assertIsInstance(self.candles._rb_, RingBuffer)
        self.assertEqual(self.candles._rb_.maxlen, 1000)

    def test_add_single(self):
        self.candles.add_single(self.candle)
        self.assertEqual(len(self.candles), 1)
        np.testing.assert_array_equal(
            self.candles[0],
            np.array([1622470400.0, 35000.0, 35500.0, 34500.0, 35200.0, 100.0])
        )

    def test_add_many(self):
        candles_list = [self.candle, self.candle]
        self.candles.add_many(candles_list)
        self.assertEqual(len(self.candles), 2)
        np.testing.assert_array_equal(
            self.candles[0],
            np.array([1622470400.0, 35000.0, 35500.0, 34500.0, 35200.0, 100.0])
        )
        np.testing.assert_array_equal(
            self.candles[1],
            np.array([1622470400.0, 35000.0, 35500.0, 34500.0, 35200.0, 100.0])
        )

    def test_reset(self):
        self.candles.add_single(self.candle)
        self.candles.reset()
        self.assertEqual(len(self.candles), 0)

    def test_unwrap(self):
        self.candles.add_single(self.candle)
        np.testing.assert_array_equal(
            self.candles.unwrap(),
            np.array([[1622470400.0, 35000.0, 35500.0, 34500.0, 35200.0, 100.0]])
        )

    def test_repr(self):
        self.candles.add_single(self.candle)
        self.assertEqual(
            repr(self.candles),
            "Candles(length=1000, candles=[[1.6224704e+09 3.5000000e+04 3.5500000e+04 3.4500000e+04 3.5200000e+04 1.0000000e+02]])"
        )

    def test_equality(self):
        candles2 = Candles(length=1000)
        self.candles.add_single(self.candle)
        candles2.add_single(self.candle)
        self.assertEqual(self.candles, candles2)

    def test_getitem(self):
        self.candles.add_single(self.candle)
        np.testing.assert_array_equal(
            self.candles[0],
            np.array([1622470400.0, 35000.0, 35500.0, 34500.0, 35200.0, 100.0])
        )

    def test_recordable(self):
        self.candles.add_single(self.candle)
        recordable_output = self.candles.recordable()
        expected_output = [{
            "timestamp": 1622470400.0,
            "open": 35000.0,
            "high": 35500.0,
            "low": 34500.0,
            "close": 35200.0,
            "volume": 100.0
        }]
        self.assertEqual(recordable_output, expected_output)

if __name__ == "__main__":
    unittest.main()