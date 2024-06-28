import asyncio
from abc import ABC, abstractmethod
from typing import Dict, Optional, Union

from frameworks.tools.logging import Logger
from frameworks.exchange.base.client import Client
from frameworks.exchange.base.formats import Formats
from frameworks.exchange.base.endpoints import Endpoints
from frameworks.exchange.base.orderid import OrderIdGenerator
from frameworks.exchange.base.types import Order


class Exchange(ABC):
    def __init__(
        self,
        client: Client,
        formats: Formats,
        endpoints: Endpoints,
        orderIdGenerator: OrderIdGenerator,
    ) -> None:
        """
        Initializes the Exchange class with the necessary components.

        Parameters
        ----------
        client : Client
            The client instance to interact with the exchange.

        formats : Formats
            The formats instance used to format various exchange-related data.

        endpoints : Endpoints
            The endpoints instance containing the URLs for the exchange's API endpoints.

        orderIdGenerator : OrderIdGenerator
            The order ID generator instance used to generate order IDs.
        """
        self.client = client
        self.formats = formats
        self.endpoints = endpoints
        self.base_endpoint = self.endpoints.main
        self.orderid = orderIdGenerator

    def load_required_refs(self, logging: Logger, symbol: str, data: Dict) -> None:
        """
        Loads required references such as logging, symbol, and data.

        Parameters
        ----------
        logging : Logger
            The Logger instance for logging events and messages.

        symbol : str
            The trading symbol.

        data : Dict
            A Dictionary holding various shared state data.
        """
        self.logging = logging
        self.symbol = symbol
        self.data = data
        self.client.load_required_refs(logging=logging)

    @abstractmethod
    async def warmup(self) -> None:
        """
        Abstract method for warming up the exchange-specific data.
        """
        pass

    @abstractmethod
    async def create_order(
        self,
        order: Order
    ) -> Dict:
        """
        Abstract method to create an order.

        Parameters
        ----------
        order: Order
            The order to send to the exchange.

        Returns
        -------
        Dict
            The response from the exchange.
        """
        pass

    @abstractmethod
    async def amend_order(
        self,
        order: Order
    ) -> Dict:
        """
        Abstract method to amend an existing order.

        Parameters
        ----------
        order: Order
            The order to modify/amend.

        Returns
        -------
        Dict
            The response from the exchange.
        """
        pass

    @abstractmethod
    async def cancel_order(
        self,
        order: Order
    ) -> Dict:
        """
        Abstract method to cancel an existing order.

        Parameters
        ----------
        order: Order
            The order to cancel.

        Returns
        -------
        Dict
            The response from the exchange.
        """
        pass

    @abstractmethod
    async def cancel_all_orders(self, symbol: str) -> Dict:
        """
        Abstract method to cancel all existing orders for a symbol.

        Parameters
        ----------
        symbol : str
            The trading symbol.

        Returns
        -------
        Dict
            The response from the exchange.
        """
        pass

    @abstractmethod
    async def get_ohlcv(self, symbol: str, interval: Union[int, str]) -> Dict:
        """
        Abstract method to get OHLCV (Open, High, Low, Close, Volume) data.

        Parameters
        ----------
        symbol : str
            The trading symbol.

        interval : Union[int, str]
            The interval for the OHLCV data.

        Returns
        -------
        Dict
            The OHLCV data from the exchange.
        """
        pass

    @abstractmethod
    async def get_trades(self, symbol: str) -> Dict:
        """
        Abstract method to get recent trades.

        Parameters
        ----------
        symbol : str
            The trading symbol.

        Returns
        -------
        Dict
            The trades data from the exchange.
        """
        pass

    @abstractmethod
    async def get_orderbook(self, symbol: str) -> Dict:
        """
        Abstract method to get an orderbook snapshot.

        Parameters
        ----------
        symbol : str
            The trading symbol.

        Returns
        -------
        Dict
            The order book data from the exchange.
        """
        pass

    @abstractmethod
    async def get_ticker(self, symbol: str) -> Dict:
        """
        Abstract method to get ticker data.

        Parameters
        ----------
        symbol : str
            The trading symbol.

        Returns
        -------
        Dict
            The ticker data from the exchange.
        """
        pass

    @abstractmethod
    async def get_open_orders(self, symbol: str) -> Dict:
        """
        Abstract method to get open orders.

        Parameters
        ----------
        symbol : str
            The trading symbol.

        Returns
        -------
        Dict
            The open orders data from the exchange.
        """
        pass

    @abstractmethod
    async def get_position(self, symbol: str) -> Dict:
        """
        Abstract method to get current position data.

        Parameters
        ----------
        symbol : str
            The trading symbol.

        Returns
        -------
        Dict
            The position data from the exchange.
        """
        pass

    async def shutdown(self) -> None:
        """
        Initiates the shutdown sequence for the exchange.

        This method performs the following tasks:

        1. Cancels all open orders for the specified symbol by sending multiple asynchronous cancellation requests.
        2. Creates a new market order to close the current position, if any, for the specified symbol.

        The method handles exceptions as follows:

        - If a KeyError is raised, it logs an informational message indicating that no position was found and skips the order creation step.
        - If any other exception is raised, it logs an error message with the exception details and re-raises the exception.

        The method ensures that a final log message is written to indicate the completion of the shutdown sequence.

        Raises
        ------
        Exception
            If an unexpected error occurs during the shutdown process.
        """
        try:
            tasks = []

            for attempt in range(3):
                await self.logging.debug(f"Cancel all, attempt {attempt}")
                tasks.append(self.cancel_all_orders(self.symbol))

            delta_neutralizer_orderid = self.orderid.generate_order_id()

            for attempt in range(3):
                await self.logging.debug(f"Delta neutralizer, attempt {attempt}")
                tasks.append(
                    self.create_order(
                        symbol=self.symbol,
                        side=(
                            Side.BUY if self.data["position"].size < 0.0 else Side.SELL
                        ),
                        orderType=OrderType.MARKET,
                        timeInForce=TimeInForce.GTC,
                        size=self.data["position"].size,
                        clientOrderId=delta_neutralizer_orderid,
                    )
                )

            await asyncio.gather(*tasks)

        except KeyError:
            await self.logging.info("No position found, skipping...")

        except Exception as e:
            await self.logging.error(f"Shutdown sequence: {e}")
            raise e

        finally:
            await self.logging.info(f"Exchange shutdown sequence complete.")
            await self.client.shutdown()
