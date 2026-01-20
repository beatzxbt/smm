"""
Abstract base class for data stream handlers.

Provides common functionality for market and private data streams including:
- Instrument collection management with lazy initialization
- Message broadcasting to consumer queues
- Periodic heartbeat broadcasting
"""

from __future__ import annotations

import asyncio
from abc import ABC, abstractmethod
from typing import final

from framework.base.common import Instrument, InstrumentCollection, Venue
from framework.base.stream.models import HeartbeatMsg, Msg, StreamType

from mm_toolbox.time import time_ms
from mm_toolbox.logging.standard import Logger


class DataStream(ABC):
    """Abstract base class for all data stream handlers.

    Provides shared infrastructure for streaming data from exchanges,
    including instrument management, message broadcasting, and heartbeats.

    Args:
        venue: The exchange venue this stream connects to.
        logger: Logger instance for debug and error messages.
        consumer_queues: List of queues to broadcast messages to.
    """

    def __init__(
        self,
        venue: Venue,
        logger: Logger,
        consumer_queues: list[asyncio.Queue[Msg]],
    ) -> None:
        self.venue = venue
        self.logger = logger
        self.consumer_queues = consumer_queues

        self.is_running = False
        self._instruments: list[Instrument] = []
        self._instrument_collection: InstrumentCollection | None = None

    @property
    def instrument_collection(self) -> InstrumentCollection:
        """Lazily creates and populates the instrument collection.

        Returns:
            The populated instrument collection.
        """
        if self._instrument_collection is None:
            self._instrument_collection = InstrumentCollection()
            self.populate_instrument_collection(self._instrument_collection)
        return self._instrument_collection

    @abstractmethod
    def populate_instrument_collection(self, collection: InstrumentCollection) -> None:
        """Populate the instrument collection with viable instruments.

        Args:
            collection: Empty collection to populate with instruments.
        """
        ...

    @final
    def broadcast(self, msg: Msg) -> None:
        """Broadcast a message to all consumer queues.

        Args:
            msg: The message to broadcast.
        """
        for queue in self.consumer_queues:
            queue.put_nowait(msg)

    @final
    async def broadcast_heartbeat(
        self, stream_type: StreamType, interval_s: int = 60
    ) -> None:
        """Broadcast periodic heartbeat messages to all consumer queues.

        Runs continuously while the stream is active, sending heartbeat
        messages at the specified interval.

        Args:
            stream_type: The type of stream this heartbeat is from.
            interval_s: Seconds between heartbeat broadcasts. Defaults to 60.
        """
        interval_ms = interval_s * 1000

        while True:
            if not self.is_running:
                await asyncio.sleep(1)
                continue

            await asyncio.sleep(interval_s)
            time_now_ms = time_ms()
            heartbeat_msg = HeartbeatMsg(
                venue=self.venue,
                stream_type=stream_type,
                time_now_ms=time_now_ms,
                time_next_check_ms=time_now_ms + interval_ms,
            )
            self.broadcast(heartbeat_msg)
            self.logger.debug(f"Broadcasting heartbeat from {self.__class__.__name__};")
