"""
Base stream handlers for market data streams.

Usage: subclass BaseStreamHandler to implement exchange-specific decoding.
Components: subscription tracking, connection lifecycle, and message broadcast helpers.
"""

from __future__ import annotations

import asyncio
from abc import ABC, abstractmethod
from typing import ClassVar, final

from framework.base.common import Instrument, InstrumentCollection, Venue
from framework.base.stream.connection import WebSocketConnection
from framework.base.stream.models import (
    MarketDataStreamType,
    Msg,
    StreamType,
    ALL_PRIVATE_DATA_STREAM_TYPES,
)

from mm_toolbox.logging.standard import Logger


class BaseStreamHandler(ABC):
    """Abstract base for market data stream handlers.

    Args:
        connection: WebSocket connection used by this handler.
        instrument_collection: Shared instrument collection from manager.
        venue: Venue this handler streams from.
        logger: Logger for diagnostics.
        consumer_queues: Queues to broadcast messages to.
    """

    stream_types: ClassVar[set[StreamType]]

    def __init__(
        self,
        venue: Venue,
        logger: Logger,
        connection: WebSocketConnection,
        instrument_collection: InstrumentCollection,
        consumer_queues: list[asyncio.Queue[Msg]],
    ) -> None:
        """Initialize the base stream handler.

        Args:
            venue: Venue this handler streams from.
            logger: Logger for diagnostics.
            connection: WebSocket connection used by this handler.
            instrument_collection: Shared, 'complete', instrument collection from manager.
            consumer_queues: Queues to broadcast messages to.
        """
        self._connection = connection
        self._instrument_collection = InstrumentCollection(
            instruments=instrument_collection.instruments
        )
        self._venue = venue
        self._logger = logger
        self._consumer_queues = consumer_queues

        self._is_running = False
        self._message_task: asyncio.Task[None] | None = None
        self._subscribed_instruments: set[Instrument] = set()
        self._subscribed_stream_types: set[StreamType] = set()

        self._connection.add_reconnect_callback(self._handle_reconnect)

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
    async def decode_and_broadcast(self, raw_msg: bytes) -> None:
        """Decode a raw message and broadcast it.

        Args:
            raw_msg: Raw websocket payload bytes.
        """
        ...

    async def start(self) -> None:
        """Start the handler and connection."""
        if self._is_running:
            return
        self._is_running = True
        await self._connection.connect()
        await self.authenticate()
        self._message_task = asyncio.create_task(self._message_loop())

    async def stop(self) -> None:
        """Stop the handler and close the connection."""
        if not self._is_running:
            return
        self._is_running = False
        if self._message_task is not None:
            self._message_task.cancel()
            await asyncio.gather(self._message_task, return_exceptions=True)
            self._message_task = None
        await self._connection.disconnect()
        self._subscribed_instruments.clear()
        self._subscribed_stream_types.clear()

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
        if not instruments:
            return
        self._subscribed_instruments.update(instruments)
        if stream_types:
            self._subscribed_stream_types.update(stream_types)
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
        if not instruments:
            return
        for instrument in instruments:
            self._subscribed_instruments.discard(instrument)
        if stream_types:
            for st in stream_types:
                self._subscribed_stream_types.discard(st)
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
        """Broadcast a message to all consumer queues.

        Args:
            msg: Message to broadcast.
        """
        for queue in self._consumer_queues:
            queue.put_nowait(msg)

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
            async for raw_msg in self._connection:
                try:
                    await self.decode_and_broadcast(raw_msg)
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
        if self._subscribed_instruments or self._subscribed_stream_types:
            await self.subscribe(
                list(self._subscribed_instruments),
                self._subscribed_stream_types or None,
            )


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
