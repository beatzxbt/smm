import copy
import asyncio
from enum import StrEnum
from abc import ABC, abstractmethod
from typing import final

import msgspec

from framework.base.common import Instrument, Venue
from framework.base.stream.structs import DataMsg, HeartbeatMsg
from framework.base.tools.logger import Logger
from framework.base.tools.time import time_ms

class MarketDataStreamType(StrEnum):
    TICKER = "Ticker"
    TRADES = "Trades"
    TOP_OF_ORDERBOOK = "TopOfOrderBook"
    FULL_ORDERBOOK = "FullOrderBook"

ALL_MARKET_DATA_STREAM_TYPES: set[MarketDataStreamType] = {
    MarketDataStreamType.TOP_OF_ORDERBOOK,
    MarketDataStreamType.FULL_ORDERBOOK,
    MarketDataStreamType.TRADES,
    MarketDataStreamType.TICKER,
}

class MarketDataStream(ABC):
    """Base class for market data handling."""

    def __init__(
        self,
        venue: Venue,
        logger: Logger,
        consumer_queues: list[asyncio.Queue[DataMsg]],
    ) -> None:
        self.venue = venue
        self.logger = logger
        self.consumer_queues = consumer_queues

        self.is_running = False

    @final
    def broadcast(self, msg: DataMsg):
        """Broadcast a message to all consumer queues."""
        for queue in self.consumer_queues:
            queue.put_nowait(msg)

    @final
    async def broadcast_heartbeat(self, interval: int = 60):
        """Broadcast a heartbeat message to all consumer queues."""
        while True:
            if not self.is_running:
                await asyncio.sleep(1)
                continue

            await asyncio.sleep(interval)
            time_now_ms = time_ms()
            heartbeat_msg = HeartbeatMsg(
                venue=self.venue,
                time_now_ms=time_now_ms,
                time_next_check_ms=time_now_ms + (interval * 1000),
            )
            self.broadcast(heartbeat_msg)
            self.logger.debug(
                f"Broadcasting heartbeat from {self.venue.name}MarketDataStream;"
            )

    @abstractmethod
    def instrument_to_symbol(self, instrument: Instrument) -> str:
        """Convert an instrument to a symbol."""
        pass

    @abstractmethod
    async def stream_ticker(self, instruments: list[Instrument]):
        """Process ticker data. The processed data must be distributed via self.broadcast(msg)."""
        pass
    
    @abstractmethod
    async def stream_top_of_orderbook(self, instruments: list[Instrument]):
        """Process top of orderbook data. The processed data must be distributed via self.broadcast(msg)."""
        pass

    @abstractmethod
    async def stream_full_orderbook(self, instruments: list[Instrument]):
        """Process orderbook data. The processed data must be distributed via self.broadcast(msg)."""
        pass

    @abstractmethod
    async def stream_trades(self, instruments: list[Instrument]):
        """Process trade data. The processed data must be distributed via self.broadcast(msg)."""
        pass

    @abstractmethod
    async def run(self, instruments: list[Instrument], stream_types: set[MarketDataStreamType]):
        """Open and stream the required instruments and data types."""
        pass
