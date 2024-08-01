import sys
import os

# Get the project root directory
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))

# Add the project root directory to the Python path
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# -------------------------------------------- #

import unittest
from frameworks.exchange.base.constants import (
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
