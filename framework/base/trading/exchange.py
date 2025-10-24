from abc import ABC, abstractmethod
from typing import Optional, Self, final

import aiohttp
from msgspec import Struct

from framework.base.common import Instrument, Venue
from framework.base.tools.logger import Logger
from framework.base.tools.time import time_ns
from framework.base.trading.client import HttpClient, WsClient
from framework.base.trading.structs import (
    AccountResponse,
    AmendOrder,
    AmendOrderResponse,
    CancelAllOrders,
    CancelAllOrdersResponse,
    CancelOrder,
    CancelOrderResponse,
    ClientResponse,
    CreateOrder,
    CreateOrderResponse,
    ExecutionResponse,
    InstrumentInfoResponse,
    OrderbookResponse,
    OrdersResponse,
    PositionResponse,
    TickerResponse,
    TradesResponse,
)


class Secret(Struct, frozen=True):
    name: str
    value: str

    @classmethod
    def load(cls, var_name: str) -> Self:
        import os

        import dotenv

        dotenv.load_dotenv()
        if not (var_value := os.environ.get(var_name)):
            raise RuntimeError(f"Failed to load {var_name} from '.env';")
        return cls(name=var_name, value=var_value)
    
    @classmethod
    def empty(cls) -> Self:
        return cls(name="", value="")

    def is_empty(self) -> bool:
        return self.name == "" and self.value == ""


class Exchange(ABC):
    def __init__(
        self,
        venue: Venue,
        logger: Logger,
        load_secrets: bool,
        http_client: HttpClient,
        ws_client: WsClient,
        max_cloid_length: int = 36,
    ) -> None:
        """Initializes the Exchange class with the necessary components."""
        self.venue = venue
        self.logger = logger
        self.load_secrets = load_secrets
        self.http_client = http_client
        self.ws_client = ws_client
        self.max_cloid_length = max_cloid_length

        self._unauthenticated_session: aiohttp.ClientSession | None = None

    @property
    def unauth_session(self) -> aiohttp.ClientSession:
        """Gets or creates an unauthenticated HTTP session."""
        if self._unauthenticated_session is None:
            self._unauthenticated_session = aiohttp.ClientSession()
        return self._unauthenticated_session

    @final
    def ensure_secrets_loaded(self) -> None:
        """Ensures the secrets are loaded."""
        if not self.load_secrets:
            raise RuntimeError(f"Required secrets for {self.__class__.__name__} are not loaded;")

    @final
    def ensure_running(self, http_only: bool = False, ws_only: bool = False) -> bool:
        """Checks if the exchange's clients are running, and raises if not."""
        if ws_only:
            running = self.ws_client is not None and self.ws_client.is_running
        elif http_only:
            running = self.http_client is not None and self.http_client.is_running
        else:
            running = (
                self.http_client is not None
                and self.http_client.is_running
                and self.ws_client is not None
                and self.ws_client.is_running
            )
        if not running:
            raise RuntimeError(f"{self.__class__.__name__} clients are not running")
        return True

    @final
    async def connect_ws_client(self) -> None:
        """Connects the WebSocket client if it exists."""
        try:
            if self.ws_client is not None:
                await self.ws_client.connect()
        except Exception as e:
            self.logger.error(
                f"Failed to connect {self.__class__.__name__}'s WebSocket Client; error: {e}"
            )
            raise e

    @final
    async def close_clients(self) -> None:
        """Closes all client connections, if existing."""
        if self.ws_client is not None:
            await self.ws_client.close()
        if self.http_client is not None:
            await self.http_client.close()
        if self._unauthenticated_session is not None:
            await self._unauthenticated_session.close()
        self._unauthenticated_session = None

    @final
    def generate_cloid(self, start: Optional[str] = None, end: Optional[str] = None) -> str:
        """Generates a client order ID with optional starting and ending substrings.

        The generated order ID consists of the starting substring, a timestamp
        in nanoseconds (padded with zeros if needed), and the ending substring.

        Args:
            start (Optional[str]): The starting substring of the order ID.
            end (Optional[str]): The ending substring of the order ID.

        Returns:
            str: The generated client order ID.

        Raises:
            ValueError: If the combined length of start and end exceeds max_cloid_length.

        """
        start = "" if start is None else start
        end = "" if end is None else end
        
        substr_len = len(start) + len(end)
        time_ns_str = str(time_ns())

        if substr_len < self.max_cloid_length:
            available_length = self.max_cloid_length - substr_len

            # Pad with zeros if the time_ns string is shorter than available space,
            # or truncate if longer (unlikely but possible if max_cloid_length < 19).
            if len(time_ns_str) < available_length:
                time_ns_str = time_ns_str.zfill(available_length)
            elif len(time_ns_str) > available_length:
                time_ns_str = time_ns_str[:available_length]

            return start + time_ns_str + end
        else:
            raise ValueError(
                f"Invalid cloid length; expected <={self.max_cloid_length} but got {substr_len}"
            )

    @abstractmethod
    def instrument_to_symbol(self, instrument: Instrument) -> str:
        """Converts an instrument to a symbol."""
        pass

    @abstractmethod
    async def create_order(
        self, create_order: CreateOrder
    ) -> ClientResponse[CreateOrderResponse]:
        """Creates an order on the exchange."""
        pass

    @abstractmethod
    async def amend_order(
        self, amend_order: AmendOrder
    ) -> ClientResponse[AmendOrderResponse]:
        """Amends an existing order on the exchange."""
        pass

    @abstractmethod
    async def cancel_order(
        self, cancel_order: CancelOrder
    ) -> ClientResponse[CancelOrderResponse]:
        """Cancels an order on the exchange."""
        pass

    @abstractmethod
    async def cancel_all_orders(
        self, cancel_all_orders: CancelAllOrders
    ) -> ClientResponse[CancelAllOrdersResponse]:
        """Cancels all open orders for a symbol."""
        pass

    @abstractmethod
    async def get_trades(
        self, instruments: list[Instrument]
    ) -> ClientResponse[list[TradesResponse]]:
        """Gets recent trades for some instruments.

        The trades are returned sorted in ascending order of time.
        """
        pass

    @abstractmethod
    async def get_orderbook(
        self, instruments: list[Instrument]
    ) -> ClientResponse[list[OrderbookResponse]]:
        """Gets orderbook snapshots for multiple symbols."""
        pass

    @abstractmethod
    async def get_ticker(
        self, instruments: list[Instrument]
    ) -> ClientResponse[list[TickerResponse]]:
        """Gets ticker data for multiple symbols."""
        pass

    @abstractmethod
    async def get_instrument_info(
        self, instruments: list[Instrument]
    ) -> ClientResponse[list[InstrumentInfoResponse]]:
        """Gets instrument information for multiple symbols.

        If one wants to get back all instruments, pass in an empty list. Exchanges that support
        this will return all instruments, otherwise it will throw an error.
        """
        pass

    @abstractmethod
    async def get_orders(
        self, instruments: list[Instrument]
    ) -> ClientResponse[list[OrdersResponse]]:
        """Gets open orders for multiple symbols."""
        pass

    @abstractmethod
    async def get_position(
        self, instruments: list[Instrument]
    ) -> ClientResponse[list[PositionResponse]]:
        """Gets current position data for multiple symbols."""
        pass

    @abstractmethod
    async def get_executions(
        self, instruments: list[Instrument]
    ) -> ClientResponse[list[ExecutionResponse]]:
        """Gets executions for multiple symbols."""
        pass

    @abstractmethod
    async def get_account(self) -> ClientResponse[AccountResponse]:
        """Gets account data for all symbols."""
        pass
