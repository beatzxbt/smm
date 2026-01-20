"""framework.bybit.stream.market"""

from __future__ import annotations

import asyncio
from typing import cast

import msgspec

from framework.base.common import Instrument, InstrumentCollection, Venue
from framework.base.stream.market import MarketDataStream
from framework.base.stream.models import (
    ALL_MARKET_DATA_STREAM_TYPES,
    MarketDataStreamType,
    Msg,
    TickerMsg,
)
from framework.base.tools import SimpleCache
from mm_toolbox.logging.standard import Logger
from mm_toolbox.websocket import WsConnectionConfig, WsSingle
from framework.bybit.stream.structs import (
    BybitOrderbookMsg,
    BybitPublicMsg,
    BybitTickerMsg,
    BybitTradePublicMsg,
)

WS_PUBLIC_STREAM_URL = "wss://stream.bybit.com/v5/public/linear"


class BybitMarketDataStream(MarketDataStream):
    """Bybit public market data stream implementation."""

    def __init__(
        self,
        logger: Logger,
        consumer_queues: list[asyncio.Queue[Msg]],
    ) -> None:
        """Initialize the Bybit market data stream.

        Args:
            logger: Logger instance for diagnostics.
            consumer_queues: Queues to broadcast messages to.
        """
        super().__init__(
            venue=Venue.BYBIT,
            logger=logger,
            consumer_queues=consumer_queues,
        )

        # Bybit sends partial ticker data sometimes, so we store a snapshot
        # of all ticker data to copy from in the handler for accurate broadcasting.
        self._latest_symbol_ticker_map: dict[str, TickerMsg] = {}

    def populate_instrument_collection(self, collection: InstrumentCollection) -> None:
        """Populate the instrument collection with tracked instruments.

        Args:
            collection: Empty collection to populate with instruments.
        """
        for instrument in self._instruments:
            collection.add(instrument)

    def instrument_to_symbol(self, instrument: Instrument) -> str:
        """Format an instrument into a Bybit symbol string.

        Args:
            instrument: Instrument to format.

        Returns:
            str: Symbol for websocket subscriptions.
        """
        return f"{instrument.base}{instrument.quote}".upper()

    async def stream_ticker(self, instruments: list[Instrument]):
        """Stream ticker updates for instruments.

        Args:
            instruments: Instruments to subscribe to.
        """
        on_connect: dict[str, str | list[str]] = {"op": "subscribe", "args": []}

        for instrument in instruments:
            symbol = self.instrument_to_symbol(instrument)
            cast(list[str], on_connect["args"]).append(f"tickers.{symbol}")

        on_connect_bytes = [msgspec.json.encode(on_connect)]
        json_decoder = msgspec.json.Decoder(BybitPublicMsg[BybitTickerMsg])
        ws_config = WsConnectionConfig.default(
            wss_url=WS_PUBLIC_STREAM_URL,
            on_connect=on_connect_bytes,
        )
        async with WsSingle(ws_config) as ws:
            async for msg in ws:
                try:
                    decoded_msg = json_decoder.decode(msg)
                    data = decoded_msg.data
                    symbol = decoded_msg.topic.split(".")[1]
                    exch_time_ns = (
                        decoded_msg.ts * 1_000_000 if decoded_msg.ts else None
                    )
                    ticker_msg = data.to_ticker_msg(
                        venue=self.venue,
                        instrument_collection=self.instrument_collection,
                        symbol_override=symbol,
                        exch_time_ns=exch_time_ns,
                    )
                    self.broadcast(ticker_msg)
                except Exception as e:
                    self.logger.error(
                        f"Failed to decode ticker message from {self.venue}; {e}"
                    )

    async def stream_orderbook(self, instruments: list[Instrument]):
        """Stream orderbook updates for instruments.

        Args:
            instruments: Instruments to subscribe to.
        """
        on_connect: dict[str, str | list[str]] = {"op": "subscribe", "args": []}

        args = cast(list[str], on_connect["args"])
        for instrument in instruments:
            symbol = self.instrument_to_symbol(instrument)
            args.append(f"orderbook.1.{symbol}")
            args.append(f"orderbook.500.{symbol}")

        on_connect_bytes = [msgspec.json.encode(on_connect)]
        json_decoder = msgspec.json.Decoder(BybitPublicMsg[BybitOrderbookMsg])
        ws_config = WsConnectionConfig.default(
            wss_url=WS_PUBLIC_STREAM_URL,
            on_connect=on_connect_bytes,
        )
        async with WsSingle(ws_config) as ws:
            async for msg in ws:
                try:
                    decoded_msg = json_decoder.decode(msg)
                    topic_parts = decoded_msg.topic.split(".")
                    _, n_levels, symbol = topic_parts[0], topic_parts[1], topic_parts[2]
                    is_bbo = int(n_levels) == 1
                    exch_time_ns = (
                        decoded_msg.ts * 1_000_000 if decoded_msg.ts else None
                    )
                    orderbook_msg = decoded_msg.data.to_orderbook_msg(
                        venue=self.venue,
                        instrument_collection=self.instrument_collection,
                        is_bbo=is_bbo,
                        symbol_override=symbol,
                        is_snapshot=decoded_msg.type == "snapshot",
                        exch_time_ns=exch_time_ns,
                    )
                    self.broadcast(orderbook_msg)
                except Exception as e:
                    self.logger.error(
                        f"Failed to decode orderbook message from {self.venue}; {e}"
                    )

    async def stream_top_of_orderbook(self, instruments: list[Instrument]):
        """Stream top-of-book updates for instruments.

        Args:
            instruments: Instruments to subscribe to.
        """
        await self.stream_orderbook(instruments)

    async def stream_full_orderbook(self, instruments: list[Instrument]):
        """Stream full orderbook updates for instruments.

        Args:
            instruments: Instruments to subscribe to.
        """
        await self.stream_orderbook(instruments)

    async def stream_trades(self, instruments: list[Instrument]):
        """Stream trade data from Bybit public websocket.

        Args:
            instruments: Instruments to subscribe to.
        """
        on_connect: dict[str, str | list[str]] = {"op": "subscribe", "args": []}

        symbol_to_seq_cache: SimpleCache[str, int] = SimpleCache()

        args = cast(list[str], on_connect["args"])
        for instrument in instruments:
            symbol = self.instrument_to_symbol(instrument)
            args.append(f"publicTrade.{symbol}")

        on_connect_bytes = [msgspec.json.encode(on_connect)]
        decoder = msgspec.json.Decoder(BybitTradePublicMsg)

        ws_config = WsConnectionConfig.default(
            wss_url=WS_PUBLIC_STREAM_URL,
            on_connect=on_connect_bytes,
        )
        async with WsSingle(ws_config) as ws:
            async for msg in ws:
                try:
                    decoded_msg = decoder.decode(msg)
                    symbol = decoded_msg.topic.split(".")[1]
                    trade_msg = decoded_msg.to_trade_msg(
                        venue=self.venue,
                        instrument_collection=self.instrument_collection,
                        symbol_to_seq_cache=symbol_to_seq_cache,
                        symbol_override=symbol,
                    )
                    if trade_msg:
                        self.broadcast(trade_msg)

                except Exception as e:
                    self.logger.error(
                        f"Failed to decode trade message from {self.venue}; {e}"
                    )

    async def run(
        self,
        instruments: list[Instrument],
        stream_types: set[MarketDataStreamType] = ALL_MARKET_DATA_STREAM_TYPES,
    ):
        """Run the Bybit market data streams.

        Args:
            instruments: Instruments to stream data for.
            stream_types: Market data stream types to enable.
        """
        self._instruments = instruments
        tasks: list[asyncio.Task] = []

        if MarketDataStreamType.TICKER in stream_types:
            tasks.append(asyncio.create_task(self.stream_ticker(instruments)))
        if (
            MarketDataStreamType.TOP_OF_ORDERBOOK in stream_types
            or MarketDataStreamType.FULL_ORDERBOOK in stream_types
        ):
            tasks.append(asyncio.create_task(self.stream_orderbook(instruments)))
        if MarketDataStreamType.TRADES in stream_types:
            tasks.append(asyncio.create_task(self.stream_trades(instruments)))
        tasks.append(
            asyncio.create_task(self.broadcast_heartbeat(MarketDataStreamType.TICKER))
        )

        await asyncio.gather(*tasks)

    # Removed old processing helpers; streaming handlers build messages directly
