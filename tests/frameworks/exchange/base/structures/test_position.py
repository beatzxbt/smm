import sys
import os

# Get the project root directory
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))

# Add the project root directory to the Python path
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# -------------------------------------------- #

import unittest
from frameworks.exchange.base.constants import Side
from frameworks.exchange.base.structures.position import Position


class TestPosition(unittest.TestCase):
    def setUp(self):
        self.position = Position(
            symbol="BTCUSD",
            side=Side.BUY,
            price=50000.0,
            size=1.0,
            uPnl=1000.0,
        )

    def test_position_initialization(self):
        self.assertEqual(self.position.symbol, "BTCUSD")
        self.assertEqual(self.position.side, Side.BUY)
        self.assertEqual(self.position.price, 50000.0)
        self.assertEqual(self.position.size, 1.0)
        self.assertEqual(self.position.uPnl, 1000.0)

    def test_position_repr(self):
        self.assertEqual(
            repr(self.position),
            "Position(symbol=BTCUSD, side=0, price=50000.0, size=1.0, uPnl=1000.0)",
        )

    def test_position_str(self):
        self.assertEqual(
            str(self.position),
            "Position: symbol=BTCUSD, side=0, price=50000.0, size=1.0, uPnl=1000.0",
        )

    def test_position_to_dict(self):
        position_dict = self.position.to_dict()
        expected_dict = {
            "symbol": "BTCUSD",
            "side": Side.BUY,
            "price": 50000.0,
            "size": 1.0,
            "uPnl": 1000.0,
        }
        self.assertEqual(position_dict, expected_dict)

    def test_position_update(self):
        self.position.update(symbol="ETHUSD", price=2500.0, size=2.0, uPnl=200.0)
        self.assertEqual(self.position.symbol, "ETHUSD")
        self.assertEqual(self.position.price, 2500.0)
        self.assertEqual(self.position.size, 2.0)
        self.assertEqual(self.position.uPnl, 200.0)

    def test_position_clear(self):
        self.position.clear()
        self.assertIsNone(self.position.symbol)
        self.assertIsNone(self.position.side)
        self.assertIsNone(self.position.price)
        self.assertIsNone(self.position.size)
        self.assertIsNone(self.position.uPnl)

    def test_position_is_empty(self):
        self.assertFalse(self.position.is_empty)
        self.position.size = 0.0
        self.assertTrue(self.position.is_empty)

    def test_position_in_profit(self):
        self.assertTrue(self.position.in_profit)
        self.position.uPnl = -1000.0
        self.assertFalse(self.position.in_profit)
        self.position.uPnl = 0.0
        self.assertFalse(self.position.in_profit)
        self.position.uPnl = 1000.0
        self.assertTrue(self.position.in_profit)

if __name__ == '__main__':
    unittest.main()
