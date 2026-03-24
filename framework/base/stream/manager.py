"""
Stream managers for coordinating market and private websocket handlers.

Usage: instantiate exchange-specific managers via their create() factories.
Components: handler orchestration, subscription tracking, and lifecycle events.
"""

from __future__ import annotations

import asyncio
from abc import ABC, abstractmethod

from framework.base.common import Instrument, InstrumentCollection, Venue
from framework.base.stream.handlers import (
    BBOStreamHandler,
    MarketDataStreamHandlers,
    OrderbookStreamHandler,
    PrivateStreamHandler,
    TickerStreamHandler,
    TradesStreamHandler,
)
from framework.base.stream.models import (
    DataStreamEvent,
    DataStreamEventMsg,
    MarketDataStreamType,
    Msg,
    PrivateDataStreamType,
    StreamType,
)
from framework.base.trading.exchange import Exchange
from mm_toolbox.logging.standard import Logger
from mm_toolbox.ringbuffer import GenericRingBuffer
from mm_toolbox.time import time_ms


class StreamManagerBase(ABC):
    """Shared manager utilities for broadcasting and tracking subscriptions."""

    def __init__(
        self,
        venue: Venue,
        logger: Logger,
        consumer_buffer: GenericRingBuffer,
        instrument_collection: InstrumentCollection,
    ) -> None:
        """Initialize base stream manager state.

        Args:
            venue: Venue for the manager.
            logger: Logger for diagnostics.
            consumer_buffer: Ring buffer to broadcast messages to.
            instrument_collection: Shared instrument collection.
        """
        self._venue = venue
        self._logger = logger
        self._consumer_buffer = consumer_buffer
        self._instrument_collection = instrument_collection
        self._subscriptions: dict[StreamType, set[Instrument]] = {}
        self._heartbeat_task: asyncio.Task[None] | None = None
        self._is_running = False

    @property
    def instrument_collection(self) -> InstrumentCollection:
        """Return the manager's instrument collection.

        Returns:
            InstrumentCollection: Shared instrument collection.
        """
        return self._instrument_collection

    @property
    def is_running(self) -> bool:
        """Return whether the manager is running.

        Returns:
            bool: True if running, False otherwise.
        """
        return self._is_running

    def broadcast(self, msg: Msg) -> None:
        """Broadcast a message to the consumer buffer.

        Args:
            msg: Message to broadcast.
        """
        self._consumer_buffer.insert(msg)

    def _broadcast_event(
        self,
        event: DataStreamEvent,
        changes: dict[StreamType, Instrument],
        time_ms_override: int | None = None,
        time_next_check_ms: int | None = None,
    ) -> None:
        """Broadcast a lifecycle event to consumers.

        Args:
            event: Lifecycle event type.
            changes: Stream type to instrument changes.
            time_ms_override: Override event time in milliseconds.
            time_next_check_ms: Next heartbeat check timestamp in milliseconds.
        """
        state: dict[StreamType, Instrument] = {}
        for stream_type, instruments in self._subscriptions.items():
            if instruments:
                state[stream_type] = min(instruments, key=lambda inst: inst.symbol)
        event_msg = DataStreamEventMsg(
            time_ms=time_ms_override or time_ms(),
            venue=self._venue,
            event=event,
            changes=changes,
            state=state,
            time_next_check_ms=time_next_check_ms,
        )
        self.broadcast(event_msg)

    async def _heartbeat_loop(self, interval_s: int = 60) -> None:
        """Broadcast heartbeat events at a fixed interval.

        Args:
            interval_s: Interval in seconds between heartbeats.
        """
        interval_ms = interval_s * 1000
        while True:
            if not self._is_running:
                await asyncio.sleep(1)
                continue
            await asyncio.sleep(interval_s)
            now_ms = time_ms()
            self._broadcast_event(
                event=DataStreamEvent.HEARTBEAT,
                changes={},
                time_ms_override=now_ms,
                time_next_check_ms=now_ms + interval_ms,
            )

    def _add_subscription(
        self, stream_type: StreamType, instrument: Instrument
    ) -> bool:
        """Register a subscription in the manager state.

        Args:
            stream_type: Stream type to subscribe to.
            instrument: Instrument to subscribe to.

        Returns:
            bool: True if subscription was added, False if it already existed.
        """
        instruments = self._subscriptions.setdefault(stream_type, set())
        if instrument in instruments:
            return False
        instruments.add(instrument)
        return True

    def _remove_subscription(
        self, stream_type: StreamType, instrument: Instrument
    ) -> bool:
        """Remove a subscription from the manager state.

        Args:
            stream_type: Stream type to unsubscribe from.
            instrument: Instrument to unsubscribe.

        Returns:
            bool: True if subscription was removed, False otherwise.
        """
        instruments = self._subscriptions.get(stream_type)
        if not instruments or instrument not in instruments:
            return False
        instruments.remove(instrument)
        if not instruments:
            self._subscriptions.pop(stream_type, None)
        return True

    def _resolve_instruments(self, instruments: list[Instrument]) -> list[Instrument]:
        """Resolve instruments from the provided list or all known instruments.

        Args:
            instruments: Requested instruments, or empty to use all.

        Returns:
            list[Instrument]: Resolved instrument list.
        """
        if instruments:
            return instruments
        return list(self._instrument_collection.instruments)


class MarketStreamManager(StreamManagerBase, ABC):
    """Manager for coordinating market stream handlers."""

    def __init__(
        self,
        venue: Venue,
        logger: Logger,
        consumer_buffer: GenericRingBuffer,
        instrument_collection: InstrumentCollection,
        ticker_handler: TickerStreamHandler,
        bbo_handler: BBOStreamHandler,
        orderbook_handler: OrderbookStreamHandler,
        trades_handler: TradesStreamHandler,
    ) -> None:
        """Initialize the market stream manager.

        Args:
            venue: Venue for the manager.
            logger: Logger for diagnostics.
            consumer_buffer: Ring buffer to broadcast messages to.
            instrument_collection: Shared instrument collection.
            ticker_handler: Ticker stream handler.
            bbo_handler: Top-of-book stream handler.
            orderbook_handler: Orderbook stream handler.
            trades_handler: Trades stream handler.
        """
        super().__init__(venue, logger, consumer_buffer, instrument_collection)
        self._ticker_handler = ticker_handler
        self._bbo_handler = bbo_handler
        self._orderbook_handler = orderbook_handler
        self._trades_handler = trades_handler
        self._handlers: dict[MarketDataStreamType, MarketDataStreamHandlers] = {
            MarketDataStreamType.TICKER: self._ticker_handler,
            MarketDataStreamType.TOP_OF_ORDERBOOK: self._bbo_handler,
            MarketDataStreamType.FULL_ORDERBOOK: self._orderbook_handler,
            MarketDataStreamType.TRADES: self._trades_handler,
        }
        self._active_stream_types: set[MarketDataStreamType] = set()

    @classmethod
    @abstractmethod
    async def create(
        cls,
        exchange: Exchange,
        logger: Logger,
        consumer_buffer: GenericRingBuffer,
    ) -> "MarketStreamManager":
        """Create a manager instance using an exchange client.

        Args:
            exchange: Exchange client for instrument resolution.
            logger: Logger for diagnostics.
            consumer_buffer: Ring buffer to broadcast messages to.

        Returns:
            MarketStreamManager: Initialized manager instance.
        """
        ...

    async def start(self) -> None:
        """Start manager lifecycle tasks.

        This starts heartbeat/event lifecycle tracking but defers individual handler
        startup until the first active subscription for each stream type.
        """
        if self._is_running:
            return
        self._is_running = True
        self._heartbeat_task = asyncio.create_task(self._heartbeat_loop())
        self._broadcast_event(DataStreamEvent.START, {})

    async def stop(self) -> None:
        """Stop manager lifecycle tasks and active handlers."""
        if not self._is_running:
            return
        self._is_running = False
        if self._heartbeat_task is not None:
            self._heartbeat_task.cancel()
            await asyncio.gather(self._heartbeat_task, return_exceptions=True)
            self._heartbeat_task = None
        await asyncio.gather(
            *(
                self._handlers[stream_type].stop()
                for stream_type in self._active_stream_types
            )
        )
        self._active_stream_types.clear()
        self._subscriptions.clear()
        self._broadcast_event(DataStreamEvent.STOP, {})

    async def subscribe(
        self,
        instruments: list[Instrument],
        stream_types: set[MarketDataStreamType],
    ) -> None:
        """Subscribe instruments to market stream types.

        Args:
            instruments: Instruments to subscribe to.
            stream_types: Market data stream types to enable.

        Raises:
            RuntimeError: If the manager is not running.
        """
        if not self._is_running:
            raise RuntimeError(f"{self.__class__.__name__} is not running.")
        resolved = self._resolve_instruments(instruments)
        if not resolved or not stream_types:
            return
        for stream_type in stream_types:
            new_instruments: list[Instrument] = []
            for instrument in resolved:
                if self._add_subscription(stream_type, instrument):
                    new_instruments.append(instrument)
            if not new_instruments:
                continue
            handler = self._handlers[stream_type]
            if stream_type not in self._active_stream_types:
                await handler.start()
                self._active_stream_types.add(stream_type)
            await handler.subscribe(new_instruments)
            for instrument in new_instruments:
                self._broadcast_event(
                    DataStreamEvent.SUBSCRIBE,
                    {stream_type: instrument},
                )

    async def unsubscribe(
        self,
        instruments: list[Instrument],
        stream_types: set[MarketDataStreamType],
    ) -> None:
        """Unsubscribe instruments from market stream types.

        Args:
            instruments: Instruments to unsubscribe from.
            stream_types: Market data stream types to disable.

        Raises:
            RuntimeError: If the manager is not running.
        """
        if not self._is_running:
            raise RuntimeError(f"{self.__class__.__name__} is not running.")
        resolved = self._resolve_instruments(instruments)
        if not resolved or not stream_types:
            return
        for stream_type in stream_types:
            removed_instruments: list[Instrument] = []
            for instrument in resolved:
                if self._remove_subscription(stream_type, instrument):
                    removed_instruments.append(instrument)
            if not removed_instruments:
                continue
            handler = self._handlers[stream_type]
            await handler.unsubscribe(removed_instruments)
            for instrument in removed_instruments:
                self._broadcast_event(
                    DataStreamEvent.UNSUBSCRIBE,
                    {stream_type: instrument},
                )
            if stream_type not in self._subscriptions:
                await handler.stop()
                self._active_stream_types.discard(stream_type)

    def get_subscribed_instruments(
        self, stream_type: MarketDataStreamType
    ) -> set[Instrument]:
        """Return instruments subscribed to a specific stream type.

        Args:
            stream_type: Stream type to query.

        Returns:
            set[Instrument]: Subscribed instruments.
        """
        return set(self._subscriptions.get(stream_type, set()))

    def is_subscribed(
        self, instrument: Instrument, stream_type: MarketDataStreamType
    ) -> bool:
        """Return whether an instrument is subscribed for a stream type.

        Args:
            instrument: Instrument to check.
            stream_type: Stream type to check.

        Returns:
            bool: True if subscribed, False otherwise.
        """
        return instrument in self._subscriptions.get(stream_type, set())


class PrivateStreamManager(StreamManagerBase, ABC):
    """Manager for coordinating private stream handlers.

    This is a thin wrapper around a single PrivateStreamHandler that provides
    subscription tracking and lifecycle events.
    """

    def __init__(
        self,
        venue: Venue,
        logger: Logger,
        consumer_buffer: GenericRingBuffer,
        instrument_collection: InstrumentCollection,
        handler: PrivateStreamHandler,
    ) -> None:
        """Initialize the private stream manager.

        Args:
            venue: Venue for the manager.
            logger: Logger for diagnostics.
            consumer_buffer: Ring buffer to broadcast messages to.
            instrument_collection: Shared instrument collection.
            handler: Unified private stream handler.
        """
        super().__init__(venue, logger, consumer_buffer, instrument_collection)
        self._handler = handler

    @classmethod
    @abstractmethod
    async def create(
        cls,
        exchange: Exchange,
        logger: Logger,
        consumer_buffer: GenericRingBuffer,
    ) -> "PrivateStreamManager":
        """Create a manager instance using an exchange client.

        Args:
            exchange: Exchange client for instrument resolution.
            logger: Logger for diagnostics.
            consumer_buffer: Ring buffer to broadcast messages to.

        Returns:
            PrivateStreamManager: Initialized manager instance.
        """
        ...

    async def start(self) -> None:
        """Start the private stream handler."""
        if self._is_running:
            return
        self._is_running = True
        await self._handler.start()
        self._heartbeat_task = asyncio.create_task(self._heartbeat_loop())
        self._broadcast_event(DataStreamEvent.START, {})

    async def stop(self) -> None:
        """Stop the private stream handler."""
        if not self._is_running:
            return
        self._is_running = False
        if self._heartbeat_task is not None:
            self._heartbeat_task.cancel()
            await asyncio.gather(self._heartbeat_task, return_exceptions=True)
            self._heartbeat_task = None
        await self._handler.stop()
        self._subscriptions.clear()
        self._broadcast_event(DataStreamEvent.STOP, {})

    async def subscribe(
        self,
        instruments: list[Instrument],
        stream_types: set[PrivateDataStreamType],
    ) -> None:
        """Subscribe to private stream types.

        Args:
            instruments: Instruments to associate with the subscription.
            stream_types: Private stream types to enable.
        """
        resolved = self._resolve_instruments(instruments)
        if not stream_types:
            return
        for stream_type in stream_types:
            for instrument in resolved:
                self._add_subscription(stream_type, instrument)
        await self._handler.subscribe(resolved, set(stream_types))
        for stream_type in stream_types:
            for instrument in resolved:
                self._broadcast_event(
                    DataStreamEvent.SUBSCRIBE, {stream_type: instrument}
                )

    async def unsubscribe(
        self,
        instruments: list[Instrument],
        stream_types: set[PrivateDataStreamType],
    ) -> None:
        """Unsubscribe from private stream types.

        Args:
            instruments: Instruments to associate with the unsubscribe.
            stream_types: Private stream types to disable.
        """
        resolved = self._resolve_instruments(instruments)
        if not stream_types:
            return
        for stream_type in stream_types:
            for instrument in resolved:
                self._remove_subscription(stream_type, instrument)
        await self._handler.unsubscribe(resolved, set(stream_types))
        for stream_type in stream_types:
            for instrument in resolved:
                self._broadcast_event(
                    DataStreamEvent.UNSUBSCRIBE, {stream_type: instrument}
                )
