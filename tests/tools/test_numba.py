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
from frameworks.tools.numba import nblinspace, nbgeomspace, nbclip, nbsqrt, nbdiff_1d, nbisin

class TestNumbaFunctions(unittest.TestCase):
    def test_nblinspace(self):
        result = nblinspace(0, 10, 5)
        expected = np.linspace(0, 10, 5)
        np.testing.assert_array_almost_equal(result, expected, decimal=7)

    def test_nbgeomspace(self):
        result = nbgeomspace(1, 1000, 4)
        expected = np.geomspace(1, 1000, 4)
        np.testing.assert_array_almost_equal(result, expected, decimal=7)

    def test_nbclip(self):
        result = nbclip(5, 0, 10)
        self.assertEqual(result, 5)
        result = nbclip(-1, 0, 10)
        self.assertEqual(result, 0)
        result = nbclip(15, 0, 10)
        self.assertEqual(result, 10)

    def test_nbsqrt(self):
        result = nbsqrt(4)
        self.assertAlmostEqual(result, 2.0, places=7)
        result = nbsqrt(0)
        self.assertAlmostEqual(result, 0.0, places=7)
        result = nbsqrt(-4)
        self.assertAlmostEqual(result, -2.0, places=7)

    def test_nbdiff_1d(self):
        a = np.array([1, 2, 4, 7, 0])
        result = nbdiff_1d(a)
        expected = np.diff(a)
        np.testing.assert_array_almost_equal(result, expected, decimal=7)
        
        result = nbdiff_1d(a, 2)
        expected = np.diff(a, 2)
        np.testing.assert_array_almost_equal(result, expected, decimal=7)

    def test_nbisin(self):
        a = np.array([0, 1, 2, 3, 4])
        b = np.array([1, 3, 5])
        result = nbisin(a, b)
        expected = np.isin(a, b)
        np.testing.assert_array_equal(result, expected)

if __name__ == '__main__':
    unittest.main()
