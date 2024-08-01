import sys
import os

# Get the project root directory
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))

# Add the project root directory to the Python path
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# -------------------------------------------- #

import unittest
from frameworks.exchange.base.structures.order import Order, Orders
from frameworks.exchange.base.constants import (
    Side,
    OrderType,
    TimeInForce
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

class TestOrders(unittest.TestCase):
    def setUp(self):
        self.orders = Orders()
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
        self.orders.add_single(self.order)

    def test_add_single_order(self):
        self.assertEqual(len(self.orders._orders_), 1)
        self.assertIn(self.order.orderId, self.orders._orders_)
        self.assertEqual(self.orders[self.order.orderId], self.order)

    def test_add_many_orders(self):
        order2 = Order(
            symbol="ETHUSD",
            side=Side.SELL,
            orderType=OrderType.LIMIT,
            timeInForce=TimeInForce.POST_ONLY,
            size=2.0,
            price=2500.0,
            orderId="order456",
            clientOrderId="clientorder456",
        )
        self.orders.add_many([self.order, order2])
        self.assertEqual(len(self.orders._orders_), 2)
        self.assertIn(self.order.orderId, self.orders._orders_)
        self.assertIn(order2.orderId, self.orders._orders_)
        self.assertEqual(self.orders[self.order.orderId], self.order)
        self.assertEqual(self.orders[order2.orderId], order2)

    def test_reset_orders(self):
        self.orders.reset()
        self.assertEqual(len(self.orders._orders_), 0)

    def test_get_order_by_id(self):
        self.assertEqual(self.orders[self.order.orderId], self.order)

if __name__ == '__main__':
    unittest.main()
