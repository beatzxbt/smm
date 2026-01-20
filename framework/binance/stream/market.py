"""framework.binance.stream.market"""

from __future__ import annotations

import asyncio

import msgspec

from framework.base.common import (
    Instrument,
    InstrumentCollection,
    InstrumentType,
    Venue,
)
from framework.base.stream.market import MarketDataStream
from framework.base.stream.models import (
    ALL_MARKET_DATA_STREAM_TYPES,
    MarketDataStreamType,
    Msg,
)
from framework.base.tools import SimpleCache
from mm_toolbox.logging.standard import Logger
from mm_toolbox.websocket import WsConnectionConfig, WsSingle
from framework.binance.trading.exchange import BinanceExchange
from framework.binance.stream.structs import (
    BookTickerStreamUpdate,
    DiffBookDepthStreamUpdate,
    MarkPriceStreamUpdate,
    TradeStreamUpdate,
    OpenInterestInfo,
    TickerStats24h,
)


class BinanceMarketDataStream(MarketDataStream):
    """Binance public market data stream implementation."""

    BASE_URLS = {
        Venue.BINANCE_USDM: "wss://fstream.binance.com/ws",
        Venue.BINANCE_COINM: "wss://dstream.binance.com/ws",
    }

    STREAM_URLS = {
        MarketDataStreamType.TOP_OF_ORDERBOOK: "{symbol}@bookTicker",
        MarketDataStreamType.FULL_ORDERBOOK: "{symbol}@depth@100ms",
        MarketDataStreamType.TRADES: "{symbol}@aggTrade",
        # Only provides partial data, the rest is updated internally
        # via polling the REST API and cached locally every second.
        MarketDataStreamType.TICKER: "{symbol}@markPrice@1s",
    }

    def __init__(
        self,
        logger: Logger,
        consumer_queues: list[asyncio.Queue[Msg]],
        is_usd_margined: bool,
    ):
        """Initialize the Binance market data stream.

        Args:
            logger: Logger instance for diagnostics.
            consumer_queues: Queues to broadcast messages to.
            is_usd_margined: True for USD-M, False for COIN-M.
        """
        super().__init__(
            venue=Venue.BINANCE_USDM if is_usd_margined else Venue.BINANCE_COINM,
            logger=logger,
            consumer_queues=consumer_queues,
        )

        self.base_wss_url = self.BASE_URLS[self.venue]

        self.instrument_to_open_interest_map: dict[Instrument, OpenInterestInfo] = {}
        self.instrument_to_ticker_stats_24h_map: dict[Instrument, TickerStats24h] = {}

        self.exchange_client = BinanceExchange(
            logger=logger,
            load_secrets=False,
            is_usd_margined=is_usd_margined,
        )

    def populate_instrument_collection(self, collection: InstrumentCollection) -> None:
        """Populate the instrument collection with tracked instruments.

        Args:
            collection: Empty collection to populate with instruments.
        """
        for instrument in self._instruments:
            collection.add(instrument)

    async def _update_open_interest_map(self, instruments: list[Instrument]):
        """Periodically poll REST API for open interest data and update cache.

        Args:
            instruments: Instruments to fetch open interest for.
        """
        while True:
            try:
                # Get open interests for all instruments
                response = await self.exchange_client.get_open_interest(instruments)
                if response.is_successful and response.data is not None:
                    for i, instrument in enumerate(instruments):
                        self.instrument_to_open_interest_map[instrument] = (
                            OpenInterestInfo(open_interest=response.data[i])
                        )

                await asyncio.sleep(10)  # Poll every 10 seconds
            except Exception as e:
                self.logger.warning(f"Failed to update open interest map; {e}")
                await asyncio.sleep(10)  # Wait longer on error

    async def _update_ticker_stats_24h_map(self, instruments: list[Instrument]):
        """Periodically poll REST API for 24h ticker stats and update cache.

        Args:
            instruments: Instruments to fetch ticker stats for.
        """
        while True:
            try:
                # Get ticker data for all instruments
                response = await self.exchange_client.get_ticker(instruments)
                if response.is_successful and response.data is not None:
                    for ticker_response in response.data:
                        self.instrument_to_ticker_stats_24h_map[
                            ticker_response.instrument
                        ] = TickerStats24h(
                            price_chg_24h_pct=ticker_response.price_chg_24h or 0.0,
                            avg_volume_24h=ticker_response.avg_volume_24h or 0.0,
                        )

                await asyncio.sleep(10)  # Poll every 10 seconds
            except Exception as e:
                self.logger.warning(f"Failed to update ticker stats 24h map; {e}")
                await asyncio.sleep(15)  # Wait longer on error

    async def stream_ticker(self, instruments: list[Instrument]):
        """Stream mark price updates for instruments.

        Args:
            instruments: Instruments to subscribe to.
        """
        wss_url = f"{self.base_wss_url}"
        for instrument in instruments:
            wss_url += f"/{self.STREAM_URLS[MarketDataStreamType.TICKER].format(symbol=instrument.symbol)}"

        decoder = msgspec.json.Decoder(MarkPriceStreamUpdate)

        # Start the OI/24h polling tasks before ticker stream starts
        oi_map_task = asyncio.create_task(self._update_open_interest_map(instruments))
        stats_24h_task = asyncio.create_task(
            self._update_ticker_stats_24h_map(instruments)
        )

        ws_config = WsConnectionConfig.default(wss_url=wss_url, on_connect=[])
        async with WsSingle(ws_config) as ws:
            async for msg in ws:
                try:
                    if data := decoder.decode(msg):
                        ticker_msg = data.to_ticker_msg(
                            venue=self.venue,
                            instrument_collection=self.instrument_collection,
                            instrument_to_open_interest_map=self.instrument_to_open_interest_map,
                            instrument_to_ticker_stats_24h_map=self.instrument_to_ticker_stats_24h_map,
                        )
                        self.broadcast(ticker_msg)
                except Exception as e:
                    self.logger.warning(
                        f"Failed to decode ticker message from {self.venue}; {e}"
                    )

        oi_map_task.cancel()
        stats_24h_task.cancel()

    async def stream_top_of_orderbook(self, instruments: list[Instrument]):
        """Stream best bid/ask updates for instruments.

        Args:
            instruments: Instruments to subscribe to.
        """
        wss_url = f"{self.base_wss_url}"
        for instrument in instruments:
            wss_url += f"/{self.STREAM_URLS[MarketDataStreamType.TOP_OF_ORDERBOOK].format(symbol=instrument.symbol)}"

        decoder = msgspec.json.Decoder(BookTickerStreamUpdate)

        ws_config = WsConnectionConfig.default(wss_url=wss_url, on_connect=[])
        async with WsSingle(ws_config) as ws:
            async for msg in ws:
                try:
                    if data := decoder.decode(msg):
                        orderbook_msg = data.to_orderbook_msg(
                            venue=self.venue,
                            instrument_collection=self.instrument_collection,
                        )
                        self.broadcast(orderbook_msg)
                except Exception as e:
                    self.logger.warning(
                        f"Failed to decode BBO message from {self.venue}; {e}"
                    )

    async def stream_full_orderbook(self, instruments: list[Instrument]):
        """Stream full depth updates for instruments.

        Args:
            instruments: Instruments to subscribe to.
        """
        wss_url = f"{self.base_wss_url}"
        for instrument in instruments:
            wss_url += f"/{self.STREAM_URLS[MarketDataStreamType.FULL_ORDERBOOK].format(symbol=instrument.symbol)}"

        decoder = msgspec.json.Decoder(DiffBookDepthStreamUpdate)

        ws_config = WsConnectionConfig.default(wss_url=wss_url, on_connect=[])
        async with WsSingle(ws_config) as ws:
            async for msg in ws:
                try:
                    if data := decoder.decode(msg):
                        orderbook_msg = data.to_orderbook_msg(
                            venue=self.venue,
                            instrument_collection=self.instrument_collection,
                        )
                        self.broadcast(orderbook_msg)
                except Exception as e:
                    self.logger.error(
                        f"Failed to decode full orderbook message from {self.venue}; {e}"
                    )

    async def stream_trades(self, instruments: list[Instrument]):
        """Stream aggregated trade updates for instruments.

        Args:
            instruments: Instruments to subscribe to.
        """
        wss_url = f"{self.base_wss_url}"
        for instrument in instruments:
            wss_url += f"/{self.STREAM_URLS[MarketDataStreamType.TRADES].format(symbol=instrument.symbol)}"

        symbol_to_seq_id_cache: SimpleCache[str, int] = SimpleCache()

        decoder = msgspec.json.Decoder(TradeStreamUpdate)

        ws_config = WsConnectionConfig.default(wss_url=wss_url, on_connect=[])
        async with WsSingle(ws_config) as ws:
            async for msg in ws:
                try:
                    if data := decoder.decode(msg):
                        if not symbol_to_seq_id_cache.is_higher(
                            data.symbol, data.trade_id
                        ):
                            continue

                        trade_msg = data.to_trade_msg(
                            venue=self.venue,
                            instrument_collection=self.instrument_collection,
                        )
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
        """Run the Binance market data streams.

        Args:
            instruments: Instruments to stream data for.
            stream_types: Market data stream types to enable.
        """
        self._instruments = instruments
        tasks: list[asyncio.Task] = []

        if MarketDataStreamType.TICKER in stream_types:
            tasks.append(asyncio.create_task(self.stream_ticker(instruments)))
        if MarketDataStreamType.TOP_OF_ORDERBOOK in stream_types:
            tasks.append(asyncio.create_task(self.stream_top_of_orderbook(instruments)))
        if MarketDataStreamType.FULL_ORDERBOOK in stream_types:
            tasks.append(asyncio.create_task(self.stream_full_orderbook(instruments)))
        if MarketDataStreamType.TRADES in stream_types:
            tasks.append(asyncio.create_task(self.stream_trades(instruments)))
        tasks.append(
            asyncio.create_task(self.broadcast_heartbeat(MarketDataStreamType.TICKER))
        )

        await asyncio.gather(*tasks)


if __name__ == "__main__":

    async def main():
        """Run a sample Binance market data stream."""
        consumer_queues = [asyncio.Queue() for _ in range(3)]
        stream = BinanceMarketDataStream(
            logger=Logger(),
            consumer_queues=consumer_queues,
            is_usd_margined=True,
        )
        await stream.run(
            instruments=[
                Instrument(
                    venue=Venue.BINANCE_USDM,
                    base="BTC",
                    quote="USDT",
                    symbol="BTCUSDT",
                    code=0,
                    instrument_type=InstrumentType.PERPETUAL,
                )
            ],
            stream_types={
                MarketDataStreamType.TOP_OF_ORDERBOOK,
                MarketDataStreamType.FULL_ORDERBOOK,
                MarketDataStreamType.TRADES,
            },
        )

    asyncio.run(main())
