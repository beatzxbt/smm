import sys
import os

# Get the project root directory
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..', '..', '..'))

# Add the project root directory to the Python path
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# -------------------------------------------- #

import unittest
from frameworks.exchange.base.ws_handlers.orders import Order, Orders
from frameworks.exchange.binance.ws_handlers.orders import BinanceOrdersHandler
from frameworks.exchange.binance.types import (
    BinanceSideConverter, 
    BinanceOrderTypeConverter, 
    BinanceTimeInForceConverter
)

class TestBinanceOrdersHandler(unittest.TestCase):
    def setUp(self):
        self.orders = Orders()
        self.handler = BinanceOrdersHandler(orders=self.orders, symbol="BTCUSDT")

    def test_refresh(self):
        payload = [
            {
                "avgPrice": "0.00000",
                "clientOrderId": "abc",
                "cumQuote": "0",
                "executedQty": "0",
                "orderId": 1917641,
                "origQty": "0.40",
                "origType": "LIMIT",
                "price": "0",
                "reduceOnly": False,
                "side": "BUY",
                "positionSide": "SHORT",
                "status": "NEW",
                "stopPrice": "9300",
                "closePosition": False,
                "symbol": "BTCUSDT",
                "time": 1579276756075,
                "timeInForce": "GTC",
                "type": "LIMIT",
                "activatePrice": "9020",
                "priceRate": "0.3",
                "updateTime": 1579276756075,
                "workingType": "CONTRACT_PRICE",
                "priceProtect": False,
                "priceMatch": "NONE",
                "selfTradePreventionMode": "NONE",
                "goodTillDate": 0
            }
        ]
        
        self.handler.refresh(payload)
        
        order = self.orders["1917641"]
        self.assertEqual(order.symbol, "BTCUSDT")
        self.assertEqual(order.side, BinanceSideConverter().to_num("BUY"))
        self.assertEqual(order.orderType, BinanceOrderTypeConverter().to_num("LIMIT"))
        self.assertEqual(order.timeInForce, BinanceTimeInForceConverter().to_num("GTC"))
        self.assertAlmostEqual(order.price, 0.0)
        self.assertAlmostEqual(order.size, 0.4)

    def test_process(self):
        payload = {
            "e": "ORDER_TRADE_UPDATE",
            "E": 1568879465651,
            "T": 1568879465650,
            "o": {
                "s": "BTCUSDT",
                "c": "TEST",
                "S": "SELL",
                "o": "LIMIT",
                "f": "GTC",
                "q": "0.001",
                "p": "0",
                "ap": "0",
                "sp": "7103.04",
                "x": "NEW",
                "X": "NEW",
                "i": 8886774,
                "l": "0",
                "z": "0",
                "L": "0",
                "N": "USDT",
                "n": "0",
                "T": 1568879465650,
                "t": 0,
                "b": "0",
                "a": "9.91",
                "m": False,
                "R": False,
                "wt": "CONTRACT_PRICE",
                "ot": "LIMIT",
                "ps": "LONG",
                "cp": False,
                "AP": "7476.89",
                "cr": "5.0",
                "pP": False,
                "si": 0,
                "ss": 0,
                "rp": "0",
                "V": "EXPIRE_TAKER",
                "pm": "OPPONENT",
                "gtd": 0
            }
        }
        
        self.handler.process(payload)
        
        order = self.orders["8886774"]
        self.assertEqual(order.symbol, "BTCUSDT")
        self.assertEqual(order.side, BinanceSideConverter().to_num("SELL"))
        self.assertEqual(order.orderType, BinanceOrderTypeConverter().to_num("LIMIT"))
        self.assertEqual(order.timeInForce, BinanceTimeInForceConverter().to_num("GTC"))
        self.assertAlmostEqual(order.price, 0.0)
        self.assertAlmostEqual(order.size, 0.001)

    def test_process_remove_order(self):
        # Initial state to simulate a filled order book
        refresh_payload = [
            {
                "avgPrice": "0.00000",
                "clientOrderId": "abc",
                "cumQuote": "0",
                "executedQty": "0",
                "orderId": 1917641,
                "origQty": "0.40",
                "origType": "LIMIT",
                "price": "0",
                "reduceOnly": False,
                "side": "BUY",
                "positionSide": "SHORT",
                "status": "NEW",
                "stopPrice": "9300",
                "closePosition": False,
                "symbol": "BTCUSDT",
                "time": 1579276756075,
                "timeInForce": "GTC",
                "type": "LIMIT",
                "activatePrice": "9020",
                "priceRate": "0.3",
                "updateTime": 1579276756075,
                "workingType": "CONTRACT_PRICE",
                "priceProtect": False,
                "priceMatch": "NONE",
                "selfTradePreventionMode": "NONE",
                "goodTillDate": 0
            }
        ]
        self.handler.refresh(refresh_payload)
        
        process_payload = {
            "e": "ORDER_TRADE_UPDATE",
            "E": 1568879465651,
            "T": 1568879465650,
            "o": {
                "s": "BTCUSDT",
                "c": "TEST",
                "S": "SELL",
                "o": "LIMIT",
                "f": "GTC",
                "q": "0.001",
                "p": "0",
                "ap": "0",
                "sp": "7103.04",
                "x": "NEW",
                "X": "CANCELLED",
                "i": 1917641,
                "l": "0",
                "z": "0",
                "L": "0",
                "N": "USDT",
                "n": "0",
                "T": 1568879465650,
                "t": 0,
                "b": "0",
                "a": "9.91",
                "m": False,
                "R": False,
                "wt": "CONTRACT_PRICE",
                "ot": "LIMIT",
                "ps": "LONG",
                "cp": False,
                "AP": "7476.89",
                "cr": "5.0",
                "pP": False,
                "si": 0,
                "ss": 0,
                "rp": "0",
                "V": "EXPIRE_TAKER",
                "pm": "OPPONENT",
                "gtd": 0
            }
        }
        
        self.handler.process(process_payload)
        
        self.assertNotIn("1917641", self.orders)

if __name__ == '__main__':
    unittest.main()
