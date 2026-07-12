"""
Binance stream managers for market and private websocket flows.

Usage: create managers via class factories with a BinanceExchange instance.
Components: handler wiring and Binance-specific routing.
"""

from __future__ import annotations
from typing import cast

from framework.base.common import Venue
from framework.base.stream.connection import WebSocketConnection
from framework.base.stream.manager import MarketStreamManager, PrivateStreamManager
from framework.base.stream.shared import StreamSharedContext
from framework.base.trading.exchange import Exchange
from framework.base.trading.models import is_success
from framework.binance.trading.exchange import BinanceExchange
from framework.binance.stream.handlers import (
    BinanceBBOHandler,
    BinanceOrderbookHandler,
    BinancePrivateHandler,
    BinanceTickerHandler,
    BinanceTradesHandler,
)
from mm_toolbox.logging.standard import Logger
from mm_toolbox.ringbuffer import GenericRingBuffer

BINANCE_PUBLIC_URLS = {
    Venue.BINANCE_USDM: "wss://fstream.binance.com/public/ws",
    Venue.BINANCE_COINM: "wss://dstream.binance.com/public/ws",
}


class BinanceMarketStreamManager(MarketStreamManager):
    """Binance market stream manager with dedicated public connections."""

    @classmethod
    async def create(
        cls,
        exchange: Exchange,
        logger: Logger,
        consumer_buffer: GenericRingBuffer,
    ) -> "BinanceMarketStreamManager":
        """Create the Binance market stream manager.

        Args:
            exchange: Exchange client for instrument resolution.
            logger: Logger for diagnostics.
            consumer_buffer: Ring buffer to broadcast messages to.

        Returns:
            BinanceMarketStreamManager: Initialized manager instance.
        """
        if exchange.venue not in BINANCE_PUBLIC_URLS:
            raise ValueError("BinanceMarketStreamManager requires BinanceExchange.")

        instrument_collection = await exchange.get_instrument_collection_cached()
        endpoints = getattr(exchange, "endpoints", None)
        base_url = (
            endpoints.public_ws if endpoints else BINANCE_PUBLIC_URLS[exchange.venue]
        )
        market_url = (
            (endpoints.market_ws or endpoints.public_ws)
            if endpoints
            else base_url.replace("/public/", "/market/")
        )
        shared_context = StreamSharedContext()
        ticker_handler = BinanceTickerHandler(
            connection=WebSocketConnection(market_url, logger),
            instrument_collection=instrument_collection,
            venue=exchange.venue,
            logger=logger,
            consumer_buffer=consumer_buffer,
            exchange=exchange,  # type: ignore[arg-type]
            shared_context=shared_context,
        )
        bbo_handler = BinanceBBOHandler(
            connection=WebSocketConnection(base_url, logger),
            instrument_collection=instrument_collection,
            venue=exchange.venue,
            logger=logger,
            consumer_buffer=consumer_buffer,
            shared_context=shared_context,
        )
        orderbook_handler = BinanceOrderbookHandler(
            connection=WebSocketConnection(base_url, logger),
            instrument_collection=instrument_collection,
            venue=exchange.venue,
            logger=logger,
            consumer_buffer=consumer_buffer,
            shared_context=shared_context,
        )
        trades_handler = BinanceTradesHandler(
            connection=WebSocketConnection(base_url, logger),
            instrument_collection=instrument_collection,
            venue=exchange.venue,
            logger=logger,
            consumer_buffer=consumer_buffer,
            shared_context=shared_context,
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


class BinancePrivateStreamManager(PrivateStreamManager):
    """Binance private stream manager with unified handler."""

    @classmethod
    async def create(
        cls,
        exchange: Exchange,
        logger: Logger,
        consumer_buffer: GenericRingBuffer,
    ) -> "BinancePrivateStreamManager":
        """Create the Binance private stream manager.

        Args:
            exchange: Exchange client for instrument resolution.
            logger: Logger for diagnostics.
            consumer_buffer: Ring buffer to broadcast messages to.

        Returns:
            BinancePrivateStreamManager: Initialized manager instance.
        """
        if exchange.venue not in BINANCE_PUBLIC_URLS:
            raise ValueError("BinancePrivateStreamManager requires BinanceExchange.")

        exchange = cast(BinanceExchange, exchange)  # for .get_listen_key()
        instrument_collection = await exchange.get_instrument_collection_cached()
        listen_key_resp = await exchange.get_listen_key()
        if not is_success(listen_key_resp):
            raise RuntimeError(
                f"Failed to acquire listen key; {listen_key_resp.err_msg}"
            )
        listen_key = listen_key_resp.data
        endpoints = getattr(exchange, "endpoints", None)
        private_url = (
            endpoints.private_ws if endpoints else BINANCE_PUBLIC_URLS[exchange.venue]
        )
        wss_url = (
            f"{private_url}?listenKey={listen_key}"
            "&events=ORDER_TRADE_UPDATE/ACCOUNT_UPDATE"
        )
        shared_context = StreamSharedContext()

        handler = BinancePrivateHandler(
            venue=exchange.venue,
            logger=logger,
            connection=WebSocketConnection(wss_url, logger),
            instrument_collection=instrument_collection,
            consumer_buffer=consumer_buffer,
            exchange=exchange,
            listen_key=listen_key,
            shared_context=shared_context,
        )

        return cls(
            venue=exchange.venue,
            logger=logger,
            consumer_buffer=consumer_buffer,
            instrument_collection=instrument_collection,
            handler=handler,
        )
