import sys
import os

# Get the project root directory
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..', '..', '..'))

# Add the project root directory to the Python path
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# -------------------------------------------- #

import unittest
from frameworks.exchange.base.ws_handlers.position import Position
from frameworks.exchange.binance.ws_handlers.position import BinancePositionHandler
from frameworks.exchange.binance.types import BinancePositionDirectionConverter

class TestBinancePositionHandler(unittest.TestCase):
    def setUp(self):
        self.position = Position()
        self.handler = BinancePositionHandler(position=self.position, symbol="BTCUSDT")
        self.position_side_converter = BinancePositionDirectionConverter()

    def test_refresh(self):
        payload = [
            {
                "symbol": "BTCUSDT",
                "positionSide": "BOTH",
                "positionAmt": "30",
                "entryPrice": "0.385",
                "breakEvenPrice": "0.385077",
                "markPrice": "0.41047590",
                "unRealizedProfit": "0.76427700",
                "liquidationPrice": "0",
                "isolatedMargin": "0",
                "notional": "12.31427700",
                "marginAsset": "USDT",
                "isolatedWallet": "0",
                "initialMargin": "0.61571385",
                "maintMargin": "0.08004280",
                "positionInitialMargin": "0.61571385",
                "openOrderInitialMargin": "0",
                "adl": 2,
                "bidNotional": "0",
                "askNotional": "0",
                "updateTime": 1720736417660
            }
        ]
        
        self.handler.refresh(payload)
        
        self.assertEqual(self.position.symbol, "BTCUSDT")
        self.assertEqual(self.position.side, self.position_side_converter.to_num("BOTH"))
        self.assertAlmostEqual(self.position.price, 0.385)
        self.assertAlmostEqual(self.position.size, 30)
        self.assertAlmostEqual(self.position.uPnl, 0.76427700)

    def test_process(self):
        payload = {
            "e": "ACCOUNT_UPDATE",
            "E": 1564745798939,
            "T": 1564745798938,
            "a": {
                "m": "ORDER",
                "B": [
                    {
                        "a": "USDT",
                        "wb": "122624.12345678",
                        "cw": "100.12345678",
                        "bc": "50.12345678"
                    },
                    {
                        "a": "BUSD",
                        "wb": "1.00000000",
                        "cw": "0.00000000",
                        "bc": "-49.12345678"
                    }
                ],
                "P": [
                    {
                        "s": "BTCUSDT",
                        "pa": "20",
                        "ep": "6563.66500",
                        "bep": "0",
                        "cr": "0",
                        "up": "2850.21200",
                        "mt": "isolated",
                        "iw": "13200.70726908",
                        "ps": "LONG"
                    }
                ]
            }
        }
        
        self.handler.process(payload)
        
        self.assertEqual(self.position.symbol, "BTCUSDT")
        self.assertEqual(self.position.side, self.position_side_converter.to_num("LONG"))
        self.assertAlmostEqual(self.position.price, 6563.66500)
        self.assertAlmostEqual(self.position.size, 20)
        self.assertAlmostEqual(self.position.uPnl, 2850.21200)

    def test_process_multiple_positions(self):
        payload = {
            "e": "ACCOUNT_UPDATE",
            "E": 1564745798939,
            "T": 1564745798938,
            "a": {
                "m": "ORDER",
                "B": [
                    {
                        "a": "USDT",
                        "wb": "122624.12345678",
                        "cw": "100.12345678",
                        "bc": "50.12345678"
                    },
                    {
                        "a": "BUSD",
                        "wb": "1.00000000",
                        "cw": "0.00000000",
                        "bc": "-49.12345678"
                    }
                ],
                "P": [
                    {
                        "s": "BTCUSDT",
                        "pa": "20",
                        "ep": "6563.66500",
                        "bep": "0",
                        "cr": "0",
                        "up": "2850.21200",
                        "mt": "isolated",
                        "iw": "13200.70726908",
                        "ps": "LONG"
                    },
                    {
                        "s": "BTCUSDT",
                        "pa": "-10",
                        "ep": "6563.86000",
                        "bep": "6563.6",
                        "cr": "-45.04000000",
                        "up": "-1423.15600",
                        "mt": "isolated",
                        "iw": "6570.42511771",
                        "ps": "SHORT"
                    }
                ]
            }
        }
        
        self.handler.process(payload)
        
        self.assertEqual(self.position.symbol, "BTCUSDT")
        self.assertEqual(self.position.side, self.position_side_converter.to_num("LONG"))
        self.assertAlmostEqual(self.position.price, 6563.66500)
        self.assertAlmostEqual(self.position.size, 20)
        self.assertAlmostEqual(self.position.uPnl, 2850.21200)

        self.handler.process({
            "e": "ACCOUNT_UPDATE",
            "E": 1564745798939,
            "T": 1564745798938,
            "a": {
                "m": "ORDER",
                "B": [
                    {
                        "a": "USDT",
                        "wb": "122624.12345678",
                        "cw": "100.12345678",
                        "bc": "50.12345678"
                    },
                    {
                        "a": "BUSD",
                        "wb": "1.00000000",
                        "cw": "0.00000000",
                        "bc": "-49.12345678"
                    }
                ],
                "P": [
                    {
                        "s": "BTCUSDT",
                        "pa": "-10",
                        "ep": "6563.86000",
                        "bep": "6563.6",
                        "cr": "-45.04000000",
                        "up": "-1423.15600",
                        "mt": "isolated",
                        "iw": "6570.42511771",
                        "ps": "SHORT"
                    }
                ]
            }
        })

        self.assertEqual(self.position.symbol, "BTCUSDT")
        self.assertEqual(self.position.side, self.position_side_converter.to_num("SHORT"))
        self.assertAlmostEqual(self.position.price, 6563.86000)
        self.assertAlmostEqual(self.position.size, -10)
        self.assertAlmostEqual(self.position.uPnl, -1423.15600)

if __name__ == '__main__':
    unittest.main()
