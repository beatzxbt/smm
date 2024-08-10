import sys
import os

# Get the project root directory
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..', '..', '..'))

# Add the project root directory to the Python path
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# -------------------------------------------- #

import unittest
from frameworks.exchange.base.constants import Side
from frameworks.exchange.base.ws_handlers.trades import Trade, Trades
from frameworks.exchange.binance.ws_handlers.trades import BinanceTradesHandler

class TestBinanceTradesHandler(unittest.TestCase):
    def setUp(self):
        self.trades = Trades()
        self.handler = BinanceTradesHandler(trades=self.trades)
        
    def test_refresh(self):
        payload = [
            {
                "id": 28457,
                "price": "4.00000100",
                "qty": "12.00000000",
                "quoteQty": "48.00",
                "time": 1499865549590,
                "isBuyerMaker": True,
            }
        ]
        
        self.handler.refresh(payload)
        
        self.assertEqual(len(self.trades._rb_), 1)
        trade = self.trades._rb_[0]
        self.assertAlmostEqual(trade[0], 1499865549590)
        self.assertEqual(trade[1], Side.SELL)
        self.assertAlmostEqual(trade[2], 4.00000100)
        self.assertAlmostEqual(trade[3], 12.00000000)
        
    def test_process(self):
        payload = {
            "e": "trade",
            "E": 123456789,
            "s": "BTCUSDT",
            "p": "0.001",
            "q": "100",
            "T": 123456785,
            "m": True,
        }
        
        self.handler.process(payload)
        
        self.assertEqual(len(self.trades), 1)
        trade = self.trades[0]
        self.assertAlmostEqual(trade[0], 123456785)
        self.assertEqual(trade[1], Side.SELL)
        self.assertAlmostEqual(trade[2], 0.001)
        self.assertAlmostEqual(trade[3], 100)

    def test_process_buy_side(self):
        payload = {
            "e": "trade",
            "E": 123456789,
            "s": "BTCUSDT",
            "p": "0.002",
            "q": "50",
            "T": 123456790,
            "m": False,
        }
        
        self.handler.process(payload)
        
        self.assertEqual(len(self.trades), 1)
        trade = self.trades[0]
        self.assertAlmostEqual(trade[0], 123456790)
        self.assertEqual(trade[1], Side.BUY)
        self.assertAlmostEqual(trade[2], 0.002)
        self.assertAlmostEqual(trade[3], 50)

    def test_refresh_multiple_trades(self):
        payload = [
            {
                "id": 28457,
                "price": "4.00000100",
                "qty": "12.00000000",
                "quoteQty": "48.00",
                "time": 1499865549590,
                "isBuyerMaker": True,
            },
            {
                "id": 28458,
                "price": "4.00000200",
                "qty": "15.00000000",
                "quoteQty": "60.00",
                "time": 1499865559590,
                "isBuyerMaker": False,
            }
        ]
        
        self.handler.refresh(payload)
        
        self.assertEqual(len(self.trades), 2)
        
        trade1 = self.trades[0]
        self.assertAlmostEqual(trade1[0], 1499865549590)
        self.assertEqual(trade1[1], Side.SELL)
        self.assertAlmostEqual(trade1[2], 4.00000100)
        self.assertAlmostEqual(trade1[3], 12.00000000)
        
        trade2 = self.trades[1]
        self.assertAlmostEqual(trade2[0], 1499865559590)
        self.assertEqual(trade2[1], Side.BUY)
        self.assertAlmostEqual(trade2[2], 4.00000200)
        self.assertAlmostEqual(trade2[3], 15.00000000)

if __name__ == '__main__':
    unittest.main()
