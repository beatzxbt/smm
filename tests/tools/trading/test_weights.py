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
from frameworks.tools.trading.weights import generate_geometric_weights

class TestGenerateGeometricWeights(unittest.TestCase):
    def test_generate_default_weights(self):
        num = 5
        weights = generate_geometric_weights(num)
        self.assertEqual(len(weights), num)
        self.assertAlmostEqual(weights.sum(), 1.0, places=7)
        self.assertTrue(np.all(weights >= 0))

    def test_generate_weights_with_custom_r(self):
        num = 5
        r = 0.5
        weights = generate_geometric_weights(num, r)
        self.assertEqual(len(weights), num)
        self.assertAlmostEqual(weights.sum(), 1.0, places=7)
        self.assertTrue(np.all(weights >= 0))

    def test_generate_weights_in_ascending_order(self):
        num = 5
        weights = generate_geometric_weights(num, reverse=False)
        self.assertEqual(len(weights), num)
        self.assertAlmostEqual(weights.sum(), 1.0, places=7)
        self.assertTrue(np.all(weights >= 0))
        self.assertTrue(np.all(weights[:-1] <= weights[1:]))

    def test_generate_weights_in_descending_order(self):
        num = 5
        weights = generate_geometric_weights(num, reverse=True)
        self.assertEqual(len(weights), num)
        self.assertAlmostEqual(weights.sum(), 1.0, places=7)
        self.assertTrue(np.all(weights >= 0))
        self.assertTrue(np.all(weights[:-1] >= weights[1:]))

    def test_generate_single_weight(self):
        num = 1
        weights = generate_geometric_weights(num)
        self.assertEqual(len(weights), num)
        self.assertAlmostEqual(weights.sum(), 1.0, places=7)
        self.assertTrue(np.all(weights >= 0))

    def test_invalid_r_value(self):
        num = 5
        with self.assertRaises(ValueError):
            generate_geometric_weights(num, r=-0.5)

if __name__ == '__main__':
    unittest.main()
