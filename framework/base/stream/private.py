"""
Private data stream handler for processing authenticated exchange data.

Provides abstract interface for streaming order, position, execution, and account data.
"""

from __future__ import annotations

import asyncio
from abc import abstractmethod

from framework.base.common import Instrument, Venue
from framework.base.stream.models import (
    Msg,
    PrivateDataStreamType,
)
from framework.base.stream.stream import DataStream
from mm_toolbox.logging.standard import Logger


class PrivateDataStream(DataStream):
    """Base class for handling private data streams.

    Args:
        venue (Venue): The exchange venue this stream connects to.
        logger (Logger): Logger instance for debug and error messages.
        consumer_queues (list[asyncio.Queue[Msg]]): Queues to broadcast messages to.
    """

    def __init__(
        self,
        venue: Venue,
        logger: Logger,
        consumer_queues: list[asyncio.Queue[Msg]],
    ) -> None:
        """Initialize the private data stream base.

        Args:
            venue (Venue): The exchange venue this stream connects to.
            logger (Logger): Logger instance for debug and error messages.
            consumer_queues (list[asyncio.Queue[Msg]]): Queues to broadcast messages to.

        Returns:
            None.
        """
        super().__init__(venue, logger, consumer_queues)

    @abstractmethod
    async def stream_order(self, instruments: list[Instrument]) -> None:
        """Process order data. The processed data must be distributed via self.broadcast(msg).

        Args:
            instruments (list[Instrument]): Instruments to stream order data for.

        Returns:
            None.
        """
        ...

    @abstractmethod
    async def stream_position(self, instruments: list[Instrument]) -> None:
        """Process position data. The processed data must be distributed via self.broadcast(msg).

        Args:
            instruments (list[Instrument]): Instruments to stream position data for.

        Returns:
            None.
        """
        ...

    @abstractmethod
    async def stream_execution(self, instruments: list[Instrument]) -> None:
        """Process execution data. The processed data must be distributed via self.broadcast(msg).

        Args:
            instruments (list[Instrument]): Instruments to stream execution data for.

        Returns:
            None.
        """
        ...

    @abstractmethod
    async def stream_account(self) -> None:
        """Process account data. The processed data must be distributed via self.broadcast(msg).

        Returns:
            None.
        """
        ...

    @abstractmethod
    async def run(
        self, instruments: list[Instrument], stream_types: set[PrivateDataStreamType]
    ) -> None:
        """Open and stream the required instruments and data types.

        Args:
            instruments (list[Instrument]): Instruments to stream data for.
            stream_types (set[PrivateDataStreamType]): Stream types to enable.

        Returns:
            None.
        """
        ...
