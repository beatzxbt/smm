import asyncio
import os
import yaml
import numpy as np
from abc import ABC, abstractmethod
from typing import Dict, Coroutine
from numpy_ringbuffer import RingBuffer
from frameworks.tools.logging import Logger
from frameworks.exchange.base.structures.orderbook import Orderbook


class SharedState(ABC):
    PARAM_PATH = os.path.dirname(os.path.realpath(__file__)) + "/../parameters.yaml"  

    def __init__(self) -> None:
        self.logging = Logger
        self.load_config()
        self.load_parameters()

        self.symbol = ""
        self.ohlcv = RingBuffer(1000, dtype=(np.float64, 6))
        self.trades = RingBuffer(1000, dtype=(np.float64, 4))
        self.orderbook = Orderbook(50) # NOTE: Modify OB size if required!
        self.ticker = {}
        self.current_position = {}
        self.current_orders = {}
        self.account_balance = 0.
        self.misc = {"tick_size": 0, "lot_size": 0}

    @abstractmethod
    def process_parameters(self, parameters: Dict, reload: bool) -> None:
        """
        Process YAML file here
        """
        pass

    def load_config(self) -> None:
        try:
            self.api_key = os.getenv("API_KEY")
            self.api_secret = os.getenv("API_SECRET")
                
            if not self.api_key or not self.api_secret:
                raise ValueError("Missing/incorrect API credentials!")
            
        except ValueError as ve:
            self.logging.critical(ve)
            raise ve
        
        except Exception as e:
            self.logging.critical(e)
            raise e

    def load_parameters(self, reload: bool=False) -> None:
        """
        Loads initial trading settings from the parameters YAML file.
        """
        with open(self.PARAM_PATH, "r") as f:
            params = yaml.safe_load(f)
            self.process_parameters(params, reload)

    async def refresh_parameters(self) -> Coroutine:
        """
        Periodically refreshes trading parameters from the parameters file.
        """
        while True:
            await asyncio.sleep(10)     # NOTE: Can be altered as needed
            self.load_parameters(reload=True)