"""
OKX stream managers for market and private websocket flows.

Usage: create managers via class factories with an OkxExchange instance.
Components: handler wiring and OKX-specific credential extraction.
"""

from __future__ import annotations

import asyncio

from framework.base.common import Venue
from framework.base.stream.connection import WebSocketConnection
from framework.base.stream.manager import MarketStreamManager, PrivateStreamManager
from framework.base.stream.models import Msg
from framework.base.trading.exchange import Exchange
from framework.okx.stream.handlers import (
    OkxBBOHandler,
    OkxOrderbookHandler,
    OkxPrivateHandler,
    OkxTickerHandler,
    OkxTradesHandler,
)
from framework.okx.trading.client import OkxHttpClient
from mm_toolbox.logging.standard import Logger

OKX_PUBLIC_URL = "wss://ws.okx.com:8443/ws/v5/public"
OKX_PRIVATE_URL = "wss://ws.okx.com:8443/ws/v5/private"


class OkxMarketStreamManager(MarketStreamManager):
    """OKX market stream manager with dedicated public connections."""

    @classmethod
    async def create(
        cls,
        exchange: Exchange,
        logger: Logger,
        consumer_queues: list[asyncio.Queue[Msg]],
    ) -> "OkxMarketStreamManager":
        """Create the OKX market stream manager.

        Args:
            exchange: Exchange client for instrument resolution.
            logger: Logger for diagnostics.
            consumer_queues: Queues to broadcast messages to.

        Returns:
            OkxMarketStreamManager: Initialized manager instance.
        """
        if exchange.venue != Venue.OKX:
            raise ValueError("OkxMarketStreamManager requires OkxExchange.")

        instrument_collection = await exchange.get_instrument_collection_cached()

        ticker_handler = OkxTickerHandler(
            connection=WebSocketConnection(OKX_PUBLIC_URL, logger),
            instrument_collection=instrument_collection,
            venue=exchange.venue,
            logger=logger,
            consumer_queues=consumer_queues,
        )
        bbo_handler = OkxBBOHandler(
            connection=WebSocketConnection(OKX_PUBLIC_URL, logger),
            instrument_collection=instrument_collection,
            venue=exchange.venue,
            logger=logger,
            consumer_queues=consumer_queues,
        )
        orderbook_handler = OkxOrderbookHandler(
            connection=WebSocketConnection(OKX_PUBLIC_URL, logger),
            instrument_collection=instrument_collection,
            venue=exchange.venue,
            logger=logger,
            consumer_queues=consumer_queues,
        )
        trades_handler = OkxTradesHandler(
            connection=WebSocketConnection(OKX_PUBLIC_URL, logger),
            instrument_collection=instrument_collection,
            venue=exchange.venue,
            logger=logger,
            consumer_queues=consumer_queues,
        )

        return cls(
            venue=exchange.venue,
            logger=logger,
            consumer_queues=consumer_queues,
            instrument_collection=instrument_collection,
            ticker_handler=ticker_handler,
            bbo_handler=bbo_handler,
            orderbook_handler=orderbook_handler,
            trades_handler=trades_handler,
        )


class OkxPrivateStreamManager(PrivateStreamManager):
    """OKX private stream manager with unified handler."""

    @classmethod
    async def create(
        cls,
        exchange: Exchange,
        logger: Logger,
        consumer_queues: list[asyncio.Queue[Msg]],
    ) -> "OkxPrivateStreamManager":
        """Create the OKX private stream manager.

        Args:
            exchange: Exchange client for instrument resolution.
            logger: Logger for diagnostics.
            consumer_queues: Queues to broadcast messages to.

        Returns:
            OkxPrivateStreamManager: Initialized manager instance.
        """
        if exchange.venue != Venue.OKX:
            raise ValueError("OkxPrivateStreamManager requires OkxExchange.")

        instrument_collection = await exchange.get_instrument_collection_cached()

        http_client: OkxHttpClient = exchange.http_client  # type: ignore[assignment]
        api_key = http_client.key
        api_secret = http_client.secret
        passphrase = http_client.passphrase

        handler = OkxPrivateHandler(
            venue=exchange.venue,
            logger=logger,
            connection=WebSocketConnection(OKX_PRIVATE_URL, logger),
            instrument_collection=instrument_collection,
            consumer_queues=consumer_queues,
            api_key=api_key,
            api_secret=api_secret,
            passphrase=passphrase,
        )

        return cls(
            venue=exchange.venue,
            logger=logger,
            consumer_queues=consumer_queues,
            instrument_collection=instrument_collection,
            handler=handler,
        )
