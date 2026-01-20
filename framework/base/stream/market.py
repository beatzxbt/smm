"""
Market data stream handler for processing public exchange data.

Provides abstract interface for streaming ticker, orderbook, and trade data.
"""

from __future__ import annotations

import asyncio
from abc import abstractmethod

from framework.base.common import Instrument, Venue
from framework.base.stream.models import (
    MarketDataStreamType,
    Msg,
)
from framework.base.stream.stream import DataStream
from mm_toolbox.logging.standard import Logger


class MarketDataStream(DataStream):
    """Base class for market data handling.

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
        super().__init__(venue, logger, consumer_queues)

    @abstractmethod
    async def stream_ticker(self, instruments: list[Instrument]) -> None:
        """Process ticker data. The processed data must be distributed via self.broadcast(msg).

        Args:
            instruments: List of instruments to stream ticker data for.
        """
        ...

    @abstractmethod
    async def stream_top_of_orderbook(self, instruments: list[Instrument]) -> None:
        """Process top of orderbook data. The processed data must be distributed via self.broadcast(msg).

        Args:
            instruments: List of instruments to stream top-of-book data for.
        """
        ...

    @abstractmethod
    async def stream_full_orderbook(self, instruments: list[Instrument]) -> None:
        """Process orderbook data. The processed data must be distributed via self.broadcast(msg).

        Args:
            instruments: List of instruments to stream full orderbook data for.
        """
        ...

    @abstractmethod
    async def stream_trades(self, instruments: list[Instrument]) -> None:
        """Process trade data. The processed data must be distributed via self.broadcast(msg).

        Args:
            instruments: List of instruments to stream trade data for.
        """
        ...

    @abstractmethod
    async def run(
        self, instruments: list[Instrument], stream_types: set[MarketDataStreamType]
    ) -> None:
        """Open and stream the required instruments and data types.

        Args:
            instruments: List of instruments to stream data for.
            stream_types: Set of data stream types to enable.
        """
        ...
