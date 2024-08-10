import sys
import os

# Get the project root directory
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..', '..', '..'))

# Add the project root directory to the Python path
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# -------------------------------------------- #

import unittest
from frameworks.exchange.base.ws_handlers.ticker import Ticker
from frameworks.exchange.binance.ws_handlers.markprice import BinanceTickerHandler

class TestBinanceTickerHandler(unittest.TestCase):
    def setUp(self):
        self.ticker = Ticker()
        self.handler = BinanceTickerHandler(ticker=self.ticker)
        
    def test_refresh(self):
        payload = {
            "symbol": "BTCUSDT",
            "markPrice": "11793.63104562",
            "indexPrice": "11781.80495970",
            "estimatedSettlePrice": "11781.16138815",
            "lastFundingRate": "0.00038246",
            "nextFundingTime": 1597392000000,
            "interestRate": "0.00010000",
            "time": 1597370495002
        }
        
        self.handler.refresh(payload)
        
        self.assertAlmostEqual(self.ticker.markPx, 11793.63104562)
        self.assertAlmostEqual(self.ticker.indexPx, 11781.80495970)
        self.assertAlmostEqual(self.ticker.fundingRate, 0.00038246)
        self.assertEqual(self.ticker.fundingTs, 1597392000000)
        
    def test_process(self):
        payload = {
            "e": "markPriceUpdate",
            "E": 1562305380000,
            "s": "BTCUSDT",
            "p": "11794.15000000",
            "i": "11784.62659091",
            "P": "11784.25641265",
            "r": "0.00038167",
            "T": 1562306400000
        }
        
        self.handler.process(payload)
        
        self.assertAlmostEqual(self.ticker.markPx, 11794.15000000)
        self.assertAlmostEqual(self.ticker.indexPx, 11784.62659091)
        self.assertAlmostEqual(self.ticker.fundingRate, 0.00038167)
        self.assertEqual(self.ticker.fundingTs, 1562306400000)

if __name__ == '__main__':
    unittest.main()
