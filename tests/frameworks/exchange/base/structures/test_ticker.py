import sys
import os

# Get the project root directory
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))

# Add the project root directory to the Python path
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# -------------------------------------------- #

import unittest
from frameworks.exchange.base.structures.ticker import Ticker

class TestTicker(unittest.TestCase):
    def setUp(self):
        self.ticker = Ticker(
            fundingTs=1622470400.0,
            fundingRate=0.0001,
            markPx=35000.0,
            indexPx=34900.0,
        )

    def test_ticker_initialization(self):
        self.assertEqual(self.ticker.fundingTs, 1622470400.0)
        self.assertEqual(self.ticker.fundingRate, 0.0001)
        self.assertEqual(self.ticker.markPx, 35000.0)
        self.assertEqual(self.ticker.indexPx, 34900.0)

    def test_ticker_repr(self):
        self.assertEqual(
            repr(self.ticker),
            "Ticker(fundingTs=1622470400.0, fundingRate=0.0001, markPx=35000.0, indexPx=34900.0)"
        )

    def test_ticker_str(self):
        self.assertEqual(
            str(self.ticker),
            "Ticker: fundingTs=1622470400.0, fundingRate=0.0001, markPx=35000.0, indexPx=34900.0"
        )

    def test_ticker_equality(self):
        ticker2 = Ticker(
            fundingTs=1622470400.0,
            fundingRate=0.0001,
            markPx=35000.0,
            indexPx=34900.0,
        )
        self.assertEqual(self.ticker, ticker2)

    def test_ticker_to_dict(self):
        ticker_dict = self.ticker.to_dict()
        expected_dict = {
            "fundingTs": 1622470400.0,
            "fundingRate": 0.0001,
            "markPx": 35000.0,
            "indexPx": 34900.0,
        }
        self.assertEqual(ticker_dict, expected_dict)

    def test_ticker_update(self):
        self.ticker.update(fundingTs=1622470500.0, fundingRate=0.0002, markPx=36000.0, indexPx=35900.0)
        self.assertEqual(self.ticker.fundingTs, 1622470500.0)
        self.assertEqual(self.ticker.fundingRate, 0.0002)
        self.assertEqual(self.ticker.markPx, 36000.0)
        self.assertEqual(self.ticker.indexPx, 35900.0)

    def test_ticker_reset(self):
        self.ticker.reset()
        self.assertIsNone(self.ticker.fundingTs)
        self.assertIsNone(self.ticker.fundingRate)
        self.assertIsNone(self.ticker.markPx)
        self.assertIsNone(self.ticker.indexPx)

    def test_fundingRateBps(self):
        self.assertEqual(self.ticker.fundingRateBps, 1.0)

if __name__ == '__main__':
    unittest.main()
