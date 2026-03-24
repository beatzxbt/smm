"""Exchange base interface and utilities.

Usage: subclass Exchange for venue-specific implementations.
Components: connection helpers, instrument caching, and abstract API.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Optional, final

import aiohttp

from mm_toolbox.logging.standard import Logger
from mm_toolbox.time import time_ns

from framework.base.common import Instrument, InstrumentCollection, Symbol, Venue
from framework.base.trading.client import HttpClient, WsClient
from framework.base.trading.models import (
    AccountResponse,
    AmendOrder,
    AmendOrderResponse,
    CancelAllOrders,
    CancelAllOrdersResponse,
    CancelOrder,
    CancelOrderResponse,
    ClientResponse,
    ClientResponseFailure,
    ClientResponseMeta,
    ClientResponseSuccess,
    ClientResponseTransport,
    CreateOrder,
    CreateOrderResponse,
    ExecutionResponse,
    InstrumentInfoResponse,
    OrderbookResponse,
    OrdersResponse,
    PositionResponse,
    TickerResponse,
    TradesResponse,
    is_success,
)


class Exchange(ABC):
    """Base exchange interface with HTTP/WS clients and instrument helpers.

    Attributes:
        venue (Venue): Venue identifier for the exchange.
        logger (Logger): Logger for status and error output.
        load_secrets (bool): Whether secrets are loaded for authenticated calls.
        http_client (HttpClient): HTTP client implementation.
        ws_client (WsClient): WebSocket client implementation.
        max_cloid_length (int): Maximum length for generated client order ids.
    """

    def __init__(
        self,
        venue: Venue,
        logger: Logger,
        load_secrets: bool,
        http_client: HttpClient,
        ws_client: WsClient,
        max_cloid_length: int = 36,
    ) -> None:
        """Initialize the exchange with its runtime dependencies.

        Args:
            venue (Venue): Venue identifier for the exchange.
            logger (Logger): Logger instance for status and error output.
            load_secrets (bool): Whether secrets are loaded for auth calls.
            http_client (HttpClient): HTTP client implementation.
            ws_client (WsClient): WebSocket client implementation.
            max_cloid_length (int): Maximum length for generated order ids.
        """
        self.venue = venue
        self.logger = logger
        self.load_secrets = load_secrets
        self.http_client = http_client
        self.ws_client = ws_client
        self.max_cloid_length = max_cloid_length

        self._unauthenticated_session: aiohttp.ClientSession | None = None
        self._instrument_collection: InstrumentCollection | None = None

    @property
    def unauth_session(self) -> aiohttp.ClientSession:
        """Get or create the unauthenticated HTTP session.

        Returns:
            aiohttp.ClientSession: Lazily created unauthenticated session.
        """
        if self._unauthenticated_session is None:
            self._unauthenticated_session = aiohttp.ClientSession()
        return self._unauthenticated_session

    @final
    def ensure_secrets_loaded(self) -> None:
        """Ensure required secrets are loaded for authenticated calls.

        Raises:
            RuntimeError: If secrets were not loaded.
        """
        if not self.load_secrets:
            raise RuntimeError(
                f"Required secrets for {self.__class__.__name__} are not loaded;"
            )

    @final
    def ensure_running(self, http_only: bool = False, ws_only: bool = False) -> bool:
        """Check whether exchange clients are running.

        Args:
            http_only (bool): Whether to require only the HTTP client.
            ws_only (bool): Whether to require only the WebSocket client.

        Returns:
            bool: True if the requested clients are running.

        Raises:
            RuntimeError: If the requested clients are not running.
        """
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
    def make_meta(
        self,
        *,
        operation: str,
        started_ns: int,
        finished_ns: int | None = None,
        request_id: str | None = None,
        status_code: int | None = None,
        attempt: int = 1,
        timeout: bool = False,
    ) -> ClientResponseMeta:
        """Create metadata for an exchange method response.

        Args:
            operation: Fully-qualified exchange operation name.
            started_ns: Start timestamp in nanoseconds.
            finished_ns: Optional finish timestamp in nanoseconds.
            request_id: Optional request identifier.
            status_code: Optional status code associated with the operation.
            attempt: One-based retry attempt counter.
            timeout: Whether the response was produced by timeout.

        Returns:
            ClientResponseMeta: Metadata envelope for the exchange response.
        """
        end_ns = started_ns if finished_ns is None else finished_ns
        return ClientResponseMeta(
            started_ns=started_ns,
            finished_ns=end_ns,
            venue=self.venue,
            transport=ClientResponseTransport.INTERNAL,
            operation=operation,
            request_id=request_id,
            status_code=status_code,
            attempt=attempt,
            timeout=timeout,
        )

    @final
    def make_success[T](
        self, *, data: T, meta: ClientResponseMeta
    ) -> ClientResponse[T]:
        """Create a successful exchange response.

        Args:
            data: Response payload.
            meta: Response metadata envelope.

        Returns:
            ClientResponse[T]: Successful response variant.
        """
        return ClientResponseSuccess(data=data, meta=meta)

    @final
    def make_failure[T](
        self,
        *,
        meta: ClientResponseMeta,
        err_no: int = 1,
        err_msg: str = "",
    ) -> ClientResponse[T]:
        """Create a failed exchange response.

        Args:
            meta: Response metadata envelope.
            err_no: Numeric error code.
            err_msg: Human-readable error message.

        Returns:
            ClientResponse[T]: Failed response variant.
        """
        normalized_err_no = err_no
        normalized_err_msg = err_msg
        if normalized_err_no == 0 and normalized_err_msg == "":
            normalized_err_no = 1
            normalized_err_msg = "Unknown error"
        return ClientResponseFailure(
            meta=meta,
            err_no=normalized_err_no,
            err_msg=normalized_err_msg,
        )

    @final
    async def connect_ws_client(self) -> None:
        """Connect the WebSocket client if it exists."""
        try:
            if self.ws_client is not None:
                await self.ws_client.connect()
        except Exception as e:
            self.logger.error(
                f"Failed to connect {self.__class__.__name__}'s WebSocket Client; error: {e}"
            )
            raise e

    @final
    async def get_instrument_collection_cached(
        self, refresh: bool = False
    ) -> InstrumentCollection:
        """Get and cache the exchange instrument collection.

        Args:
            refresh (bool): Whether to refresh the cached instrument collection.

        Returns:
            InstrumentCollection: Cached or freshly loaded instrument collection.

        Raises:
            RuntimeError: If the exchange fails to load instruments.
        """
        if self._instrument_collection is None or refresh:
            response = await self.get_instrument_collection()
            if not is_success(response):
                raise RuntimeError(
                    f"Failed to load instruments for {self.venue}; {response.err_msg}"
                )
            self._instrument_collection = response.data
        return self._instrument_collection

    @final
    async def resolve_instrument(self, symbol: Symbol) -> Instrument:
        """Resolve a symbol to a concrete Instrument using the cached collection.

        Args:
            symbol (Symbol): Exchange-specific symbol to resolve.

        Returns:
            Instrument: Resolved instrument for the current venue.

        Raises:
            ValueError: If the symbol cannot be resolved for the venue.
        """
        collection = await self.get_instrument_collection_cached()

        lookup = symbol.strip()
        if instrument := collection.get(lookup):
            return instrument

        upper = lookup.upper()
        if instrument := collection.get(upper):
            return instrument

        lower = lookup.lower()
        if instrument := collection.get(lower):
            return instrument

        # Fallback: case-insensitive search
        for inst in collection.instruments:
            if inst.venue == self.venue and inst.symbol.lower() == lookup.lower():
                return inst

        raise ValueError(f"Unknown symbol '{symbol}' for venue '{self.venue}'")

    @final
    async def close_clients(self) -> None:
        """Close all client connections if they exist."""
        if self.ws_client is not None:
            await self.ws_client.close()
        if self.http_client is not None:
            await self.http_client.close()
        if self._unauthenticated_session is not None:
            await self._unauthenticated_session.close()
        self._unauthenticated_session = None

    @final
    def generate_cloid(
        self, start: Optional[str] = None, end: Optional[str] = None
    ) -> str:
        """Generate a client order id with optional prefix and suffix.

        The id is formed as: prefix + time_ns (zero-padded) + suffix.

        Args:
            start (Optional[str]): Prefix for the generated id.
            end (Optional[str]): Suffix for the generated id.

        Returns:
            str: Generated client order id.

        Raises:
            ValueError: If the prefix and suffix exceed the max length.
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
    async def get_instrument_collection(self) -> ClientResponse[InstrumentCollection]:
        """Fetch the instrument collection for the exchange.

        Returns:
            ClientResponse[InstrumentCollection]: Instrument collection response.
        """
        pass

    @abstractmethod
    async def create_order(
        self, create_order: CreateOrder
    ) -> ClientResponse[CreateOrderResponse]:
        """Create an order on the exchange.

        Args:
            create_order (CreateOrder): Create order payload.

        Returns:
            ClientResponse[CreateOrderResponse]: Create order response.
        """
        pass

    @abstractmethod
    async def amend_order(
        self, amend_order: AmendOrder
    ) -> ClientResponse[AmendOrderResponse]:
        """Amend an existing order on the exchange.

        Args:
            amend_order (AmendOrder): Amend order payload.

        Returns:
            ClientResponse[AmendOrderResponse]: Amend order response.
        """
        pass

    @abstractmethod
    async def cancel_order(
        self, cancel_order: CancelOrder
    ) -> ClientResponse[CancelOrderResponse]:
        """Cancel a single order on the exchange.

        Args:
            cancel_order (CancelOrder): Cancel order payload.

        Returns:
            ClientResponse[CancelOrderResponse]: Cancel order response.
        """
        pass

    @abstractmethod
    async def cancel_all_orders(
        self, cancel_all_orders: CancelAllOrders
    ) -> ClientResponse[CancelAllOrdersResponse]:
        """Cancel all open orders for the provided scope.

        Args:
            cancel_all_orders (CancelAllOrders): Cancel-all payload.

        Returns:
            ClientResponse[CancelAllOrdersResponse]: Cancel-all response.
        """
        pass

    @abstractmethod
    async def get_trades(
        self, instruments: list[Instrument]
    ) -> ClientResponse[list[TradesResponse]]:
        """Fetch recent trades for multiple instruments.

        The trades should be returned sorted in ascending order of time.

        Args:
            instruments (list[Instrument]): Instruments to fetch trades for.

        Returns:
            ClientResponse[list[TradesResponse]]: Trade response list.
        """
        pass

    @abstractmethod
    async def get_orderbook(
        self, instruments: list[Instrument]
    ) -> ClientResponse[list[OrderbookResponse]]:
        """Fetch orderbook snapshots for multiple instruments.

        Args:
            instruments (list[Instrument]): Instruments to fetch orderbooks for.

        Returns:
            ClientResponse[list[OrderbookResponse]]: Orderbook response list.
        """
        pass

    @abstractmethod
    async def get_ticker(
        self, instruments: list[Instrument]
    ) -> ClientResponse[list[TickerResponse]]:
        """Fetch ticker data for multiple instruments.

        Args:
            instruments (list[Instrument]): Instruments to fetch tickers for.

        Returns:
            ClientResponse[list[TickerResponse]]: Ticker response list.
        """
        pass

    @abstractmethod
    async def get_instrument_info(
        self, instruments: list[Instrument]
    ) -> ClientResponse[list[InstrumentInfoResponse]]:
        """Fetch instrument metadata for multiple instruments.

        If one wants to get back all instruments, pass in an empty list. Exchanges that support
        this will return all instruments, otherwise it will throw an error.

        Args:
            instruments (list[Instrument]): Instruments to fetch metadata for.

        Returns:
            ClientResponse[list[InstrumentInfoResponse]]: Instrument info response list.
        """
        pass

    @abstractmethod
    async def get_orders(
        self, instruments: list[Instrument]
    ) -> ClientResponse[list[OrdersResponse]]:
        """Fetch open orders for multiple instruments.

        Args:
            instruments (list[Instrument]): Instruments to fetch orders for.

        Returns:
            ClientResponse[list[OrdersResponse]]: Orders response list.
        """
        pass

    @abstractmethod
    async def get_position(
        self, instruments: list[Instrument]
    ) -> ClientResponse[list[PositionResponse]]:
        """Fetch position data for multiple instruments.

        Args:
            instruments (list[Instrument]): Instruments to fetch positions for.

        Returns:
            ClientResponse[list[PositionResponse]]: Position response list.
        """
        pass

    @abstractmethod
    async def get_executions(
        self, instruments: list[Instrument]
    ) -> ClientResponse[list[ExecutionResponse]]:
        """Fetch executions for multiple instruments.

        Args:
            instruments (list[Instrument]): Instruments to fetch executions for.

        Returns:
            ClientResponse[list[ExecutionResponse]]: Executions response list.
        """
        pass

    @abstractmethod
    async def get_account(self) -> ClientResponse[AccountResponse]:
        """Fetch account data for the exchange.

        Returns:
            ClientResponse[AccountResponse]: Account response data.
        """
        pass
