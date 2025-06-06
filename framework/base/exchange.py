import msgspec
import aiohttp
from abc import ABC, abstractmethod
from typing import Dict, Optional, Union, Literal, Tuple, List

from framework.tools.time import time_ns
from framework.tools.logger import Logger

from framework.base.internal_structs import (
    Symbol, 
    OrderMsg, 
    OrderbookMsg, 
    TickerMsg, 
    TradeMsg, 
    PositionMsg, 
    AccountMsg, 
    ExecutionMsg, 
    OrderTimeInForce
)
from framework.base.client import BaseRestTradeClient, BaseWsTradeClient


class BaseExchange(ABC):
    def __init__(
        self,
        logger: Logger,
        rest_client: Optional[BaseRestTradeClient]=None,
        ws_client: Optional[BaseWsTradeClient]=None,
        max_cloid_length: int = 36,
    ) -> None:
        """Initializes the Exchange class with the necessary components.

        Args:
            logger: Logger instance for logging.
            rest_client: The REST client instance to interact with the exchange.
            ws_client: The WebSocket client instance to interact with the exchange.
            max_cloid_length: Maximum length for client order IDs.
        """
        self._logger = logger
        self._rest_client = rest_client
        self._ws_client = ws_client
        self._max_cloid_length = max_cloid_length

        self._unauthenticated_session = None

        self._json_encoder = msgspec.json.Encoder()
        self._json_decoder = msgspec.json.Decoder()
    
    @property
    def unauth_session(self) -> aiohttp.ClientSession:
        """Gets or creates an unauthenticated HTTP session.

        Returns:
            An aiohttp ClientSession instance.
        """
        if self._unauthenticated_session is None:
            self._unauthenticated_session = aiohttp.ClientSession()
        return self._unauthenticated_session
    
    def is_running(self, rest_only: bool = False, ws_only: bool = False) -> bool:
        """Checks if the exchange clients are running.

        Args:
            rest_only: If True, only checks if the REST client is running.
            ws_only: If True, only checks if the WebSocket client is running.

        Returns:
            True if the specified clients are running, False otherwise.
        """
        if ws_only:
            return self._ws_client is not None and self._ws_client.is_running
        elif rest_only:
            return self._rest_client is not None and self._rest_client.is_running
        else:
            return self._rest_client is not None and self._rest_client.is_running and self._ws_client is not None and self._ws_client.is_running

    def ensure_running(self, rest_only: bool = False, ws_only: bool = False) -> None:
        """Ensures that the exchange clients are running.

        Args:
            rest_only: If True, only checks if the REST client is running.
            ws_only: If True, only checks if the WebSocket client is running.

        Raises:
            RuntimeError: If the specified clients are not running.
        """
        if not self.is_running(rest_only, ws_only):
            raise RuntimeError("Exchange clients are not running.")

    async def connect_ws_client(self) -> None:
        """Connects the WebSocket client if it exists.

        Raises:
            Exception: If connection fails, the error is logged.
        """
        try:
            if self._ws_client is not None:
                await self._ws_client.connect()
        except Exception as e:
            self._logger.error(f"Failed to connect to trade WS; error: {e}")

    async def close_all_clients(self) -> None:
        """Closes all client connections."""
        if self._ws_client is not None:
            await self._ws_client.close()
        if self._rest_client is not None:
            await self._rest_client.close()
        if self._unauthenticated_session is not None:
            await self._unauthenticated_session.close()
            
    def generate_cloid(
        self, start: Optional[str]="", end: Optional[str]=""
    ) -> str:
        """Generates a client order ID with optional starting and ending substrings.

        The generated order ID consists of the starting substring, a timestamp
        in nanoseconds (padded with zeros if needed), and the ending substring.

        Args:
            start: The starting substring of the order ID.
            end: The ending substring of the order ID.

        Returns:
            The generated client order ID.

        Raises:
            ValueError: If the combined length of start and end exceeds max_cloid_length.
        """
        substring_length = len(start) + len(end)
        
        if substring_length < self._max_cloid_length:
            time_ns_str = str(time_ns())
            available_length = self._max_cloid_length - substring_length
            
            # Pad with zeros if the time_ns string is shorter than available space,
            # or truncate if longer (unlikely but possible if max_cloid_length < 19).
            if len(time_ns_str) < available_length:
                time_ns_str = time_ns_str.zfill(available_length)
            elif len(time_ns_str) > available_length:
                time_ns_str = time_ns_str[:available_length]
                
            return start + time_ns_str + end
        else:
            raise ValueError(
                f"Invalid cloid length; expected <={self._max_cloid_length} but got {substring_length}."
            )

    @abstractmethod
    async def create_order(
        self, 
        symbol: Symbol, 
        is_maker: bool, 
        sz: float, 
        is_buy: bool, 
        px: Optional[float]=None, 
        tif: Optional[OrderTimeInForce]=OrderTimeInForce.GTC, 
        reduce_only: Optional[bool]=False, 
        cloid: Optional[str]=None
    ) -> Optional[Dict]:
        """Creates an order on the exchange.

        Args:
            symbol: The trading symbol.
            is_maker: If True, creates a maker order.
            sz: Size of the order.
            is_buy: If True, creates a buy order; otherwise, a sell order.
            px: Price of the order. Required for limit orders.
            tif: Time-in-force for the order.
            reduce_only: If True, the order will only reduce position size.
            cloid: Client order ID. If None, one will be generated.

        Returns:
            The exchange response or None if the request failed.
        """
        pass

    @abstractmethod
    async def amend_order(
        self, 
        symbol: Symbol,
        sz: Optional[float]=None,
        px: Optional[float]=None,
        oid: Optional[str]=None,
        cloid: Optional[str]=None
    ) -> Optional[Dict]:
        """Amends an existing order on the exchange.

        Args:
            symbol: The trading symbol.
            sz: New size for the order.
            px: New price for the order.
            oid: Exchange order ID.
            cloid: Client order ID.

        Returns:
            The exchange response or None if the request failed.
        """
        pass

    @abstractmethod
    async def cancel_order(
        self, 
        symbol: Symbol, 
        oid: Optional[str]=None, 
        cloid: Optional[str]=None
    ) -> Optional[Dict]:
        """Cancels an order on the exchange.

        Args:
            symbol: The trading symbol.
            oid: Exchange order ID.
            cloid: Client order ID.

        Returns:
            The exchange response or None if the request failed.
        """
        pass

    @abstractmethod
    async def cancel_all_orders(self, symbol: Symbol) -> Optional[Dict]:
        """Cancels all open orders for a symbol.

        Args:
            symbol: The trading symbol.

        Returns:
            The exchange response or None if the request failed.
        """
        pass

    @abstractmethod
    async def get_trades(self, symbol: Symbol) -> Optional[TradeMsg]:
        """Gets recent trades for a symbol. The trades are returned in 
        re-chronological order, so the first trade in the list is the 
        oldest and the last trade in the list is the newest.

        Args:
            symbol: The trading symbol.

        Returns:
            A TradeMsg containing recent trades or None if the request failed.
        """
        pass

    @abstractmethod
    async def get_orderbook(self, symbol: Symbol) -> Optional[OrderbookMsg]:
        """Gets an orderbook snapshot for a symbol. The orderbook is returned 
        with the levels sorted in ascending order of price. Bids will have the 
        lowest price at the front of its list and asks will have the highest 
        price at the end of its list.

        Args:
            symbol: The trading symbol.

        Returns:
            An OrderbookMsg containing the orderbook data or None if the request failed.
        """
        pass

    @abstractmethod
    async def get_ticker(self, symbol: Symbol) -> Optional[TickerMsg]:
        """Gets ticker data for a symbol.

        Args:
            symbol: The trading symbol.

        Returns:
            A TickerMsg containing the ticker data or None if the request failed.
        """
        pass

    @abstractmethod
    async def get_orders(self, symbol: Symbol) -> Optional[List[OrderMsg]]:
        """Gets open orders for a symbol.

        Args:
            symbol: The trading symbol.

        Returns:
            A List[OrderMsg] containing open orders or None if the request failed.
        """
        pass

    @abstractmethod
    async def get_position(self, symbol: Symbol) -> Optional[PositionMsg]:
        """Gets current position data for a symbol.

        Args:
            symbol: The trading symbol.

        Returns:
            A PositionMsg containing position data or None if the request failed.
        """
        pass
    
    @abstractmethod
    async def get_executions(self, symbol: Symbol) -> Optional[List[ExecutionMsg]]:
        """Gets executions for a symbol.

        Args:
            symbol: The trading symbol.

        Returns:
            A List[ExecutionMsg] containing executions or None if the request failed.
        """
        pass

    @abstractmethod
    async def get_account(self) -> Optional[AccountMsg]:
        """Gets account data from the exchange.

        Returns:
            An AccountMsg containing account data or None if the request failed.
        """
        pass

    @abstractmethod
    async def get_precision(self, symbol: Symbol) -> Optional[Tuple[float, float]]:
        """Gets the precision for a symbol.

        Returns:
            A tuple containing the tick size and lot size for the symbol.
        """
        pass
