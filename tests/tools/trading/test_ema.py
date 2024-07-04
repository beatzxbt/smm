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

from frameworks.tools.trading.ringbuffer import RingBufferF64
from frameworks.tools.trading.ema import EMA

class TestEMA(unittest.TestCase):
    def setUp(self):
        self.window = 5
        self.alpha = 0.5
        self.data = np.array([1.0, 2.0, 3.0, 4.0, 5.0], dtype=np.float64)
        self.ema = EMA(self.window, self.alpha, fast=False)

    def test_initialization(self):
        self.assertEqual(self.ema.window, self.window)
        self.assertEqual(self.ema.alpha, self.alpha)
        self.assertFalse(self.ema.fast)
        self.assertEqual(self.ema.value, 0.0)
        self.assertIsInstance(self.ema.rb, RingBufferF64)
        self.assertEqual(len(self.ema.rb), 0)

    def test_recursive_ema(self):
        initial_value = 1.0
        update_value = 2.0
        self.ema.value = initial_value
        result = self.ema._recursive_ema_(update_value)
        expected = self.alpha * update_value + (1.0 - self.alpha) * initial_value
        self.assertAlmostEqual(result, expected)

    def test_initialize(self):
        self.ema.initialize(self.data)
        self.assertAlmostEqual(self.ema.value, 4.0625)
        self.assertEqual(len(self.ema.rb), self.window)

    def test_update(self):
        self.ema.initialize(self.data)
        new_val = 6.0
        old_value = self.ema.value
        self.ema.update(new_val)
        expected = self.alpha * new_val + (1.0 - self.alpha) * old_value
        self.assertAlmostEqual(self.ema.value, expected)
        self.assertEqual(len(self.ema.rb), self.window)
        self.assertAlmostEqual(self.ema.rb[-1], expected)

    def test_fast_mode(self):
        fast_ema = EMA(self.window, self.alpha, fast=True)
        fast_ema.initialize(self.data)
        self.assertEqual(len(fast_ema.rb), 0)
        new_val = 6.0
        fast_ema.update(new_val)
        self.assertEqual(len(fast_ema.rb), 0)

if __name__ == '__main__':
    unittest.main()