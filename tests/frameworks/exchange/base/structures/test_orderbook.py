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
        asks = np.array([[1.0, 10.0], [1.1, 15.0], [1.2, 20.0]], dtype=np.float64)
        bids = np.array([[0.9, 5.0], [0.8, 25.0], [0.7, 30.0]], dtype=np.float64)
        self.orderbook.refresh(asks, bids)
        self.assertEqual(self.orderbook.asks[0, 0], 1.0)
        self.assertEqual(self.orderbook.bids[0, 0], 0.9)

        # Test with fewer levels
        asks = np.array([[1.0, 10.0]], dtype=np.float64)
        bids = np.array([[0.9, 5.0]], dtype=np.float64)
        self.orderbook.refresh(asks, bids)
        self.assertEqual(self.orderbook.asks[0, 0], 1.0)
        self.assertEqual(self.orderbook.bids[0, 0], 0.9)

        # Test with no levels
        asks = np.array([], dtype=np.float64)
        bids = np.array([], dtype=np.float64)
        self.orderbook.refresh(asks, bids)
        self.assertTrue((self.orderbook.asks == 0).all())
        self.assertTrue((self.orderbook.bids == 0).all())

    def test_sort_bids(self):
        bids = np.array([[0.8, 25.0], [0.9, 5.0], [0.7, 30.0]], dtype=np.float64)
        self.orderbook.update_bids(bids)
        self.orderbook.sort_bids()
        self.assertEqual(self.orderbook.bids[0, 0], 0.9)

        # Test with unordered bids
        bids = np.array([[0.7, 30.0], [0.8, 25.0], [0.9, 5.0]], dtype=np.float64)
        self.orderbook.update_bids(bids)
        self.orderbook.sort_bids()
        self.assertEqual(self.orderbook.bids[0, 0], 0.9)

        # Test with all equal bids
        bids = np.array([[0.8, 25.0], [0.8, 25.0], [0.8, 25.0]], dtype=np.float64)
        self.orderbook.update_bids(bids)
        self.orderbook.sort_bids()
        self.assertEqual(self.orderbook.bids[0, 0], 0.8)

    def test_sort_asks(self):
        asks = np.array([[1.1, 15.0], [1.0, 10.0], [1.2, 20.0]], dtype=np.float64)
        self.orderbook.update_asks(asks)
        self.orderbook.sort_asks()
        self.assertEqual(self.orderbook.asks[0, 0], 1.0)

        # Test with unordered asks
        asks = np.array([[1.2, 20.0], [1.0, 10.0], [1.1, 15.0]], dtype=np.float64)
        self.orderbook.update_asks(asks)
        self.orderbook.sort_asks()
        self.assertEqual(self.orderbook.asks[0, 0], 1.0)

        # Test with all equal asks
        asks = np.array([[1.1, 15.0], [1.1, 15.0], [1.1, 15.0]], dtype=np.float64)
        self.orderbook.update_asks(asks)
        self.orderbook.sort_asks()
        self.assertEqual(self.orderbook.asks[0, 0], 1.1)

    def test_update_bids(self):
        bids = np.array([[0.9, 5.0], [0.8, 25.0]], dtype=np.float64)
        self.orderbook.update_bids(bids)
        self.assertEqual(self.orderbook.bids[0, 0], 0.9)

        # Test updating existing bid with size zero
        new_bids = np.array([[0.9, 0.0], [0.85, 10.0]], dtype=np.float64)
        self.orderbook.update_bids(new_bids)
        self.assertEqual(self.orderbook.bids[0, 0], 0.85)

        # Test adding new bid
        more_bids = np.array([[0.95, 15.0]], dtype=np.float64)
        self.orderbook.update_bids(more_bids)
        self.assertEqual(self.orderbook.bids[0, 0], 0.95)

    def test_update_asks(self):
        asks = np.array([[1.1, 15.0], [1.0, 10.0]], dtype=np.float64)
        self.orderbook.update_asks(asks)
        self.assertEqual(self.orderbook.asks[0, 0], 1.0)

        # Test updating existing ask with size zero
        new_asks = np.array([[1.1, 0.0], [1.15, 10.0]], dtype=np.float64)
        self.orderbook.update_asks(new_asks)
        self.assertEqual(self.orderbook.asks[0, 0], 1.0)
        self.assertEqual(self.orderbook.asks[1, 0], 1.15)

        # Test adding new ask
        more_asks = np.array([[1.05, 20.0]], dtype=np.float64)
        self.orderbook.update_asks(more_asks)
        self.assertEqual(self.orderbook.asks[0, 0], 1.0)
        self.assertEqual(self.orderbook.asks[1, 0], 1.05)

    def test_get_mid(self):
        asks = np.array([[1.1, 15.0]], dtype=np.float64)
        bids = np.array([[0.9, 5.0]], dtype=np.float64)
        self.orderbook.refresh(asks, bids)
        self.assertAlmostEqual(self.orderbook.get_mid(), 1.0)

        # Test with no bids
        asks = np.array([[1.1, 15.0]], dtype=np.float64)
        bids = np.array([])
        self.orderbook.refresh(asks, bids)
        self.assertEqual(self.orderbook.get_mid(), 1.1)

        # Test with no asks
        asks = np.array([])
        bids = np.array([[0.9, 5.0]], dtype=np.float64)
        self.orderbook.refresh(asks, bids)
        self.assertEqual(self.orderbook.get_mid(), 0.9)

    def test_get_wmid(self):
        asks = np.array([[1.1, 15.0]], dtype=np.float64)
        bids = np.array([[0.9, 5.0]], dtype=np.float64)
        self.orderbook.refresh(asks, bids)
        self.assertAlmostEqual(self.orderbook.get_wmid(), 1.05)

        # Test with no bids
        asks = np.array([[1.1, 15.0]], dtype=np.float64)
        bids = np.array([])
        self.orderbook.refresh(asks, bids)
        self.assertEqual(self.orderbook.get_wmid(), 1.1)

        # Test with no asks
        asks = np.array([])
        bids = np.array([[0.9, 5.0]], dtype=np.float64)
        self.orderbook.refresh(asks, bids)
        self.assertEqual(self.orderbook.get_wmid(), 0.9)

    def test_get_vamp(self):
        asks = np.array([[1.1, 15.0], [1.2, 10.0]], dtype=np.float64)
        bids = np.array([[0.9, 5.0], [0.8, 10.0]], dtype=np.float64)
        self.orderbook.refresh(asks, bids)
        self.assertAlmostEqual(self.orderbook.get_vamp(10.0), 1.0)

        # Test with small depth
        self.assertAlmostEqual(self.orderbook.get_vamp(5.0), 1.0)

        # Test with larger depth than available volume
        self.assertAlmostEqual(self.orderbook.get_vamp(100.0), 1.0)

    def test_get_spread(self):
        asks = np.array([[1.1, 15.0]], dtype=np.float64)
        bids = np.array([[0.9, 5.0]], dtype=np.float64)
        self.orderbook.refresh(asks, bids)
        self.assertAlmostEqual(self.orderbook.get_spread(), 0.2)

        # Test with no bids
        asks = np.array([[1.1, 15.0]], dtype=np.float64)
        bids = np.array([])
        self.orderbook.refresh(asks, bids)
        self.assertEqual(self.orderbook.get_spread(), 1.1)

        # Test with no asks
        asks = np.array([])
        bids = np.array([[0.9, 5.0]], dtype=np.float64)
        self.orderbook.refresh(asks, bids)
        self.assertEqual(self.orderbook.get_spread(), 0.9)

    def test_get_slippage(self):
        bids = np.array([[0.9, 5.0], [0.8, 25.0], [0.7, 30.0]], dtype=np.float64)
        self.orderbook.refresh(np.zeros((0, 2)), bids)
        self.assertAlmostEqual(self.orderbook.get_slippage(self.orderbook.bids, 10.0), 0.1)

        # Test with small order size
        self.assertAlmostEqual(self.orderbook.get_slippage(self.orderbook.bids, 2.0), 0.05)

        # Test with large order size
        self.assertAlmostEqual(self.orderbook.get_slippage(self.orderbook.bids, 60.0), 0.15)

if __name__ == '__main__':
    unittest.main()
