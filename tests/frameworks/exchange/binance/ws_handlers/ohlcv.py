import sys
import os

# Get the project root directory
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..', '..', '..'))

# Add the project root directory to the Python path
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# -------------------------------------------- #

import unittest
from frameworks.exchange.base.ws_handlers.ohlcv import OHLCV, Candles
from frameworks.exchange.binance.ws_handlers.ohlcv import BinanceOhlcvHandler

class TestBinanceOhlcvHandler(unittest.TestCase):
    def setUp(self):
        self.ohlcv = Candles(length=10)
        self.handler = BinanceOhlcvHandler(ohlcv=self.ohlcv)

    def test_refresh(self):
        payload = [
            [
                1499040000000,
                "0.01634790",
                "0.80000000",
                "0.01575800",
                "0.01577100",
                "148976.11427815",
                1499644799999,
                "2434.19055334",
                308,
                "1756.87402397",
                "28.46694368",
                "17928899.62484339"
            ]
        ]
        
        self.handler.refresh(payload)
        
        self.assertEqual(len(self.ohlcv.unwrap()), 1)
        self.assertAlmostEqual(self.ohlcv.unwrap()[0][0], 1499040000000)
        self.assertAlmostEqual(self.ohlcv.unwrap()[0][1], 0.01634790)
        self.assertAlmostEqual(self.ohlcv.unwrap()[0][2], 0.80000000)
        self.assertAlmostEqual(self.ohlcv.unwrap()[0][3], 0.01575800)
        self.assertAlmostEqual(self.ohlcv.unwrap()[0][4], 0.01577100)
        self.assertAlmostEqual(self.ohlcv.unwrap()[0][5], 148976.11427815)

    def test_process(self):
        payload = {
            "e": "kline",
            "E": 1638747660000,
            "s": "BTCUSDT",
            "k": {
                "t": 1638747660000,
                "T": 1638747719999,
                "s": "BTCUSDT",
                "i": "1m",
                "f": 100,
                "L": 200,
                "o": "0.0010",
                "c": "0.0020",
                "h": "0.0025",
                "l": "0.0015",
                "v": "1000",
                "n": 100,
                "x": False,
                "q": "1.0000",
                "V": "500",
                "Q": "0.500",
                "B": "123456"
            }
        }
        
        self.handler.process(payload)
        
        self.assertEqual(len(self.ohlcv.unwrap()), 1)
        self.assertAlmostEqual(self.ohlcv.unwrap()[0][0], 1638747660000)
        self.assertAlmostEqual(self.ohlcv.unwrap()[0][1], 0.0010)
        self.assertAlmostEqual(self.ohlcv.unwrap()[0][2], 0.0025)
        self.assertAlmostEqual(self.ohlcv.unwrap()[0][3], 0.0015)
        self.assertAlmostEqual(self.ohlcv.unwrap()[0][4], 0.0020)
        self.assertAlmostEqual(self.ohlcv.unwrap()[0][5], 1000)

if __name__ == '__main__':
    unittest.main()
