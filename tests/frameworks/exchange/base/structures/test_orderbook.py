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
from frameworks.exchange.base.structures.orderbook import Orderbook  

class TestOrderbook(unittest.TestCase):
    def setUp(self):
        self.size = 5
        self.orderbook = Orderbook(self.size)
    
    def test_initial_state(self):
        self.assertEqual(self.orderbook.size, self.size)
        self.assertTrue((self.orderbook.asks == 0).all())
        self.assertTrue((self.orderbook.bids == 0).all())
        self.assertTrue((self.orderbook.bba == 0).all())

    def test_refresh(self):
        asks = np.array([[1.0, 10.0], [1.1, 15.0], [1.2, 20.0]])
        bids = np.array([[0.9, 5.0], [0.8, 25.0], [0.7, 30.0]])
        self.orderbook.refresh(asks, bids)
        self.assertEqual(self.orderbook.asks[0, 0], 1.0)
        self.assertEqual(self.orderbook.bids[0, 0], 0.9)

    def test_sort_bids(self):
        bids = np.array([[0.8, 25.0], [0.9, 5.0], [0.7, 30.0]])
        self.orderbook.update_bids(bids)
        self.orderbook.sort_bids()
        self.assertEqual(self.orderbook.bids[0, 0], 0.9)

    def test_sort_asks(self):
        asks = np.array([[1.1, 15.0], [1.0, 10.0], [1.2, 20.0]])
        self.orderbook.update_asks(asks)
        self.orderbook.sort_asks()
        self.assertEqual(self.orderbook.asks[0, 0], 1.0)

    def test_update_bids(self):
        bids = np.array([[0.9, 5.0], [0.8, 25.0]])
        self.orderbook.update_bids(bids)
        self.assertEqual(self.orderbook.bids[0, 0], 0.9)
        new_bids = np.array([[0.9, 0.0], [0.85, 10.0]])
        self.orderbook.update_bids(new_bids)
        self.assertEqual(self.orderbook.bids[0, 0], 0.85)

    def test_update_asks(self):
        asks = np.array([[1.1, 15.0], [1.0, 10.0]])
        self.orderbook.update_asks(asks)
        self.assertEqual(self.orderbook.asks[0, 0], 1.0)
        new_asks = np.array([[1.1, 0.0], [1.15, 10.0]])
        self.orderbook.update_asks(new_asks)
        self.assertEqual(self.orderbook.asks[0, 0], 1.0)
        self.assertEqual(self.orderbook.asks[1, 0], 1.15)

    def test_get_mid(self):
        asks = np.array([[1.1, 15.0]])
        bids = np.array([[0.9, 5.0]])
        self.orderbook.refresh(asks, bids)
        self.assertAlmostEqual(self.orderbook.get_mid(), 1.0)

    def test_get_wmid(self):
        asks = np.array([[1.1, 15.0]])
        bids = np.array([[0.9, 5.0]])
        self.orderbook.refresh(asks, bids)
        self.assertAlmostEqual(self.orderbook.get_wmid(), 1.05)

    def test_get_vamp(self):
        asks = np.array([[1.1, 15.0], [1.2, 10.0]])
        bids = np.array([[0.9, 5.0], [0.8, 10.0]])
        self.orderbook.refresh(asks, bids)
        self.assertAlmostEqual(self.orderbook.get_vamp(10.0), 1.0)

    def test_get_spread(self):
        asks = np.array([[1.1, 15.0]])
        bids = np.array([[0.9, 5.0]])
        self.orderbook.refresh(asks, bids)
        self.assertAlmostEqual(self.orderbook.get_spread(), 0.2)

    def test_get_slippage(self):
        bids = np.array([[0.9, 5.0], [0.8, 25.0], [0.7, 30.0]])
        self.orderbook.refresh(np.zeros((0, 2)), bids)
        self.assertAlmostEqual(self.orderbook.get_slippage(self.orderbook.bids, 10.0), 0.1)

if __name__ == '__main__':
    unittest.main()
