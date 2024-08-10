import sys
import os

# Get the project root directory
project_root = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "..", "..", "..")
)

# Add the project root directory to the Python path
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# -------------------------------------------- #

import unittest
import numpy as np

from frameworks.exchange.hyperliquid.ws_handlers.orderbook import (
    Orderbook,
    HyperliquidOrderbookHandler,
)


class TestHyperliquidOrderbookHandler(unittest.TestCase):
    def setUp(self):
        self.orderbook = Orderbook(size=5)
        self.handler = HyperliquidOrderbookHandler(orderbook=self.orderbook)

    def test_refresh(self):
        recv = [
            [
                {"px": "19900", "sz": "1", "n": 1},
                {"px": "19800", "sz": "2", "n": 2},
                {"px": "19700", "sz": "3", "n": 3},
            ],
            [
                {"px": "20100", "sz": "1", "n": 1},
                {"px": "20200", "sz": "2", "n": 2},
                {"px": "20300", "sz": "3", "n": 3},
            ],
        ]

        self.handler.refresh(recv)

        expected_bids = np.array([[19900, 1], [19800, 2], [19700, 3]])
        expected_asks = np.array([[20100, 1], [20200, 2], [20300, 3]])

        np.testing.assert_array_equal(self.orderbook.bids, expected_bids)
        np.testing.assert_array_equal(self.orderbook.asks, expected_asks)
        self.assertEqual(self.orderbook.seq_id, 0)

    def test_process(self):
        recv = {
            "channel": "l2Book",
            "data": {
                "coin": "BTC",
                "time": 1722657437786,
                "levels": [
                    [
                        {"px": "61991.0", "sz": "0.46401", "n": 2},
                        {"px": "61989.0", "sz": "0.6316", "n": 7},
                    ],
                    [
                        {"px": "61993.0", "sz": "0.16717", "n": 5},
                        {"px": "61994.0", "sz": "0.07409", "n": 3},
                    ],
                ],
            },
        }

        self.handler.process(recv)

        expected_bids = np.array([[61991.0, 0.46401], [61989.0, 0.6316]])
        expected_asks = np.array([[61993.0, 0.16717], [61994.0, 0.07409]])

        np.testing.assert_array_equal(self.orderbook.bids, expected_bids)
        np.testing.assert_array_equal(self.orderbook.asks, expected_asks)
        self.assertEqual(self.orderbook.seq_id, 1722657437786)

    def test_process_only_bids(self):
        recv = {
            "channel": "l2Book",
            "data": {
                "coin": "BTC",
                "time": 1722657437786,
                "levels": [
                    [
                        {"px": "61991.0", "sz": "0.46401", "n": 2},
                        {"px": "61989.0", "sz": "0.6316", "n": 7},
                    ],
                    [
                        {"px": "61993.0", "sz": "0.16717", "n": 5},
                        {"px": "61994.0", "sz": "0.07409", "n": 3},
                    ],
                ],
            },
        }

        self.handler.refresh(recv)

        process_payload = {
            "channel": "l2Book",
            "data": {
                "coin": "BTC",
                "time": 1722657437786,
                "levels": [[{"px": "0.0024", "sz": "10"}], []],
            },
        }

        self.handler.process(process_payload)

        expected_bids = np.array([[0.0024, 10]])
        expected_asks = np.array([[61993.0, 0.16717], [61994.0, 0.07409]])

        np.testing.assert_array_equal(self.orderbook.bids, expected_bids)
        np.testing.assert_array_equal(self.orderbook.asks, expected_asks)
        self.assertEqual(self.orderbook.seq_id, 1722657437786)

    def test_process_only_asks(self):
        recv = {
            "channel": "l2Book",
            "data": {
                "coin": "BTC",
                "time": 1722657437786,
                "levels": [
                    [
                        {"px": "61991.0", "sz": "0.46401", "n": 2},
                        {"px": "61989.0", "sz": "0.6316", "n": 7},
                    ],
                    [
                        {"px": "61993.0", "sz": "0.16717", "n": 5},
                        {"px": "61994.0", "sz": "0.07409", "n": 3},
                    ],
                ],
            },
        }

        self.handler.refresh(recv)

        process_payload = {
            "channel": "l2Book",
            "data": {
                "coin": "BTC",
                "time": 1722657437786,
                "levels": [[], [{"px": "0.0026", "sz": "100"}]],
            },
        }

        self.handler.process(process_payload)

        expected_bids = np.array([[61991.0, 0.46401], [61989.0, 0.6316]])
        expected_asks = np.array([[0.0026, 100]])

        np.testing.assert_array_equal(self.orderbook.bids, expected_bids)
        np.testing.assert_array_equal(self.orderbook.asks, expected_asks)
        self.assertEqual(self.orderbook.seq_id, 1722657437786)


if __name__ == "__main__":
    unittest.main()
