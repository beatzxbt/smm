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
from frameworks.tools.trading.rounding import round_ceil, round_floor, round_discrete

class TestRoundingFunctions(unittest.TestCase):

    def test_round_ceil(self):
        self.assertAlmostEqual(round_ceil(5.1, 0.5), 5.5)
        np.testing.assert_array_almost_equal(round_ceil(np.array([2.3, 4.6, 6.1]), 2), np.array([4, 6, 8]))

    def test_round_floor(self):
        self.assertAlmostEqual(round_floor(5.8, 0.5), 5.5)
        np.testing.assert_array_almost_equal(round_floor(np.array([2.7, 4.2, 6.9]), 2), np.array([2, 4, 6]))

    def test_round_discrete(self):
        self.assertAlmostEqual(round_discrete(5.3, 0.5), 5.5)
        np.testing.assert_array_almost_equal(round_discrete(np.array([2.4, 4.5, 7.7]), 2), np.array([2.0, 4.0, 8.0]))

if __name__ == '__main__':
    unittest.main()