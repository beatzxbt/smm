import sys
import os

# Get the project root directory
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..', '..', '..'))

# Add the project root directory to the Python path
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# -------------------------------------------- #

import unittest
from frameworks.exchange.base.ws_handlers.orderbook import Orderbook
from frameworks.exchange.binance.ws_handlers.orderbook import BinanceOrderbookHandler

class TestBinanceOrderbookHandler(unittest.TestCase):
    def setUp(self):
        self.orderbook = Orderbook(size=5)
        self.handler = BinanceOrderbookHandler(orderbook=self.orderbook)

    def test_refresh(self):
        payload = {
            "lastUpdateId": 1027024,
            "E": 1589436922972,
            "T": 1589436922959,
            "bids": [
                ["4.00000000", "431.00000000"]
            ],
            "asks": [
                ["4.00000200", "12.00000000"]
            ]
        }
        
        self.handler.refresh(payload)
        
        self.assertEqual(len(self.orderbook.bids), 5)
        self.assertEqual(len(self.orderbook.asks), 5)
        self.assertAlmostEqual(self.orderbook.bids[0][0], 4.00000000)
        self.assertAlmostEqual(self.orderbook.bids[0][1], 431.00000000)
        self.assertAlmostEqual(self.orderbook.asks[0][0], 4.00000200)
        self.assertAlmostEqual(self.orderbook.asks[0][1], 12.00000000)

    def test_process(self):
        # Initial state to simulate a filled order book
        refresh_payload = {
            "lastUpdateId": 1027024,
            "E": 1589436922972,
            "T": 1589436922959,
            "bids": [
                ["4.00000000", "431.00000000"]
            ],
            "asks": [
                ["4.00000200", "12.00000000"]
            ]
        }
        self.handler.refresh(refresh_payload)
        
        process_payload = {
            "e": "depthUpdate",
            "E": 123456789,
            "T": 123456788,
            "s": "BTCUSDT",
            "U": 157,
            "u": 160,
            "pu": 149,
            "b": [
                ["0.0024", "10"]
            ],
            "a": [
                ["0.0026", "100"]
            ]
        }
        
        self.handler.process(process_payload)
        
        self.assertAlmostEqual(self.orderbook.bids[0][0], 0.0024)
        self.assertAlmostEqual(self.orderbook.bids[0][1], 10)
        self.assertAlmostEqual(self.orderbook.asks[0][0], 0.0026)
        self.assertAlmostEqual(self.orderbook.asks[0][1], 100)

    def test_process_only_bids(self):
        # Initial state to simulate a filled order book
        refresh_payload = {
            "lastUpdateId": 1027024,
            "E": 1589436922972,
            "T": 1589436922959,
            "bids": [
                ["4.00000000", "431.00000000"]
            ],
            "asks": [
                ["4.00000200", "12.00000000"]
            ]
        }
        self.handler.refresh(refresh_payload)
        
        process_payload = {
            "e": "depthUpdate",
            "E": 123456789,
            "T": 123456788,
            "s": "BTCUSDT",
            "U": 157,
            "u": 160,
            "pu": 149,
            "b": [
                ["0.0024", "10"]
            ],
            "a": []
        }
        
        self.handler.process(process_payload)
        
        self.assertAlmostEqual(self.orderbook.bids[0][0], 0.0024)
        self.assertAlmostEqual(self.orderbook.bids[0][1], 10)
        self.assertAlmostEqual(self.orderbook.asks[0][0], 4.00000200)
        self.assertAlmostEqual(self.orderbook.asks[0][1], 12.00000000)

    def test_process_only_asks(self):
        # Initial state to simulate a filled order book
        refresh_payload = {
            "lastUpdateId": 1027024,
            "E": 1589436922972,
            "T": 1589436922959,
            "bids": [
                ["4.00000000", "431.00000000"]
            ],
            "asks": [
                ["4.00000200", "12.00000000"]
            ]
        }
        self.handler.refresh(refresh_payload)
        
        process_payload = {
            "e": "depthUpdate",
            "E": 123456789,
            "T": 123456788,
            "s": "BTCUSDT",
            "U": 157,
            "u": 160,
            "pu": 149,
            "b": [],
            "a": [
                ["0.0026", "100"]
            ]
        }
        
        self.handler.process(process_payload)
        
        self.assertAlmostEqual(self.orderbook.bids[0][0], 4.00000000)
        self.assertAlmostEqual(self.orderbook.bids[0][1], 431.00000000)
        self.assertAlmostEqual(self.orderbook.asks[0][0], 0.0026)
        self.assertAlmostEqual(self.orderbook.asks[0][1], 100)

if __name__ == '__main__':
    unittest.main()
