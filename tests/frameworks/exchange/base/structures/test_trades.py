import sys
import os

# Get the project root directory
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))

# Add the project root directory to the Python path
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# -------------------------------------------- #

import unittest
import numpy as np
from numpy_ringbuffer import RingBuffer

from frameworks.exchange.base.structures.trades import Trade, Trades
from frameworks.exchange.base.constants import Side

class TestTrades(unittest.TestCase):
    def setUp(self):
        self.trades = Trades(length=1000)
        self.trade = Trade(
            timestamp=1622470400.0,
            side=Side.BUY,
            price=35000.0,
            size=1.0
        )

    def test_trades_initialization(self):
        self.assertEqual(self.trades.length, 1000)
        self.assertIsInstance(self.trades._rb_, RingBuffer)
        self.assertEqual(self.trades._rb_.maxlen, 1000)

    def test_add_single(self):
        self.trades.add_single(self.trade)
        self.assertEqual(len(self.trades), 1)
        np.testing.assert_array_equal(
            self.trades[0],
            np.array([1622470400.0, Side.BUY, 35000.0, 1.0])
        )

    def test_add_many(self):
        trades_list = [self.trade, self.trade]
        self.trades.add_many(trades_list)
        self.assertEqual(len(self.trades), 2)
        np.testing.assert_array_equal(
            self.trades[0],
            np.array([1622470400.0, Side.BUY, 35000.0, 1.0])
        )
        np.testing.assert_array_equal(
            self.trades[1],
            np.array([1622470400.0, Side.BUY, 35000.0, 1.0])
        )

    def test_reset(self):
        self.trades.add_single(self.trade)
        self.trades.reset()
        self.assertEqual(len(self.trades), 0)

    def test_unwrap(self):
        self.trades.add_single(self.trade)
        np.testing.assert_array_equal(
            self.trades.unwrap(),
            np.array([[1622470400.0, Side.BUY, 35000.0, 1.0]])
        )

    def test_repr(self):
        self.trades.add_single(self.trade)
        self.assertEqual(
            repr(self.trades),
            "Trades(length=1000, trades=[[1.6224704e+09 0.0000000e+00 3.5000000e+04 1.0000000e+00]])"
        )

    def test_equality(self):
        trades2 = Trades(length=1000)
        self.trades.add_single(self.trade)
        trades2.add_single(self.trade)
        self.assertEqual(self.trades, trades2)

    def test_getitem(self):
        self.trades.add_single(self.trade)
        np.testing.assert_array_equal(
            self.trades[0],
            np.array([1622470400.0, Side.BUY, 35000.0, 1.0])
        )

    def test_recordable(self):
        self.trades.add_single(self.trade)
        expected_recordable = [{
            "timestamp": 1622470400.0,
            "side": Side.BUY,
            "price": 35000.0,
            "size": 1.0
        }]
        self.assertEqual(self.trades.recordable(), expected_recordable)

if __name__ == '__main__':
    unittest.main()