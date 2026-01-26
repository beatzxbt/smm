"""
Binance stream managers for market and private websocket flows.

Usage: create managers via class factories with a BinanceExchange instance.
Components: handler wiring and Binance-specific routing.
"""

from __future__ import annotations

import asyncio

from framework.base.common import Venue
from framework.base.stream.connection import WebSocketConnection
from framework.base.stream.manager import MarketStreamManager, PrivateStreamManager
from framework.base.stream.models import Msg
from framework.base.trading.exchange import Exchange
from framework.binance.stream.handlers import (
    BinanceBBOHandler,
    BinanceOrderbookHandler,
    BinancePrivateHandler,
    BinanceTickerHandler,
    BinanceTradesHandler,
)
from mm_toolbox.logging.standard import Logger

BINANCE_PUBLIC_URLS = {
    Venue.BINANCE_USDM: "wss://fstream.binance.com/ws",
    Venue.BINANCE_COINM: "wss://dstream.binance.com/ws",
}


class BinanceMarketStreamManager(MarketStreamManager):
    """Binance market stream manager with dedicated public connections."""

    @classmethod
    async def create(
        cls,
        exchange: Exchange,
        logger: Logger,
        consumer_queues: list[asyncio.Queue],
    ) -> "BinanceMarketStreamManager":
        """Create the Binance market stream manager.

        Args:
            exchange: Exchange client for instrument resolution.
            logger: Logger for diagnostics.
            consumer_queues: Queues to broadcast messages to.

        Returns:
            BinanceMarketStreamManager: Initialized manager instance.
        """
        if exchange.venue not in BINANCE_PUBLIC_URLS:
            raise ValueError("BinanceMarketStreamManager requires BinanceExchange.")

        instrument_collection = await exchange.get_instrument_collection_cached()
        base_url = BINANCE_PUBLIC_URLS[exchange.venue]
        ticker_handler = BinanceTickerHandler(
            connection=WebSocketConnection(base_url, logger),
            instrument_collection=instrument_collection,
            venue=exchange.venue,
            logger=logger,
            consumer_queues=consumer_queues,
            exchange=exchange,  # type: ignore[arg-type]
        )
        bbo_handler = BinanceBBOHandler(
            connection=WebSocketConnection(base_url, logger),
            instrument_collection=instrument_collection,
            venue=exchange.venue,
            logger=logger,
            consumer_queues=consumer_queues,
        )
        orderbook_handler = BinanceOrderbookHandler(
            connection=WebSocketConnection(base_url, logger),
            instrument_collection=instrument_collection,
            venue=exchange.venue,
            logger=logger,
            consumer_queues=consumer_queues,
        )
        trades_handler = BinanceTradesHandler(
            connection=WebSocketConnection(base_url, logger),
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


class BinancePrivateStreamManager(PrivateStreamManager):
    """Binance private stream manager with unified handler."""

    @classmethod
    async def create(
        cls,
        exchange: Exchange,
        logger: Logger,
        consumer_queues: list[asyncio.Queue[Msg]],
    ) -> "BinancePrivateStreamManager":
        """Create the Binance private stream manager.

        Args:
            exchange: Exchange client for instrument resolution.
            logger: Logger for diagnostics.
            consumer_queues: Queues to broadcast messages to.

        Returns:
            BinancePrivateStreamManager: Initialized manager instance.
        """
        if exchange.venue not in BINANCE_PUBLIC_URLS:
            raise ValueError("BinancePrivateStreamManager requires BinanceExchange.")

        instrument_collection = await exchange.get_instrument_collection_cached()
        listen_key_resp = await exchange.get_listen_key()
        if listen_key_resp.is_successful is False:
            raise RuntimeError(
                f"Failed to acquire listen key; {listen_key_resp.err_msg}"
            )
        listen_key = listen_key_resp.data
        wss_url = f"{BINANCE_PUBLIC_URLS[exchange.venue]}/{listen_key}"

        handler = BinancePrivateHandler(
            venue=exchange.venue,
            logger=logger,
            connection=WebSocketConnection(wss_url, logger),
            instrument_collection=instrument_collection,
            consumer_queues=consumer_queues,
            exchange=exchange,
            listen_key=listen_key,
        )

        return cls(
            venue=exchange.venue,
            logger=logger,
            consumer_queues=consumer_queues,
            instrument_collection=instrument_collection,
            handler=handler,
        )
