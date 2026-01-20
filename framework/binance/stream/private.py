"""Private data stream implementation for Binance futures.

Usage: instantiate BinancePrivateDataStream and call run() with instruments.
Components: listen-key auth, message routing, and heartbeats.
"""

from __future__ import annotations

import asyncio
from typing import cast

import msgspec

from framework.base.common import Instrument, InstrumentCollection, Venue
from framework.base.stream.private import PrivateDataStream, PrivateDataStreamType
from framework.base.stream.models import Msg
from mm_toolbox.logging.standard import Logger
from mm_toolbox.websocket import WsConnectionConfig, WsSingle
from framework.binance.stream.structs import (
    AccountUpdateStreamUpdate,
    ExecutionReportStreamUpdate,
    OrderUpdateStreamUpdate,
    PositionUpdateStreamUpdate,
)

# Type imports
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from framework.binance.trading.exchange import BinanceExchange

WSS_USDM_FUTURES_PRIVATE_BASE = "wss://fstream.binance.com/ws"
WSS_COINM_FUTURES_PRIVATE_BASE = "wss://dstream.binance.com/ws"


class BinancePrivateDataStream(PrivateDataStream):
    """Private stream handler for Binance futures data.

    Args:
        exchange_client (BinanceExchange): Exchange client for auth and REST calls.
        logger (Logger): Logger instance for stream logs.
        consumer_queues (list[asyncio.Queue[Msg]]): Queues to broadcast messages to.
    """

    def __init__(
        self,
        exchange_client: "BinanceExchange",
        logger: Logger,
        consumer_queues: list[asyncio.Queue[Msg]],
    ) -> None:
        """Initialize the Binance private data stream.

        Args:
            exchange_client (BinanceExchange): Exchange client for auth and REST calls.
            logger (Logger): Logger instance for stream logs.
            consumer_queues (list[asyncio.Queue[Msg]]): Queues to broadcast messages to.

        Returns:
            None.
        """
        from framework.binance.trading.client import BinanceHttpClient

        cast(BinanceHttpClient, exchange_client.http_client)
        super().__init__(
            venue=exchange_client.venue,
            logger=logger,
            consumer_queues=consumer_queues,
        )
        self.exchange_client = exchange_client
        self.base_wss_url = (
            WSS_USDM_FUTURES_PRIVATE_BASE
            if self.venue == Venue.BINANCE_USDM
            else WSS_COINM_FUTURES_PRIVATE_BASE
        )

        self._symbol_map_cache: dict[str, Instrument] = {}

        # Listen key for authenticated websocket connection
        self.listen_key: str | None = None

    def populate_instrument_collection(self, collection: InstrumentCollection) -> None:
        """Populate the instrument collection with tracked instruments.

        Args:
            collection (InstrumentCollection): Empty collection to populate.

        Returns:
            None.
        """
        for instrument in self._instruments:
            collection.add(instrument)

    async def _get_listen_key(self) -> str:
        """Get a listen key from the Binance REST API.

        Returns:
            str: Listen key for the authenticated websocket connection.

        Raises:
            Exception: If the listen key request fails.
        """
        response = await self.exchange_client.get_listen_key()

        if not response.is_successful:
            raise Exception(f"Failed to get listen key; {response.err_msg}")

        return str(response.data)

    def instrument_to_symbol(self, instrument: Instrument) -> str:
        """Convert an instrument to the Binance symbol string.

        Args:
            instrument (Instrument): Instrument to convert.

        Returns:
            str: Binance symbol string.
        """
        return f"{instrument.base}{instrument.quote}".lower()

    def _get_symbol_map(self) -> dict[str, Instrument]:
        """Build a symbol map for decoder lookups.

        Returns:
            dict[str, Instrument]: Mapping of symbol string to instrument.
        """
        return {
            self.instrument_to_symbol(inst): inst
            for inst in self.instrument_collection.instruments
        }

    async def stream_order(self, instruments: list[Instrument]) -> None:
        """Process order data and broadcast to consumer queues.

        Args:
            instruments (list[Instrument]): Instruments to stream order data for.

        Returns:
            None.
        """
        # This will be called as a task from run() method
        # The websocket iteration is handled in the run() method
        pass

    async def stream_position(self, instruments: list[Instrument]) -> None:
        """Process position data and broadcast to consumer queues.

        Args:
            instruments (list[Instrument]): Instruments to stream positions for.

        Returns:
            None.
        """
        # This will be called as a task from run() method
        # The websocket iteration is handled in the run() method
        pass

    async def stream_execution(self, instruments: list[Instrument]) -> None:
        """Process execution data and broadcast to consumer queues.

        Args:
            instruments (list[Instrument]): Instruments to stream executions for.

        Returns:
            None.
        """
        # This will be called as a task from run() method
        # The websocket iteration is handled in the run() method
        pass

    async def stream_account(self) -> None:
        """Process account data and broadcast to consumer queues.

        Returns:
            None.
        """
        # This will be called as a task from run() method
        # The websocket iteration is handled in the run() method
        pass

    async def run(
        self, instruments: list[Instrument], stream_types: set[PrivateDataStreamType]
    ) -> None:
        """Run the Binance private data stream tasks.

        Args:
            instruments (list[Instrument]): Instruments to stream data for.
            stream_types (set[PrivateDataStreamType]): Stream types to enable.

        Returns:
            None.
        """
        self._instruments = instruments

        # Cache symbol map for decoders
        self._symbol_map_cache = self._get_symbol_map()

        # Get listenKey (requires REST API call)
        self.listen_key = await self._get_listen_key()
        wss_url = f"{self.base_wss_url}/{self.listen_key}"

        # Create decoders for different message types
        order_decoder = msgspec.json.Decoder(OrderUpdateStreamUpdate)
        position_decoder = msgspec.json.Decoder(PositionUpdateStreamUpdate)
        execution_decoder = msgspec.json.Decoder(ExecutionReportStreamUpdate)
        account_decoder = msgspec.json.Decoder(AccountUpdateStreamUpdate)

        async def process_messages() -> None:
            """Process incoming websocket messages and route to handlers.

            Returns:
                None.
            """
            async for msg in ws:
                try:
                    raw_data = msgspec.json.decode(msg)
                    event_type = raw_data.get("e")

                    if event_type == "ORDER_TRADE_UPDATE":
                        # First broadcast execution (if any)
                        if (
                            PrivateDataStreamType.EXECUTION in stream_types
                            and raw_data.get("o", {}).get("X") == "TRADE"
                        ):
                            if data := execution_decoder.decode(msg):
                                execution_msg = data.to_execution_msg(
                                    venue=self.venue,
                                    symbol_map=self._symbol_map_cache,
                                )
                                if execution_msg:
                                    self.broadcast(execution_msg)

                        # Always broadcast order updates if requested
                        if PrivateDataStreamType.ORDER in stream_types:
                            if data := order_decoder.decode(msg):
                                order_msg = data.to_order_msg(
                                    venue=self.venue,
                                    symbol_map=self._symbol_map_cache,
                                )
                                if order_msg:
                                    self.broadcast(order_msg)

                    elif event_type == "ACCOUNT_UPDATE":
                        if PrivateDataStreamType.POSITION in stream_types:
                            if data := position_decoder.decode(msg):
                                position_msg = data.to_position_msg(
                                    venue=self.venue,
                                    symbol_map=self._symbol_map_cache,
                                )
                                if position_msg:
                                    self.broadcast(position_msg)

                        if PrivateDataStreamType.ACCOUNT in stream_types:
                            if data := account_decoder.decode(msg):
                                account_msg = data.to_account_msg(venue=self.venue)
                                if account_msg:
                                    self.broadcast(account_msg)

                except Exception as e:
                    self.logger.error(
                        f"Failed to decode private message from {self.venue}; {e}"
                    )

        ws_config = WsConnectionConfig.default(wss_url=wss_url, on_connect=[])
        async with WsSingle(ws_config) as ws:
            self.is_running = True

            tasks: list[asyncio.Task] = [
                asyncio.create_task(process_messages()),
                asyncio.create_task(
                    self.broadcast_heartbeat(PrivateDataStreamType.ORDER)
                ),
            ]

            await asyncio.gather(*tasks)


if __name__ == "__main__":

    async def main() -> None:
        """Run a manual sanity check for the private stream.

        Returns:
            None.
        """
        from framework.base.common import Instrument, InstrumentType, Venue
        from mm_toolbox.logging.standard import Logger
        from framework.binance.trading.exchange import BinanceExchange

        # Initialize exchange
        logger = Logger()
        exchange = BinanceExchange(
            logger=logger, load_secrets=True, is_usd_margined=True
        )

        # Create consumer queues
        consumer_queues = [asyncio.Queue() for _ in range(3)]

        # Initialize private stream
        stream = BinancePrivateDataStream(
            exchange_client=exchange,
            logger=logger,
            consumer_queues=consumer_queues,
        )

        # Test instruments
        instruments = [
            Instrument(
                venue=Venue.BINANCE_USDM,
                symbol="BTCUSDT",
                base="BTC",
                quote="USDT",
                code=0,
                instrument_type=InstrumentType.PERPETUAL,
            ),
            Instrument(
                venue=Venue.BINANCE_USDM,
                symbol="ETHUSDT",
                base="ETH",
                quote="USDT",
                code=0,
                instrument_type=InstrumentType.PERPETUAL,
            ),
        ]

        # Stream all private data types
        await stream.run(
            instruments=instruments,
            stream_types={
                PrivateDataStreamType.ORDER,
                PrivateDataStreamType.POSITION,
                PrivateDataStreamType.EXECUTION,
                PrivateDataStreamType.ACCOUNT,
            },
        )

    asyncio.run(main())
