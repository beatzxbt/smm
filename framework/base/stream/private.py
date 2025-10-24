import asyncio
from enum import StrEnum
from abc import ABC, abstractmethod
from collections.abc import Iterable
from typing import final

from framework.base.trading.exchange import Secret
from framework.base.tools.time import time_ms
from framework.base.tools.logger import Logger
from framework.base.common import Instrument, Venue
from framework.base.stream.structs import DataMsg, HeartbeatMsg, PrivateDataMsg

class PrivateDataStreamType(StrEnum):
    ORDER = "Order"
    POSITION = "Position"
    EXECUTION = "Execution"
    ACCOUNT = "Account"

ALL_PRIVATE_DATA_STREAM_TYPES: set[PrivateDataStreamType] = {
    PrivateDataStreamType.ORDER,
    PrivateDataStreamType.POSITION,
    PrivateDataStreamType.EXECUTION,
    PrivateDataStreamType.ACCOUNT,
}

class PrivateDataStream(ABC):
    """Base class for handling private data streams."""

    def __init__(
        self,
        venue: Venue,
        key: Secret,
        secret: Secret,
        logger: Logger,
        consumer_queues: list[asyncio.Queue[DataMsg]],
    ):
        """Initialize the base private data handler."""
        self.venue = venue
        self.key = key
        self.secret = secret
        self.logger = logger
        self.consumer_queues = consumer_queues

        self.is_running = False

    @final
    def broadcast(self, msg: DataMsg):
        """Broadcast a message to all consumer queues."""
        for queue in self.consumer_queues:
            queue.put_nowait(msg)

    @final
    async def broadcast_heartbeat(self, interval_s: int = 60):
        """Broadcast a health check message to all consumer queues."""
        interval_ms = interval_s * 1000

        while True:
            if not self.is_running:
                await asyncio.sleep(1)
                continue

            await asyncio.sleep(interval_s)
            time_now_ms = time_ms()
            heartbeat_msg = HeartbeatMsg(
                venue=self.venue,
                time_now_ms=time_now_ms,
                time_next_check_ms=time_now_ms + interval_ms,
            )
            self.broadcast(heartbeat_msg)
            self.logger.debug(
                f"Broadcasting heartbeat from {self.venue.name}PrivateDataStream;"
            )

    @abstractmethod
    def instrument_to_symbol(self, instrument: Instrument) -> str:
        """Convert an instrument to a symbol."""
        pass

    @abstractmethod
    async def stream_order(self, instruments: list[Instrument]):
        """Process order data. The processed data must be distributed via self.broadcast(msg)."""
        pass

    @abstractmethod
    async def stream_position(self, instruments: list[Instrument]):
        """Process position data. The processed data must be distributed via self.broadcast(msg)."""
        pass

    @abstractmethod
    async def stream_execution(self, instruments: list[Instrument]):
        """Process execution data. The processed data must be distributed via self.broadcast(msg)."""
        pass

    @abstractmethod
    async def stream_account(self):
        """Process account data. The processed data must be distributed via self.broadcast(msg)."""
        pass

    @abstractmethod
    async def start(self, instruments: list[Instrument], stream_types: set[PrivateDataStreamType]):
        """Open and stream the required instruments and data types."""
        pass
