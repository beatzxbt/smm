"""
Bybit stream managers for market and private websocket flows.

Usage: create managers via class factories with an Exchange instance.
Components: handler wiring and Bybit-specific routing.
"""

from __future__ import annotations

import asyncio

from framework.base.stream.connection import WebSocketConnection
from framework.base.stream.manager import MarketStreamManager, PrivateStreamManager
from framework.base.stream.models import Msg
from framework.base.trading.exchange import Exchange
from framework.bybit.stream.handlers import (
    BybitBBOHandler,
    BybitOrderbookHandler,
    BybitPrivateHandler,
    BybitTickerHandler,
    BybitTradesHandler,
)
from mm_toolbox.logging.standard import Logger

BYBIT_PUBLIC_STREAM_URL = "wss://stream.bybit.com/v5/public/linear"
BYBIT_PRIVATE_STREAM_URL = "wss://stream.bybit.com/v5/private"


class BybitMarketStreamManager(MarketStreamManager):
    """Bybit market stream manager with dedicated public connections."""

    @classmethod
    async def create(
        cls,
        exchange: Exchange,
        logger: Logger,
        consumer_queues: list[asyncio.Queue],
    ) -> "BybitMarketStreamManager":
        """Create the Bybit market stream manager.

        Args:
            exchange: Exchange client for instrument resolution.
            logger: Logger for diagnostics.
            consumer_queues: Queues to broadcast messages to.

        Returns:
            BybitMarketStreamManager: Initialized manager instance.
        """
        instrument_collection = await exchange.get_instrument_collection_cached()
        venue = exchange.venue
        ticker_handler = BybitTickerHandler(
            connection=WebSocketConnection(BYBIT_PUBLIC_STREAM_URL, logger),
            instrument_collection=instrument_collection,
            venue=venue,
            logger=logger,
            consumer_queues=consumer_queues,
        )
        bbo_handler = BybitBBOHandler(
            connection=WebSocketConnection(BYBIT_PUBLIC_STREAM_URL, logger),
            instrument_collection=instrument_collection,
            venue=venue,
            logger=logger,
            consumer_queues=consumer_queues,
        )
        orderbook_handler = BybitOrderbookHandler(
            connection=WebSocketConnection(BYBIT_PUBLIC_STREAM_URL, logger),
            instrument_collection=instrument_collection,
            venue=venue,
            logger=logger,
            consumer_queues=consumer_queues,
        )
        trades_handler = BybitTradesHandler(
            connection=WebSocketConnection(BYBIT_PUBLIC_STREAM_URL, logger),
            instrument_collection=instrument_collection,
            venue=venue,
            logger=logger,
            consumer_queues=consumer_queues,
        )
        return cls(
            venue=venue,
            logger=logger,
            consumer_queues=consumer_queues,
            instrument_collection=instrument_collection,
            ticker_handler=ticker_handler,
            bbo_handler=bbo_handler,
            orderbook_handler=orderbook_handler,
            trades_handler=trades_handler,
        )


class BybitPrivateStreamManager(PrivateStreamManager):
    """Bybit private stream manager with unified handler."""

    @classmethod
    async def create(
        cls,
        exchange: Exchange,
        logger: Logger,
        consumer_queues: list[asyncio.Queue[Msg]],
    ) -> "BybitPrivateStreamManager":
        """Create the Bybit private stream manager.

        Args:
            exchange: Exchange client for instrument resolution.
            logger: Logger for diagnostics.
            consumer_queues: Queues to broadcast messages to.

        Returns:
            BybitPrivateStreamManager: Initialized manager instance.
        """
        instrument_collection = await exchange.get_instrument_collection_cached()
        venue = exchange.venue
        key, secret = cls._resolve_credentials(exchange)

        handler = BybitPrivateHandler(
            venue=venue,
            logger=logger,
            connection=WebSocketConnection(BYBIT_PRIVATE_STREAM_URL, logger),
            instrument_collection=instrument_collection,
            consumer_queues=consumer_queues,
            key=key,
            secret=secret,
        )

        return cls(
            venue=venue,
            logger=logger,
            consumer_queues=consumer_queues,
            instrument_collection=instrument_collection,
            handler=handler,
        )

    @staticmethod
    def _resolve_credentials(exchange: Exchange) -> tuple[str, str]:
        """Extract Bybit credentials from the exchange client.

        Args:
            exchange: Exchange client with loaded secrets.

        Returns:
            tuple[str, str]: API key and secret.
        """
        http_client = getattr(exchange, "http_client", None)
        key = getattr(http_client, "key", "")
        secret = getattr(http_client, "secret", "")
        if not key or not secret:
            raise RuntimeError("Bybit credentials not available on exchange client.")
        return str(key), str(secret)
