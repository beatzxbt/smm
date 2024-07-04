import sys
import os

# Get the project root directory
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))

# Add the project root directory to the Python path
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# -------------------------------------------- #

import unittest
from frameworks.exchange.base.orderid import OrderIdGenerator

class TestOrderIdGenerator(OrderIdGenerator):
    def generate_random_str(self, length: int) -> str:
        return "X" * length

class TestOrderIdGeneratorImplementation(unittest.TestCase):
    def setUp(self):
        self.max_len = 10
        self.generator = TestOrderIdGenerator(self.max_len)

    def test_generate_random_str(self):
        random_str = self.generator.generate_random_str(5)
        self.assertEqual(random_str, "XXXXX")

    def test_generate_order_id_with_no_start_end(self):
        order_id = self.generator.generate_order_id()
        self.assertEqual(order_id, "X" * self.max_len)

    def test_generate_order_id_with_start(self):
        start = "START"
        order_id = self.generator.generate_order_id(start=start)
        expected_len = self.max_len - len(start)
        self.assertEqual(order_id, start + "X" * expected_len)
        self.assertEqual(len(order_id), self.max_len)

    def test_generate_order_id_with_end(self):
        end = "END"
        order_id = self.generator.generate_order_id(end=end)
        expected_len = self.max_len - len(end)
        self.assertEqual(order_id, "X" * expected_len + end)
        self.assertEqual(len(order_id), self.max_len)

    def test_generate_order_id_with_start_and_end(self):
        start = "START"
        end = "END"
        order_id = self.generator.generate_order_id(start=start, end=end)
        expected_len = self.max_len - len(start) - len(end)
        self.assertEqual(order_id, start + "X" * expected_len + end)
        self.assertEqual(len(order_id), self.max_len)

    def test_generate_order_id_length_limit(self):
        start = "LONGSTART"
        end = "LONGEND"
        with self.assertRaises(ValueError):
            self.generator.generate_order_id(start=start, end=end)

if __name__ == '__main__':
    unittest.main()
