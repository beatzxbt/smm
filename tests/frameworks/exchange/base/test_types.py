import sys
import os

# Get the project root directory
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))

# Add the project root directory to the Python path
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# -------------------------------------------- #

import unittest
from frameworks.exchange.base.types import (
    Order,
    Position,
    Side,
    OrderType,
    TimeInForce,
    PositionDirection,
    StrNumConverter,
    SideConverter,
    OrderTypeConverter,
    TimeInForceConverter,
    PositionDirectionConverter
)

class TestOrder(unittest.TestCase):
    def setUp(self):
        self.order = Order(
            symbol="BTCUSD",
            side=Side.BUY,
            orderType=OrderType.LIMIT,
            timeInForce=TimeInForce.GTC,
            size=1.0,
            price=50000.0,
            orderId="order123",
            clientOrderId="clientorder123",
        )

    def test_order_initialization(self):
        self.assertEqual(self.order.symbol, "BTCUSD")
        self.assertEqual(self.order.side, Side.BUY)
        self.assertEqual(self.order.orderType, OrderType.LIMIT)
        self.assertEqual(self.order.timeInForce, TimeInForce.GTC)
        self.assertEqual(self.order.size, 1.0)
        self.assertEqual(self.order.price, 50000.0)
        self.assertEqual(self.order.orderId, "order123")
        self.assertEqual(self.order.clientOrderId, "clientorder123")

    def test_order_repr(self):
        self.assertEqual(
            repr(self.order),
            "Order(symbol=BTCUSD, side=0, orderType=0, timeInForce=0, price=50000.0, size=1.0, orderId=order123, clientOrderId=clientorder123)",
        )

    def test_order_str(self):
        self.assertEqual(
            str(self.order),
            "Order: symbol=BTCUSD, side=0, orderType=0, timeInForce=0, price=50000.0, size=1.0, orderId=order123, clientOrderId=clientorder123",
        )

    def test_order_equality(self):
        order2 = Order(
            symbol="BTCUSD",
            side=Side.BUY,
            orderType=OrderType.LIMIT,
            timeInForce=TimeInForce.GTC,
            size=1.0,
            price=50000.0,
            orderId="order123",
            clientOrderId="clientorder123",
        )
        self.assertEqual(self.order, order2)

    def test_order_to_dict(self):
        order_dict = self.order.to_dict()
        expected_dict = {
            "symbol": "BTCUSD",
            "side": Side.BUY,
            "orderType": OrderType.LIMIT,
            "timeInForce": TimeInForce.GTC,
            "size": 1.0,
            "price": 50000.0,
            "orderId": "order123",
            "clientOrderId": "clientorder123",
        }
        self.assertEqual(order_dict, expected_dict)

    def test_order_from_dict(self):
        order_dict = {
            "symbol": "BTCUSD",
            "side": Side.BUY,
            "orderType": OrderType.LIMIT,
            "timeInForce": TimeInForce.GTC,
            "size": 1.0,
            "price": 50000.0,
            "orderId": "order123",
            "clientOrderId": "clientorder123",
        }
        order = Order.from_dict(order_dict)
        self.assertEqual(order, self.order)

class TestPosition(unittest.TestCase):
    def setUp(self):
        self.position = Position(
            symbol="BTCUSD",
            side=Side.BUY,
            price=50000.0,
            size=1.0,
            uPnl=1000.0,
        )

    def test_position_initialization(self):
        self.assertEqual(self.position.symbol, "BTCUSD")
        self.assertEqual(self.position.side, Side.BUY)
        self.assertEqual(self.position.price, 50000.0)
        self.assertEqual(self.position.size, 1.0)
        self.assertEqual(self.position.uPnl, 1000.0)

    def test_position_repr(self):
        self.assertEqual(
            repr(self.position),
            "Position(symbol=BTCUSD, side=0, price=50000.0, size=1.0, uPnl=1000.0)",
        )

    def test_position_str(self):
        self.assertEqual(
            str(self.position),
            "Position: symbol=BTCUSD, side=0, price=50000.0, size=1.0, uPnl=1000.0",
        )

    def test_position_to_dict(self):
        position_dict = self.position.to_dict()
        expected_dict = {
            "symbol": "BTCUSD",
            "side": Side.BUY,
            "price": 50000.0,
            "size": 1.0,
            "uPnl": 1000.0,
        }
        self.assertEqual(position_dict, expected_dict)

    def test_position_update(self):
        self.position.update(symbol="ETHUSD", price=2500.0, size=2.0, uPnl=200.0)
        self.assertEqual(self.position.symbol, "ETHUSD")
        self.assertEqual(self.position.price, 2500.0)
        self.assertEqual(self.position.size, 2.0)
        self.assertEqual(self.position.uPnl, 200.0)

    def test_position_clear(self):
        self.position.clear()
        self.assertIsNone(self.position.symbol)
        self.assertIsNone(self.position.side)
        self.assertIsNone(self.position.price)
        self.assertIsNone(self.position.size)
        self.assertIsNone(self.position.uPnl)

class TestStrNumConverter(unittest.TestCase):
    def test_to_str(self):
        converter = StrNumConverter({"one": 1, "two": 2})
        self.assertEqual(converter.to_str(1), "one")
        self.assertEqual(converter.to_str(3), "UNKNOWN")

    def test_to_num(self):
        converter = StrNumConverter({"one": 1, "two": 2})
        self.assertEqual(converter.to_num("one"), 1)
        self.assertEqual(converter.to_num("three"), -1)

class TestSideConverter(unittest.TestCase):
    def setUp(self):
        self.converter = SideConverter(BUY="BUY", SELL="SELL")

    def test_side_converter_to_str(self):
        self.assertEqual(self.converter.to_str(Side.BUY), "BUY")
        self.assertEqual(self.converter.to_str(99), "UNKNOWN")

    def test_side_converter_to_num(self):
        self.assertEqual(self.converter.to_num("BUY"), Side.BUY)
        self.assertEqual(self.converter.to_num("UNKNOWN"), -1)

class TestOrderTypeConverter(unittest.TestCase):
    def setUp(self):
        self.converter = OrderTypeConverter(
            LIMIT="LIMIT",
            MARKET="MARKET",
            STOP_LIMIT="STOP_LIMIT",
            TAKE_PROFIT_LIMIT="TAKE_PROFIT_LIMIT",
        )

    def test_order_type_converter_to_str(self):
        self.assertEqual(self.converter.to_str(OrderType.LIMIT), "LIMIT")
        self.assertEqual(self.converter.to_str(99), "UNKNOWN")

    def test_order_type_converter_to_num(self):
        self.assertEqual(self.converter.to_num("LIMIT"), OrderType.LIMIT)
        self.assertEqual(self.converter.to_num("UNKNOWN"), -1)

class TestTimeInForceConverter(unittest.TestCase):
    def setUp(self):
        self.converter = TimeInForceConverter(GTC="GTC", FOK="FOK", POST_ONLY="POST_ONLY")

    def test_time_in_force_converter_to_str(self):
        self.assertEqual(self.converter.to_str(TimeInForce.GTC), "GTC")
        self.assertEqual(self.converter.to_str(99), "UNKNOWN")

    def test_time_in_force_converter_to_num(self):
        self.assertEqual(self.converter.to_num("GTC"), TimeInForce.GTC)
        self.assertEqual(self.converter.to_num("UNKNOWN"), -1)

class TestPositionDirectionConverter(unittest.TestCase):
    def setUp(self):
        self.converter = PositionDirectionConverter(LONG="LONG", SHORT="SHORT")

    def test_position_direction_converter_to_str(self):
        self.assertEqual(self.converter.to_str(PositionDirection.LONG), "LONG")
        self.assertEqual(self.converter.to_str(99), "UNKNOWN")

    def test_position_direction_converter_to_num(self):
        self.assertEqual(self.converter.to_num("LONG"), PositionDirection.LONG)
        self.assertEqual(self.converter.to_num("UNKNOWN"), -1)

if __name__ == '__main__':
    unittest.main()
