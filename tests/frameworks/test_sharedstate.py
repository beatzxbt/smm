import sys
import os

# Get the project root directory
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))

# Add the project root directory to the Python path
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# -------------------------------------------- #

import asyncio
import unittest
from unittest.mock import MagicMock, patch, mock_open
from numpy_ringbuffer import RingBuffer
from frameworks.exchange.base.structures.orderbook import Orderbook
from frameworks.exchange.base.constants import Position
from frameworks.sharedstate import SharedState

class TestableSharedState(SharedState):
    def set_parameters_path(self):
        return "path/to/parameters.yaml"

    def process_parameters(self, parameters, reload) -> None:
        pass

class TestSharedState(unittest.TestCase):
    def setUp(self):
        # Mock the YAML file content
        self.mock_yaml_content = """
        parameter1: value1
        parameter2: value2
        """
        # Mock the open function and yaml.safe_load
        self.mock_open = mock_open(read_data=self.mock_yaml_content)
        self.patcher_open = patch("builtins.open", self.mock_open)
        self.patcher_yaml = patch("yaml.safe_load", return_value={"parameter1": "value1", "parameter2": "value2"})
        self.patcher_open.start()
        self.patcher_yaml.start()
        
        self.shared_state = TestableSharedState(debug=True)
        
    def tearDown(self):
        self.patcher_open.stop()
        self.patcher_yaml.stop()
        
    @patch('frameworks.sharedstate.Logger')
    def test_initial_state(self, MockLogger):
        self.assertIsInstance(self.shared_state.data, dict)
        self.assertIsInstance(self.shared_state.data["ohlcv"], RingBuffer)
        self.assertIsInstance(self.shared_state.data["trades"], RingBuffer)
        self.assertIsInstance(self.shared_state.data["orderbook"], Orderbook)
        self.assertIsInstance(self.shared_state.data["position"], Position)
        self.assertEqual(self.shared_state.data["account_balance"], 0.0)
        self.assertIsInstance(self.shared_state.logging, MockLogger)
        self.assertEqual(self.shared_state.symbol, "")
        self.assertIsInstance(self.shared_state.parameters, dict)

    def test_set_parameters_path(self):
        self.assertEqual(self.shared_state.set_parameters_path(), "path/to/parameters.yaml")

    def test_process_parameters(self):
        self.shared_state.process_parameters(parameters={}, reload=False)
        self.assertTrue(True)  # If no exception is raised, the test passes

    @patch('os.getenv')
    def test_load_config(self, mock_getenv):
        mock_getenv.side_effect = lambda key: "dummy_key" if key == "API_KEY" else "dummy_secret" if key == "API_SECRET" else None
        self.shared_state.load_config()
        self.assertEqual(self.shared_state.api_key, "dummy_key")
        self.assertEqual(self.shared_state.api_secret, "dummy_secret")

    @patch('os.getenv')
    def test_load_config_missing_credentials(self, mock_getenv):
        mock_getenv.side_effect = lambda key: None
        with self.assertRaises(Exception):
            self.shared_state.load_config()

    def test_load_parameters(self):
        self.shared_state.process_parameters = MagicMock()
        self.shared_state.load_parameters()
        self.shared_state.process_parameters.assert_called_once_with({"parameter1": "value1", "parameter2": "value2"}, False)

    def test_load_parameters_exception(self):
        # Simulate an exception when opening the file
        self.patcher_open.stop()
        self.mock_open = mock_open()
        self.mock_open.side_effect = FileNotFoundError
        with patch("builtins.open", self.mock_open):
            with self.assertRaises(Exception):
                self.shared_state.load_parameters()

    @patch('asyncio.gather')
    @patch.object(TestableSharedState, 'start_internal_processes', new_callable=MagicMock)
    def test_start_internal_processes(self, mock_start_internal_processes, mock_gather):
        loop = asyncio.get_event_loop()
        loop.run_until_complete(self.shared_state.start_internal_processes())
        mock_gather.assert_called_once()

    @patch('asyncio.sleep', new_callable=MagicMock)
    def test_refresh_parameters(self, mock_sleep):
        self.shared_state.load_parameters = MagicMock()
        loop = asyncio.get_event_loop()
        loop.run_until_complete(self.shared_state.refresh_parameters(0.1))
        self.assertGreater(self.shared_state.load_parameters.call_count, 1)

if __name__ == '__main__':
    unittest.main()
