"""
OKX stream managers for market and private websocket flows.

Usage: create managers via class factories with an OkxExchange instance.
Components: handler wiring and OKX-specific credential extraction.
"""

from __future__ import annotations


from framework.base.common import Venue
from framework.base.stream.connection import WebSocketConnection
from framework.base.stream.manager import MarketStreamManager, PrivateStreamManager
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
from mm_toolbox.ringbuffer import GenericRingBuffer

OKX_PUBLIC_URL = "wss://ws.okx.com:8443/ws/v5/public"
OKX_PRIVATE_URL = "wss://ws.okx.com:8443/ws/v5/private"


class OkxMarketStreamManager(MarketStreamManager):
    """OKX market stream manager with dedicated public connections."""

    @classmethod
    async def create(
        cls,
        exchange: Exchange,
        logger: Logger,
        consumer_buffer: GenericRingBuffer,
    ) -> "OkxMarketStreamManager":
        """Create the OKX market stream manager.

        Args:
            exchange: Exchange client for instrument resolution.
            logger: Logger for diagnostics.
            consumer_buffer: Ring buffer to broadcast messages to.

        Returns:
            OkxMarketStreamManager: Initialized manager instance.
        """
        if exchange.venue != Venue.OKX:
            raise ValueError("OkxMarketStreamManager requires OkxExchange.")

        instrument_collection = await exchange.get_instrument_collection_cached()
        endpoints = getattr(exchange, "endpoints", None)
        public_url = endpoints.public_ws if endpoints else OKX_PUBLIC_URL

        ticker_handler = OkxTickerHandler(
            connection=WebSocketConnection(public_url, logger),
            instrument_collection=instrument_collection,
            venue=exchange.venue,
            logger=logger,
            consumer_buffer=consumer_buffer,
        )
        bbo_handler = OkxBBOHandler(
            connection=WebSocketConnection(public_url, logger),
            instrument_collection=instrument_collection,
            venue=exchange.venue,
            logger=logger,
            consumer_buffer=consumer_buffer,
        )
        orderbook_handler = OkxOrderbookHandler(
            connection=WebSocketConnection(public_url, logger),
            instrument_collection=instrument_collection,
            venue=exchange.venue,
            logger=logger,
            consumer_buffer=consumer_buffer,
        )
        trades_handler = OkxTradesHandler(
            connection=WebSocketConnection(public_url, logger),
            instrument_collection=instrument_collection,
            venue=exchange.venue,
            logger=logger,
            consumer_buffer=consumer_buffer,
        )

        return cls(
            venue=exchange.venue,
            logger=logger,
            consumer_buffer=consumer_buffer,
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
        consumer_buffer: GenericRingBuffer,
    ) -> "OkxPrivateStreamManager":
        """Create the OKX private stream manager.

        Args:
            exchange: Exchange client for instrument resolution.
            logger: Logger for diagnostics.
            consumer_buffer: Ring buffer to broadcast messages to.

        Returns:
            OkxPrivateStreamManager: Initialized manager instance.
        """
        if exchange.venue != Venue.OKX:
            raise ValueError("OkxPrivateStreamManager requires OkxExchange.")

        instrument_collection = await exchange.get_instrument_collection_cached()
        endpoints = getattr(exchange, "endpoints", None)
        private_url = endpoints.private_ws if endpoints else OKX_PRIVATE_URL

        http_client: OkxHttpClient = exchange.http_client  # type: ignore[assignment]
        api_key = http_client.key
        api_secret = http_client.secret
        passphrase = http_client.passphrase

        handler = OkxPrivateHandler(
            venue=exchange.venue,
            logger=logger,
            connection=WebSocketConnection(private_url, logger),
            instrument_collection=instrument_collection,
            consumer_buffer=consumer_buffer,
            api_key=api_key,
            api_secret=api_secret,
            passphrase=passphrase,
        )

        return cls(
            venue=exchange.venue,
            logger=logger,
            consumer_buffer=consumer_buffer,
            instrument_collection=instrument_collection,
            handler=handler,
        )
