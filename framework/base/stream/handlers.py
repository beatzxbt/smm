"""
Base stream handlers for market data streams.

Usage: subclass BaseStreamHandler to implement exchange-specific decoding.
Components: subscription tracking, connection lifecycle, and message broadcast helpers.
"""

from __future__ import annotations

import asyncio
from abc import ABC, abstractmethod
from enum import StrEnum
from typing import Callable, ClassVar, TypeVar, final

from framework.base.common import Instrument, InstrumentCollection, Venue
from framework.base.stream.connection import WebSocketConnection
from framework.base.stream.models import (
    MarketDataStreamType,
    Msg,
    StreamType,
    ALL_PRIVATE_DATA_STREAM_TYPES,
)
from framework.base.stream.shared import StreamSharedContext

from mm_toolbox.logging.standard import Logger
from mm_toolbox.ringbuffer import GenericRingBuffer

TShared = TypeVar("TShared")


class SubscriptionTransport(StrEnum):
    """Subscription transport modes supported by stream handlers.

    Attributes:
        PAYLOAD: Subscriptions are managed by websocket subscribe/unsubscribe payloads.
        URL_QUERY: Subscriptions are encoded in the websocket URL/query string.
    """

    PAYLOAD = "payload"
    URL_QUERY = "url_query"


class BaseStreamHandler(ABC):
    """Abstract base for market data stream handlers.

    Args:
        connection: WebSocket connection used by this handler.
        instrument_collection: Shared instrument collection from manager.
        venue: Venue this handler streams from.
        logger: Logger for diagnostics.
        consumer_buffer: Ring buffer to broadcast messages to.
    """

    stream_types: ClassVar[set[StreamType]]
    subscription_transport: ClassVar[SubscriptionTransport] = (
        SubscriptionTransport.PAYLOAD
    )
    shared_slots: ClassVar[dict[str, Callable[[], object]]] = {}

    def __init__(
        self,
        venue: Venue,
        logger: Logger,
        connection: WebSocketConnection,
        instrument_collection: InstrumentCollection,
        consumer_buffer: GenericRingBuffer,
        shared_context: StreamSharedContext | None = None,
    ) -> None:
        """Initialize the base stream handler.

        Args:
            venue: Venue this handler streams from.
            logger: Logger for diagnostics.
            connection: WebSocket connection used by this handler.
            instrument_collection: Shared, 'complete', instrument collection from manager.
            consumer_buffer: Ring buffer to broadcast messages to.
            shared_context: Optional shared state container scoped to a manager.
        """
        self._connection = connection
        self._instrument_collection = InstrumentCollection(
            instruments=instrument_collection.instruments
        )
        self._venue = venue
        self._logger = logger
        self._consumer_buffer = consumer_buffer

        self._is_running = False
        self._message_task: asyncio.Task[None] | None = None
        self._subscribed_instruments: set[Instrument] = set()
        self._subscribed_stream_types: set[StreamType] = set()
        self._active_subscription_url: str | None = None
        self._shared_context = (
            StreamSharedContext() if shared_context is None else shared_context
        )
        for key, factory in self.shared_slots.items():
            self._shared_context.get_or_create(key, factory)

        self._connection.add_reconnect_callback(self._handle_reconnect)

    @final
    def get_shared(self, key: str, factory: Callable[[], TShared]) -> TShared:
        """Return a manager-scoped shared object.

        Args:
            key: Shared object key.
            factory: Zero-argument factory for initializing missing values.

        Returns:
            TShared: Shared object stored under the provided key.
        """
        return self._shared_context.get_or_create(key, factory)

    @abstractmethod
    def build_authentication_payload(self) -> bytes:
        """Build the websocket authentication payload.

        Returns:
            Serialized websocket payload bytes.
        """
        ...

    @abstractmethod
    def build_subscribe_payload(
        self,
        instruments: list[Instrument],
        stream_types: set[StreamType] | None = None,
    ) -> bytes:
        """Build the websocket subscribe payload.

        Args:
            instruments: Instruments to subscribe to.
            stream_types: Optional stream types to subscribe to (for private handlers).

        Returns:
            Serialized websocket payload bytes.
        """
        ...

    @abstractmethod
    def build_unsubscribe_payload(
        self,
        instruments: list[Instrument],
        stream_types: set[StreamType] | None = None,
    ) -> bytes:
        """Build the websocket unsubscribe payload.

        Args:
            instruments: Instruments to unsubscribe from.
            stream_types: Optional stream types to unsubscribe from (for private handlers).

        Returns:
            Serialized websocket payload bytes.
        """
        ...

    @abstractmethod
    async def decode_and_broadcast(
        self,
        recv_time_ns: int,
        raw_msg: bytes,
    ) -> None:
        """Decode a raw message and broadcast it.

        Args:
            recv_time_ns: Receive timestamp captured when the websocket payload
                arrived.
            raw_msg: Raw websocket payload bytes.
        """
        ...

    def build_subscription_url(
        self,
        instruments: list[Instrument],
        stream_types: set[StreamType] | None = None,
    ) -> str | None:
        """Build the websocket URL for URL-based subscriptions.

        Handlers using `SubscriptionTransport.URL_QUERY` should override this method
        to map the current desired subscription state into a concrete websocket URL.

        Args:
            instruments: Instruments currently subscribed for this handler.
            stream_types: Optional stream types currently subscribed.

        Returns:
            str | None: URL to connect to, or None when no active subscription exists.
        """
        if instruments or stream_types:
            raise NotImplementedError(
                f"{self.__class__.__name__}.build_subscription_url must be "
                "overridden when using URL query subscriptions."
            )
        return None

    async def start(self) -> None:
        """Start the handler and connection."""
        if self._is_running:
            return
        self._is_running = True
        if self._uses_url_query_transport():
            await self._sync_url_query_subscription()
            return
        await self._start_connection_and_message_loop()

    async def stop(self) -> None:
        """Stop the handler and close the connection."""
        if not self._is_running:
            return
        self._is_running = False
        await self._cancel_message_task()
        await self._connection.disconnect()
        self._subscribed_instruments.clear()
        self._subscribed_stream_types.clear()
        self._active_subscription_url = None

    async def authenticate(self) -> None:
        """Authenticate with the websocket connection.

        Raises:
            RuntimeError: If the handler is not running.
        """
        if not self._is_running:
            raise RuntimeError(f"{self.__class__.__name__} is not running.")
        payload = self.build_authentication_payload()
        if payload:
            await self._connection.send(payload)

    async def subscribe(
        self,
        instruments: list[Instrument],
        stream_types: set[StreamType] | None = None,
    ) -> None:
        """Subscribe to instruments for this stream.

        Args:
            instruments: Instruments to subscribe to.
            stream_types: Optional stream types to subscribe to (for private handlers).
        """
        if not self._is_running:
            raise RuntimeError(f"{self.__class__.__name__} is not running.")
        if not instruments and not stream_types:
            return
        self._subscribed_instruments.update(instruments)
        if stream_types:
            self._subscribed_stream_types.update(stream_types)
        if self._uses_url_query_transport():
            await self._sync_url_query_subscription()
            return
        payload = self.build_subscribe_payload(instruments, stream_types)
        if payload:
            await self._connection.send(payload)

    async def unsubscribe(
        self,
        instruments: list[Instrument],
        stream_types: set[StreamType] | None = None,
    ) -> None:
        """Unsubscribe from instruments for this stream.

        Args:
            instruments: Instruments to unsubscribe from.
            stream_types: Optional stream types to unsubscribe from (for private handlers).
        """
        if not self._is_running:
            raise RuntimeError(f"{self.__class__.__name__} is not running.")
        if not instruments and not stream_types:
            return
        for instrument in instruments:
            self._subscribed_instruments.discard(instrument)
        if stream_types:
            for st in stream_types:
                self._subscribed_stream_types.discard(st)
        if self._uses_url_query_transport():
            await self._sync_url_query_subscription()
            return
        payload = self.build_unsubscribe_payload(instruments, stream_types)
        if payload:
            await self._connection.send(payload)

    @property
    def venue(self) -> Venue:
        """Return the handler's venue.

        Returns:
            Venue: Venue this handler streams from.
        """
        return self._venue

    @property
    def instrument_collection(self) -> InstrumentCollection:
        """Return the handler's instrument collection.

        Returns:
            InstrumentCollection: Handler-scoped instrument collection.
        """
        return self._instrument_collection

    @final
    def broadcast(self, msg: Msg) -> None:
        """Broadcast a message to the consumer buffer.

        Args:
            msg: Message to broadcast.
        """
        if self._consumer_buffer.is_full():
            self._logger.debug(
                f"{self.__class__.__name__}.broadcast consumer buffer full; "
                f"overwriting oldest message with {msg.__class__.__name__}"
            )
        self._consumer_buffer.insert(msg)

    @final
    def get_subscribed_instruments(self) -> set[Instrument]:
        """Return the current subscribed instrument set.

        Returns:
            set[Instrument]: Subscribed instruments for this handler.
        """
        return set(self._subscribed_instruments)

    @final
    def get_instrument_collection(self) -> InstrumentCollection:
        """Return the handler's instrument collection.

        Returns:
            InstrumentCollection: Handler-scoped instrument collection.
        """
        return self._instrument_collection

    @final
    async def _message_loop(self) -> None:
        """Consume websocket messages and broadcast decoded payloads."""
        try:
            async for recv_time_ns, raw_msg in self._connection:
                try:
                    await self.decode_and_broadcast(
                        recv_time_ns,
                        raw_msg,
                    )
                except Exception as exc:
                    self._logger.warning(
                        f"{self.__class__.__name__}._message_loop error; {exc}"
                    )
        except asyncio.CancelledError:
            return

    @final
    async def _handle_reconnect(self) -> None:
        """Resubscribe after a reconnect."""
        if not self._is_running:
            return
        await self.authenticate()
        if self._uses_url_query_transport():
            return
        if self._subscribed_instruments or self._subscribed_stream_types:
            await self.subscribe(
                list(self._subscribed_instruments),
                self._subscribed_stream_types or None,
            )

    @final
    def _uses_url_query_transport(self) -> bool:
        """Return whether this handler uses URL-query subscriptions.

        Returns:
            bool: True when using URL query subscriptions, otherwise False.
        """
        return self.subscription_transport == SubscriptionTransport.URL_QUERY

    @final
    async def _start_connection_and_message_loop(self) -> None:
        """Connect, authenticate, and ensure a running message loop."""
        await self._connection.connect()
        await self.authenticate()
        if self._message_task is None or self._message_task.done():
            self._message_task = asyncio.create_task(self._message_loop())

    @final
    async def _cancel_message_task(self) -> None:
        """Cancel and clear the background message loop task."""
        if self._message_task is None:
            return
        self._message_task.cancel()
        await asyncio.gather(self._message_task, return_exceptions=True)
        self._message_task = None

    @final
    async def _sync_url_query_subscription(self) -> None:
        """Reconcile URL-based subscriptions with the websocket connection.

        Raises:
            RuntimeError: If URL transport has active subscriptions but no URL is built.
        """
        desired_url = self.build_subscription_url(
            instruments=sorted(
                self._subscribed_instruments, key=lambda instrument: instrument.symbol
            ),
            stream_types=self._subscribed_stream_types or None,
        )
        if desired_url is None:
            if self._subscribed_instruments or self._subscribed_stream_types:
                raise RuntimeError(
                    f"{self.__class__.__name__} uses URL subscriptions but did not "
                    "produce a URL for an active subscription state."
                )
            has_active_connection = (
                self._active_subscription_url is not None
                or self._message_task is not None
            )
            self._active_subscription_url = None
            if has_active_connection:
                await self._cancel_message_task()
                await self._connection.disconnect()
            return

        if (
            desired_url == self._active_subscription_url
            and self._message_task is not None
            and not self._message_task.done()
        ):
            return

        has_active_connection = (
            self._active_subscription_url is not None or self._message_task is not None
        )
        if has_active_connection:
            await self._cancel_message_task()
            await self._connection.disconnect()

        self._connection.set_url(desired_url)
        self._active_subscription_url = desired_url
        await self._start_connection_and_message_loop()


class TickerStreamHandler(BaseStreamHandler, ABC):
    """Base handler for ticker streams."""

    stream_types: ClassVar[set[StreamType]] = {MarketDataStreamType.TICKER}


class BBOStreamHandler(BaseStreamHandler, ABC):
    """Base handler for top-of-book streams."""

    stream_types: ClassVar[set[StreamType]] = {MarketDataStreamType.TOP_OF_ORDERBOOK}


class OrderbookStreamHandler(BaseStreamHandler, ABC):
    """Base handler for full orderbook streams."""

    stream_types: ClassVar[set[StreamType]] = {MarketDataStreamType.FULL_ORDERBOOK}


class TradesStreamHandler(BaseStreamHandler, ABC):
    """Base handler for trade streams."""

    stream_types: ClassVar[set[StreamType]] = {MarketDataStreamType.TRADES}


class PrivateStreamHandler(BaseStreamHandler, ABC):
    """Base handler for private streams."""

    stream_types: ClassVar[set[StreamType]] = set(ALL_PRIVATE_DATA_STREAM_TYPES)


type MarketDataStreamHandlers = (
    TickerStreamHandler
    | BBOStreamHandler
    | OrderbookStreamHandler
    | TradesStreamHandler
)
type PrivateDataStreamHandlers = PrivateStreamHandler
type DataStreamHandlers = MarketDataStreamHandlers | PrivateDataStreamHandlers
