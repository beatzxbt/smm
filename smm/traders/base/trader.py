"""Base trader runtime for configuring streams, routing, and lifecycle.

Usage: subclass BaseTrader and override consume_msg/update_state.
Components: stream setup, heartbeat tracking, and shutdown orchestration.
"""

from __future__ import annotations

import asyncio
from abc import ABC, abstractmethod
from typing import final

from framework.base.common import Instrument, Venue
from framework.base.stream.market import MarketDataStream
from framework.base.stream.models import (
    ALL_MARKET_DATA_STREAM_TYPES,
    ALL_PRIVATE_DATA_STREAM_TYPES,
    DataMsg,
    HeartbeatMsg,
    Msg,
)
from framework.base.stream.private import PrivateDataStream
from framework.base.tools.multiq import consume_multiq
from framework.base.trading.exchange import Exchange
from framework.base.trading.models import Secret
from framework.loader import VenueBundle, load_venue_bundle
from mm_toolbox.logging.standard import Logger
from mm_toolbox.rounding import Rounder, RounderConfig
from mm_toolbox.time import time_ns, time_s

from smm.config import AppConfig
from smm.traders.base.oms import BaseOrderManagementSystem


class BaseTrader(ABC):
    """Base trader that manages exchange streams and component lifecycle.

    Attributes:
        config (AppConfig): Application configuration.
        logger (Logger): Logger instance.
        exchange (Exchange): Exchange client.
        instrument (Instrument): Resolved instrument.
        rounder (Rounder): Price/size rounder.
        market_data (MarketDataStream): Market data stream.
        private_data (PrivateDataStream): Private data stream.
        producer_queues (list[asyncio.Queue[Msg]]): Stream queues.
        oms (BaseOrderManagementSystem | None): OMS implementation.
    """

    def __init__(
        self,
        config: AppConfig,
        logger: Logger,
        exchange: Exchange,
        instrument: Instrument,
        rounder: Rounder,
        market_data: MarketDataStream,
        private_data: PrivateDataStream,
        producer_queues: list[asyncio.Queue[Msg]],
    ) -> None:
        """Initialize the trader with runtime dependencies.

        Args:
            config (AppConfig): Application configuration.
            logger (Logger): Logger instance.
            exchange (Exchange): Exchange client.
            instrument (Instrument): Resolved instrument.
            rounder (Rounder): Price/size rounder.
            market_data (MarketDataStream): Market data stream.
            private_data (PrivateDataStream): Private data stream.
            producer_queues (list[asyncio.Queue[Msg]]): Queues for stream messages.

        Returns:
            None.
        """
        self.config = config
        self.logger = logger
        self.exchange = exchange
        self.instrument = instrument
        self.rounder = rounder
        self.market_data = market_data
        self.private_data = private_data
        self.producer_queues = producer_queues

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
        queues = [asyncio.Queue()]
        market_data = cls._build_market_data(
            venue_bundle, config.core.venue, logger, queues
        )
        private_data = cls._build_private_data(
            venue_bundle, config.core.venue, exchange, logger, queues
        )
        return cls(
            config=config,
            logger=logger,
            exchange=exchange,
            instrument=instrument,
            rounder=rounder,
            market_data=market_data,
            private_data=private_data,
            producer_queues=queues,
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
    def _build_market_data(
        venue_bundle: VenueBundle,
        venue: Venue,
        logger: Logger,
        queues: list[asyncio.Queue[Msg]],
    ) -> MarketDataStream:
        """Build the market data stream for a venue.

        Args:
            venue_bundle (VenueBundle): Loaded venue bundle for the venue.
            venue (Venue): Venue identifier.
            logger (Logger): Logger instance.
            queues (list[asyncio.Queue[Msg]]): Producer queues for streaming messages.

        Returns:
            MarketDataStream: Market data stream instance.
        """
        if venue in (Venue.BINANCE_USDM, Venue.BINANCE_COINM):
            return venue_bundle.market_data_stream(
                logger=logger,
                consumer_queues=queues,
                is_usd_margined=venue == Venue.BINANCE_USDM,
            )
        if venue == Venue.BYBIT:
            return venue_bundle.market_data_stream(
                logger=logger,
                consumer_queues=queues,
            )
        raise ValueError(f"Unsupported venue: {venue}")

    @staticmethod
    def _build_private_data(
        venue_bundle: VenueBundle,
        venue: Venue,
        exchange: Exchange,
        logger: Logger,
        queues: list[asyncio.Queue[Msg]],
    ) -> PrivateDataStream:
        """Build the private data stream for a venue.

        Args:
            venue_bundle (VenueBundle): Loaded venue bundle for the venue.
            venue (Venue): Venue identifier.
            exchange (Exchange): Exchange client to reuse for streams.
            logger (Logger): Logger instance.
            queues (list[asyncio.Queue[Msg]]): Producer queues for streaming messages.

        Returns:
            PrivateDataStream: Private data stream instance.
        """
        if venue in (Venue.BINANCE_USDM, Venue.BINANCE_COINM):
            return venue_bundle.private_data_stream(
                exchange_client=exchange,
                logger=logger,
                consumer_queues=queues,
            )
        if venue == Venue.BYBIT:
            key = Secret.load("BYBIT_KEY")
            secret = Secret.load("BYBIT_SECRET")
            return venue_bundle.private_data_stream(
                key=key,
                secret=secret,
                logger=logger,
                consumer_queues=queues,
            )
        raise ValueError(f"Unsupported venue: {venue}")

    @final
    async def run(self) -> None:
        """Run the trader event loop and stream tasks.

        Returns:
            None.
        """
        tasks: list[asyncio.Task[None]] = []
        try:
            await self.exchange.connect_ws_client()
            tasks = [
                asyncio.create_task(
                    self.market_data.run(
                        instruments=[self.instrument],
                        stream_types=ALL_MARKET_DATA_STREAM_TYPES,
                    )
                ),
                asyncio.create_task(
                    self.private_data.run(
                        instruments=[self.instrument],
                        stream_types=ALL_PRIVATE_DATA_STREAM_TYPES,
                    )
                ),
                asyncio.create_task(self._consume_loop()),
            ]
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
        """Consume stream messages and update trader state.

        Returns:
            None.
        """
        async for msg in consume_multiq(self.producer_queues):
            match msg:
                case HeartbeatMsg():
                    await self.received_heartbeat(msg)
                case _:
                    await self.consume_msg(msg)
                    await self.update_state()

    @final
    async def received_heartbeat(self, msg: HeartbeatMsg) -> None:
        """Track a heartbeat message.

        Args:
            msg (HeartbeatMsg): Heartbeat message.

        Returns:
            None.
        """
        if self._heartbeat_task is not None:
            self._heartbeat_task.cancel()
        self._heartbeat_task = asyncio.create_task(self._track_heartbeat(msg))

    @final
    async def _track_heartbeat(self, msg: HeartbeatMsg) -> None:
        """Monitor heartbeat timing to detect stalled streams.

        Args:
            msg (HeartbeatMsg): Heartbeat message to schedule against.

        Returns:
            None.
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
        """Shutdown internal components and close clients.

        Returns:
            None.
        """
        self.market_data.is_running = False
        self.private_data.is_running = False
        if self.oms is not None:
            await self.oms.kill_switch()
        await self.exchange.close_clients()
        await self.logger.shutdown()

    @abstractmethod
    async def consume_msg(self, msg: DataMsg) -> None:
        """Consume a data message from the streams.

        Args:
            msg (DataMsg): Data message to process.

        Returns:
            None.
        """

    @abstractmethod
    async def update_state(self) -> None:
        """Update desired state and send OMS actions.

        Returns:
            None.
        """
