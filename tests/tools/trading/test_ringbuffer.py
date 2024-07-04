import sys
import os

# Get the project root directory
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))

# Add the project root directory to the Python path
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# -------------------------------------------- #

import unittest
from frameworks.tools.trading.ringbuffer import RingBufferF64


class TestRingBufferF64(unittest.TestCase):
    def setUp(self):
        self.capacity = 5
        self.buffer = RingBufferF64(self.capacity)

    def test_initial_state(self):
        self.assertEqual(len(self.buffer), 0)
        self.assertFalse(self.buffer.is_full)
    
    def test_appendright(self):
        self.buffer.appendright(1.1)
        self.buffer.appendright(2.2)
        self.assertEqual(len(self.buffer), 2)
        self.assertEqual(self.buffer[0], 1.1)
        self.assertEqual(self.buffer[1], 2.2)

    def test_appendleft(self):
        self.buffer.appendleft(1.1)
        self.buffer.appendleft(2.2)
        self.assertEqual(len(self.buffer), 2)
        self.assertEqual(self.buffer[0], 2.2)
        self.assertEqual(self.buffer[1], 1.1)
    
    def test_popright(self):
        self.buffer.appendright(1.1)
        self.buffer.appendright(2.2)
        self.assertEqual(self.buffer.popright(), 2.2)
        self.assertEqual(len(self.buffer), 1)
        self.assertEqual(self.buffer.popright(), 1.1)
        self.assertEqual(len(self.buffer), 0)
        with self.assertRaises(IndexError):
            self.buffer.popright()
    
    def test_popleft(self):
        self.buffer.appendright(1.1)
        self.buffer.appendright(2.2)
        self.assertEqual(self.buffer.popleft(), 1.1)
        self.assertEqual(len(self.buffer), 1)
        self.assertEqual(self.buffer.popleft(), 2.2)
        self.assertEqual(len(self.buffer), 0)
        with self.assertRaises(IndexError):
            self.buffer.popleft()
    
    def test_is_full(self):
        for i in range(self.capacity):
            self.buffer.appendright(float(i))
        self.assertTrue(self.buffer.is_full)
        self.buffer.appendright(5.5)
        self.assertTrue(self.buffer.is_full)
        self.assertEqual(len(self.buffer), self.capacity)

    def test_reset(self):
        for i in range(self.capacity):
            self.buffer.appendright(float(i))
        data = self.buffer.reset()
        self.assertEqual(len(self.buffer), 0)
        self.assertEqual(len(data), self.capacity)

    def test_len(self):
        self.assertEqual(len(self.buffer), 0)
        self.buffer.appendright(1.1)
        self.assertEqual(len(self.buffer), 1)
        self.buffer.appendright(2.2)
        self.assertEqual(len(self.buffer), 2)
    
    def test_getitem(self):
        self.buffer.appendright(1.1)
        self.buffer.appendright(2.2)
        self.assertEqual(self.buffer[0], 1.1)
        self.assertEqual(self.buffer[1], 2.2)
        self.buffer.appendleft(0.0)
        self.assertEqual(self.buffer[0], 0.0)
        self.assertEqual(self.buffer[1], 1.1)
        self.assertEqual(self.buffer[2], 2.2)

if __name__ == '__main__':
    unittest.main()