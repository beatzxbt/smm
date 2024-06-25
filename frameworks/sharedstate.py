import asyncio
import os
import yaml
import numpy as np
from abc import ABC, abstractmethod
from typing import Dict
from numpy_ringbuffer import RingBuffer

from frameworks.tools.logging import Logger
from frameworks.exchange.base.exchange import Exchange
from frameworks.exchange.base.websocket import WebsocketStream
from frameworks.exchange.base.structures.orderbook import Orderbook


class SharedState(ABC):
    def __init__(self, debug) -> None:
        """
        Initializes the SharedState class with default values.

        Attributes
        ----------
        data : Dict
            A dictionary holding various shared state data like tick size, lot size, OHLCV data, trades, orderbook, etc.

        logging : Logger
            A Logger instance for logging events and messages.

        param_path : str
            The file path to the parameters YAML file.

        client : None
            Placeholder for the client object, to be defined in subclasses.

        symbol : str
            The trading symbol, to be set in subclasses.

        parameters : Dict
            A dictionary to hold parameters loaded from the YAML file.

        """
        self.debug = debug

        self.data = {
            "tick_size": 0.0,
            "lot_size": 0.0,

            "ohlcv": RingBuffer(1000, dtype=(np.float64, 6)),
            "trades": RingBuffer(1000, dtype=(np.float64, 4)),
            "orderbook": Orderbook(50), # NOTE: Modify OB size if required!
            "ticker": {
                "markPrice": 0.0,
                "indexPrice": 0.0,
                "fundingTime": 0.0,
                "fundingRate": 0.0,
            },

            "position": {
                "createTime": 0.0,
                "price": 0.0, 
                "size": 0.0, 
                "uPnl": 0.0
            },
            "orders": {},
            "account_balance": 0.0,
        }

        self.logging = Logger(debug_mode=self.debug)
        self.param_path = self.set_parameters_path()
        self.load_config()

        self.exchange: Exchange = None
        self.websocket: WebsocketStream = None

        self.symbol = ""
        self.parameters = {}
        self.load_parameters()

    @abstractmethod
    def set_parameters_path(self) -> str:
        """
        Abstract method to set the path of the parameters YAML file.

        Returns
        -------
        str
            The file path to the parameters YAML file.
        """
        pass

    @abstractmethod
    def process_parameters(self, parameters: Dict, reload: bool) -> None:
        """
        Abstract method to process the parameters from the YAML file.

        Parameters
        ----------
        parameters : dict
            The dictionary of parameters loaded from the YAML file.

        reload : bool
            Flag to indicate if the parameters are being reloaded.
        """
        pass
    
    def load_exchange(self, exchange: str) -> None:
        """
        Loads the specified exchange and initializes the exchange and websocket objects.

        Parameters
        ----------
        exchange : str
            The name of the exchange to be loaded.

        Raises
        ------
        Exception
            If the specified exchange is not found or invalid.
        """
        match exchange.lower():
            case "binance":
                from frameworks.exchange.binance.exchange import Binance
                from frameworks.exchange.binance.websocket import BinanceWebsocket

                # NOTE: Binance requires capital symbols
                self.symbol = self.symbol.upper()

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

            case "bybit": 
                from frameworks.exchange.bybit.exchange import Bybit
                from frameworks.exchange.bybit.websocket import BybitWebsocket

                # NOTE: Bybit requires capital symbols
                self.symbol = self.symbol.upper()

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

            case "dydx_v4":
                from frameworks.exchange.dydx_v4.exchange import Dydx
                from frameworks.exchange.dydx_v4.websocket import DydxWebsocket

                self.exchange = Dydx(self.api_key, self.api_secret)
                self.exchange.load_required_refs(
                    logging=self.logging,
                    symbol=self.symbol,
                    data=self.data
                )

                self.websocket = DydxWebsocket(self.exchange)
                self.websocket.load_required_refs(
                    logging=self.logging,
                    symbol=self.symbol,
                    data=self.data
                )

            # TODO: Add Paradex, OKX, Vertex, Kraken (in that order)

            case _:
                raise ValueError("Invalid exchange name, not found...")

    def load_config(self) -> None:
        """
        Loads the API credentials from environment variables.

        Raises
        ------
        Exception
            If the API credentials are missing or incorrect.
        """
        self.api_key = os.getenv("API_KEY")
        self.api_secret = os.getenv("API_SECRET")
            
        if not self.api_key or not self.api_secret:
            raise Exception("Missing/incorrect API credentials!")
            
    def load_parameters(self, reload: bool=False) -> None:
        """
        Loads initial trading settings from the parameters YAML file.

        Parameters
        ----------
        reload : bool, optional
            Flag to indicate if the parameters are being reloaded (default is False).
        """
        try:
            with open(self.param_path, "r") as f:
                params = yaml.safe_load(f)
                self.process_parameters(params, reload)

        except Exception as e:
            raise Exception(f"Error loading parameters: {e}")
    
    async def start_internal_processes(self) -> None:
        """
        Starts the internal processes such as warming up the exchange and starting the websocket.
        """
        tasks = [
            self.exchange.warmup(),
            self.websocket.start()
        ]

        await asyncio.gather(*tasks)

    async def refresh_parameters(self, interval: float=10.0) -> None:
        """
        Periodically refreshes trading parameters from the parameters file.
        """
        self.load_parameters(reload=False)
        while True:
            await asyncio.sleep(interval)
            self.load_parameters(reload=True)