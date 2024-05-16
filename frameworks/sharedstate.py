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
    def __init__(self) -> None:
        self.data = {
            "tick_size": 0.0,
            "lot_size": 0.0,

            "ohlcv": RingBuffer(1000, dtype=(np.float64, 6)),
            "trades": RingBuffer(1000, dtype=(np.float64, 4)),
            "orderbook": Orderbook(50), # NOTE: Modify OB size if required!
            "ticker": {},

            "position": {},
            "orders": {},
            "account_balance": 0.0,
        }

        self.logging = Logger(
            print_to_console=True,
            discord_webhook=""
        )
        self.param_path = self.set_parameters_path()
        self.load_config()

        self.client = None
        self.symbol = ""
        self.parameters = {}
        self.load_parameters()

    @abstractmethod
    def set_parameters_path(self) -> str:
        pass

    @abstractmethod
    def process_parameters(self, parameters: Dict, reload: bool) -> None:
        """
        Process YAML file here
        """
        pass
    
    def load_exchange(self, exchange: str) -> None:
        match exchange.lower():
            case "binance":
                from frameworks.exchange.binance.exchange import Binance
                from frameworks.exchange.binance.websocket import BinanceWebsocket

                self.exchange = Binance(self.api_key, self.api_secret)
                self.exchange.load_required_refs(
                    logging=self.logging,
                    symbol=self.symbol,
                    data=self.data
                )

                self.websocket = BinanceWebsocket(self.exchange)
                self.websocket.load_required_refs(
                    logging=self.logging,
                    symbol=self.symbol,
                    data=self.data
                )

                print("Successfully loaded Binance.")

            case "bybit": 
                from frameworks.exchange.bybit.exchange import Bybit
                from frameworks.exchange.bybit.websocket import BybitWebsocket

                self.exchange = Bybit(self.api_key, self.api_secret)
                self.exchange.load_required_refs(
                    logging=self.logging,
                    symbol=self.symbol,
                    data=self.data
                )

                self.websocket = BybitWebsocket(self.exchange)
                self.websocket.load_required_refs(
                    logging=self.logging,
                    symbol=self.symbol,
                    data=self.data
                )

                print("Successfully loaded Bybit.")

            # case "okx": 
            #     self.exchange = Okx
            #     self.websocket = OkxWebsocket

            # case "kraken":
            #     self.exchange = Kraken
            #     self.websocket = KrakenWebsocket

            case "hyperliquid":
                from frameworks.exchange.hyperliquid.exchange import Hyperliquid
                from frameworks.exchange.hyperliquid.websocket import HyperliquidWebsocket

                self.exchange = Hyperliquid(self.api_key, self.api_secret)
                self.exchange.load_required_refs(
                    logging=self.logging,
                    symbol=self.symbol,
                    data=self.data
                )

                self.websocket = HyperliquidWebsocket(self.exchange)
                self.websocket.load_required_refs(
                    logging=self.logging,
                    symbol=self.symbol,
                    data=self.data
                )

            # case "paradex":
            #     self.exchange = Paradex
            #     self.websocket = ParadexWebsocket

            # case "vertex": 
            #     self.exchange = Vertex
            #     self.websocket = VertexWebsocket

            case _:
                self.logging.critical("Invalid exchange name, not found...")
                raise Exception("Invalid exchange name, not found...")

    def load_config(self) -> None:
        try:
            self.api_key = os.getenv("API_KEY")
            self.api_secret = os.getenv("API_SECRET")
                
            if not self.api_key or not self.api_secret:
                raise Exception("Missing/incorrect API credentials!")
            
        except Exception as e:
            self.logging.critical(e)
            raise e

    def load_parameters(self, reload: bool=False) -> None:
        """
        Loads initial trading settings from the parameters YAML file.
        """
        with open(self.param_path, "r") as f:
            params = yaml.safe_load(f)
            self.process_parameters(params, reload)

    async def start_internal_processes(self) -> None:
        await asyncio.gather(*[
            self.exchange.warmup(),
            self.websocket.start()
        ])

    async def refresh_parameters(self) -> Coroutine:
        """
        Periodically refreshes trading parameters from the parameters file.
        """
        while True:
            await asyncio.sleep(10)     # NOTE: Can be altered as needed
            self.load_parameters(reload=True)