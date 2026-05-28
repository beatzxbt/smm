"""Base trader runtime for configuring streams, routing, and lifecycle.

Usage: subclass BaseTrader and override consume_msg/update_state.
Components: stream setup, heartbeat tracking, and shutdown orchestration.
"""

from __future__ import annotations

import asyncio
from abc import ABC, abstractmethod
from typing import final

from framework.base.common import Instrument, Venue
from framework.base.stream.manager import MarketStreamManager, PrivateStreamManager
from framework.base.stream.models import (
    ALL_MARKET_DATA_STREAM_TYPES,
    ALL_PRIVATE_DATA_STREAM_TYPES,
    DataMsg,
    DataStreamEvent,
    DataStreamEventMsg,
)
from framework.base.trading.exchange import Exchange
from framework.loader import VenueBundle, load_venue_bundle
from mm_toolbox.logging.standard import Logger
from mm_toolbox.ringbuffer import GenericRingBuffer
from mm_toolbox.rounding import Rounder, RounderConfig
from mm_toolbox.time import time_ns, time_s

from smm.config import AppConfig
from smm.traders.base.oms import BaseOrderManagementSystem

STREAM_MESSAGE_BUFFER_CAPACITY = 2**16  # 16384


class BaseTrader(ABC):
    """Base trader that manages exchange streams and component lifecycle.

    Attributes:
        config (AppConfig): Application configuration.
        logger (Logger): Logger instance.
        exchange (Exchange): Exchange client.
        instrument (Instrument): Resolved instrument.
        rounder (Rounder): Price/size rounder.
        market_data (MarketStreamManager): Market data stream manager.
        private_data (PrivateStreamManager): Private data stream manager.
        producer_buffer (GenericRingBuffer): Stream ring buffer.
        oms (BaseOrderManagementSystem | None): OMS implementation.
    """

    def __init__(
        self,
        config: AppConfig,
        logger: Logger,
        exchange: Exchange,
        instrument: Instrument,
        rounder: Rounder,
        market_data: MarketStreamManager,
        private_data: PrivateStreamManager,
        producer_buffer: GenericRingBuffer,
    ) -> None:
        """Initialize the trader with runtime dependencies.

        Args:
            config (AppConfig): Application configuration.
            logger (Logger): Logger instance.
            exchange (Exchange): Exchange client.
            instrument (Instrument): Resolved instrument.
            rounder (Rounder): Price/size rounder.
            market_data (MarketStreamManager): Market data stream manager.
            private_data (PrivateStreamManager): Private data stream manager.
            producer_buffer (GenericRingBuffer): Ring buffer for stream messages.

        """
        self.config = config
        self.logger = logger
        self.exchange = exchange
        self.instrument = instrument
        self.rounder = rounder
        self.market_data = market_data
        self.private_data = private_data
        self.producer_buffer = producer_buffer

        self.oms: BaseOrderManagementSystem | None = None
        self._heartbeat_task: asyncio.Task[None] | None = None

    @classmethod
    async def create(cls, config: AppConfig, logger: Logger) -> BaseTrader:
        """Create a trader instance with resolved exchange dependencies.

        Args:
            config (AppConfig): Application configuration.
            logger (Logger): Logger instance.

        Returns:
            BaseTrader: Initialized trader instance.
        """
        venue_bundle = load_venue_bundle(config.core.venue)
        exchange = cls._build_exchange(venue_bundle, config.core.venue, logger)
        instrument = await exchange.resolve_instrument(config.core.symbol)
        rounder = await cls._build_rounder(exchange, instrument)
        buffer: GenericRingBuffer = GenericRingBuffer(STREAM_MESSAGE_BUFFER_CAPACITY)
        market_data = await cls._build_market_data(
            venue_bundle, config.core.venue, exchange, logger, buffer
        )
        private_data = await cls._build_private_data(
            venue_bundle, config.core.venue, exchange, logger, buffer
        )
        return cls(
            config=config,
            logger=logger,
            exchange=exchange,
            instrument=instrument,
            rounder=rounder,
            market_data=market_data,
            private_data=private_data,
            producer_buffer=buffer,
        )

    @staticmethod
    def _build_exchange(
        venue_bundle: VenueBundle, venue: Venue, logger: Logger
    ) -> Exchange:
        """Build an exchange instance for a venue.

        Args:
            venue_bundle (VenueBundle): Loaded venue bundle for the venue.
            venue (Venue): Venue identifier.
            logger (Logger): Logger instance.

        Returns:
            Exchange: Exchange instance for the venue.
        """
        if venue in (Venue.BINANCE_USDM, Venue.BINANCE_COINM):
            return venue_bundle.exchange(
                logger=logger,
                load_secrets=True,
                is_usd_margined=venue == Venue.BINANCE_USDM,
            )
        if venue == Venue.BYBIT:
            return venue_bundle.exchange(logger=logger, load_secrets=True)
        raise ValueError(f"Unsupported venue: {venue}")

    @staticmethod
    async def _build_rounder(exchange: Exchange, instrument: Instrument) -> Rounder:
        """Build a rounder from instrument info.

        Args:
            exchange (Exchange): Exchange client to query instrument info.
            instrument (Instrument): Resolved instrument.

        Returns:
            Rounder: Rounder configured with tick/lot sizes.
        """
        response = await exchange.get_instrument_info([instrument])
        if not response.is_successful:
            raise RuntimeError(f"Failed to load instrument info; {response.err_msg}")
        info = response.data[0]
        return Rounder(
            RounderConfig.default(tick_size=info.tick_size, lot_size=info.lot_size)
        )

    @staticmethod
    async def _build_market_data(
        venue_bundle: VenueBundle,
        venue: Venue,
        exchange: Exchange,
        logger: Logger,
        buffer: GenericRingBuffer,
    ) -> MarketStreamManager:
        """Build the market stream manager for a venue.

        Args:
            venue_bundle (VenueBundle): Loaded venue bundle for the venue.
            venue (Venue): Venue identifier.
            logger (Logger): Logger instance.
            buffer (GenericRingBuffer): Producer ring buffer for streaming messages.

        Returns:
            MarketStreamManager: Market stream manager instance.
        """
        if venue in (Venue.BINANCE_USDM, Venue.BINANCE_COINM):
            return await venue_bundle.market_stream_manager.create(
                exchange=exchange,
                logger=logger,
                consumer_buffer=buffer,
            )
        if venue == Venue.BYBIT:
            return await venue_bundle.market_stream_manager.create(
                exchange=exchange,
                logger=logger,
                consumer_buffer=buffer,
            )
        raise ValueError(f"Unsupported venue: {venue}")

    @staticmethod
    async def _build_private_data(
        venue_bundle: VenueBundle,
        venue: Venue,
        exchange: Exchange,
        logger: Logger,
        buffer: GenericRingBuffer,
    ) -> PrivateStreamManager:
        """Build the private stream manager for a venue.

        Args:
            venue_bundle (VenueBundle): Loaded venue bundle for the venue.
            venue (Venue): Venue identifier.
            exchange (Exchange): Exchange client to reuse for streams.
            logger (Logger): Logger instance.
            buffer (GenericRingBuffer): Producer ring buffer for streaming messages.

        Returns:
            PrivateStreamManager: Private stream manager instance.
        """
        if venue in (Venue.BINANCE_USDM, Venue.BINANCE_COINM):
            return await venue_bundle.private_stream_manager.create(
                exchange=exchange,
                logger=logger,
                consumer_buffer=buffer,
            )
        if venue == Venue.BYBIT:
            return await venue_bundle.private_stream_manager.create(
                exchange=exchange,
                logger=logger,
                consumer_buffer=buffer,
            )
        raise ValueError(f"Unsupported venue: {venue}")

    @final
    async def run(self) -> None:
        """Run the trader event loop and stream tasks."""
        tasks: list[asyncio.Task[None]] = []
        try:
            await self.exchange.connect_ws_client()
            await self.market_data.start()
            await self.private_data.start()
            await self.market_data.subscribe(
                instruments=[self.instrument],
                stream_types=ALL_MARKET_DATA_STREAM_TYPES,
            )
            await self.private_data.subscribe(
                instruments=[self.instrument],
                stream_types=ALL_PRIVATE_DATA_STREAM_TYPES,
            )
            tasks = [asyncio.create_task(self._consume_loop())]
            await asyncio.gather(*tasks)
        except asyncio.CancelledError:
            self.logger.info("Trader cancelled; shutting down.")
        except Exception as exc:
            self.logger.error(f"Trader error; {exc}")
        finally:
            for task in tasks:
                task.cancel()
            await asyncio.gather(*tasks, return_exceptions=True)
            await self.shutdown()

    @final
    async def _consume_loop(self) -> None:
        """Consume stream messages and update trader state."""
        while True:
            msg = await self.producer_buffer.aconsume()
            match msg:
                case DataStreamEventMsg(event=DataStreamEvent.HEARTBEAT):
                    await self.received_heartbeat(msg)
                case _:
                    await self.consume_msg(msg)
                    await self.update_state()

    @final
    async def received_heartbeat(self, msg: DataStreamEventMsg) -> None:
        """Track a heartbeat message.

        Args:
            msg (DataStreamEventMsg): Heartbeat message.

        """
        if self._heartbeat_task is not None:
            self._heartbeat_task.cancel()
        self._heartbeat_task = asyncio.create_task(self._track_heartbeat(msg))

    @final
    async def _track_heartbeat(self, msg: DataStreamEventMsg) -> None:
        """Monitor heartbeat timing to detect stalled streams.

        Args:
            msg (DataStreamEventMsg): Heartbeat message to schedule against.

        """
        allowed_delay_s = 1.0
        time_next_check_s = msg.time_next_check_ms / 1000.0
        time_to_next_check_s = time_next_check_s - time_s() + allowed_delay_s
        if time_to_next_check_s <= 0:
            raise ValueError("Heartbeat next_check timestamp must be in the future.")
        try:
            await asyncio.sleep(time_to_next_check_s)
            raise ConnectionError("Heartbeat timed out.")
        except asyncio.CancelledError:
            return

    @final
    def is_stale(self, msg: DataMsg, buffer_ms: int) -> bool:
        """Return True if a message is older than the provided buffer.

        Args:
            msg (DataMsg): Data message to evaluate.
            buffer_ms (int): Age threshold in milliseconds.

        Returns:
            bool: True if the message is stale, False otherwise.
        """
        buffer_ns = buffer_ms * 1_000_000
        age_ns = time_ns() - msg.moments.recv_time_ns
        return age_ns > buffer_ns

    async def shutdown(self) -> None:
        """Shutdown internal components and close clients."""
        await asyncio.gather(
            self.market_data.stop(),
            self.private_data.stop(),
            return_exceptions=True,
        )
        if self.oms is not None:
            await self.oms.kill_switch()
        await self.exchange.close_clients()
        self.logger.shutdown()

    @abstractmethod
    async def consume_msg(self, msg: DataMsg) -> None:
        """Consume a data message from the streams.

        Args:
            msg (DataMsg): Data message to process.

        """

    @abstractmethod
    async def update_state(self) -> None:
        """Update desired state and send OMS actions."""
