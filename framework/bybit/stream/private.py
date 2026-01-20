"""Private data stream implementation for Bybit.

Usage: instantiate BybitPrivateDataStream and call run() with instruments.
Components: websocket auth, order/position/execution/account streams.
"""

from __future__ import annotations

import asyncio
from typing import Any

import aiohttp
import msgspec

from framework.base.common import (
    Instrument,
    InstrumentCollection,
    Venue,
)
from framework.base.stream.private import PrivateDataStream, PrivateDataStreamType
from framework.base.stream.models import (
    Execution,
    ExecutionMsg,
    Moments,
    Msg,
    Order,
    OrderMsg,
)
from mm_toolbox.logging.standard import Logger
from mm_toolbox.time import time_ns
from framework.base.trading.models import Secret
from framework.bybit.stream.structs import (
    BybitExecutionMsg,
    BybitOrderMsg,
    BybitPositionMsg,
    BybitPrivateMsg,
    BybitWalletMsg,
)

WS_PRIVATE_STREAM_URL = "wss://stream.bybit.com/v5/private"


class BybitPrivateDataStream(PrivateDataStream):
    """Private stream handler for Bybit authenticated data.

    Args:
        key (Secret): API key for authentication.
        secret (Secret): API secret for authentication.
        logger (Logger): Logger instance for stream logs.
        consumer_queues (list[asyncio.Queue[Msg]]): Queues to broadcast messages to.
    """

    def __init__(
        self,
        key: Secret,
        secret: Secret,
        logger: Logger,
        consumer_queues: list[asyncio.Queue[Msg]],
    ) -> None:
        """Initialize the Bybit private data stream.

        Args:
            key (Secret): API key for authentication.
            secret (Secret): API secret for authentication.
            logger (Logger): Logger instance for stream logs.
            consumer_queues (list[asyncio.Queue[Msg]]): Queues to broadcast messages to.

        Returns:
            None.
        """
        super().__init__(
            venue=Venue.BYBIT, logger=logger, consumer_queues=consumer_queues
        )
        self.key = key
        self.secret = secret

    def populate_instrument_collection(self, collection: InstrumentCollection) -> None:
        """Populate the instrument collection with tracked instruments.

        Args:
            collection (InstrumentCollection): Empty collection to populate.

        Returns:
            None.
        """
        for instrument in self._instruments:
            collection.add(instrument)

    def instrument_to_symbol(self, instrument: Instrument) -> str:
        """Convert an instrument to the exchange-specific symbol string.

        Args:
            instrument (Instrument): Instrument to convert.

        Returns:
            str: Exchange-specific symbol string.
        """
        return f"{instrument.base}{instrument.quote}".upper()

    async def stream_order(self, instruments: list[Instrument]) -> None:
        """Stream order updates and broadcast messages.

        Args:
            instruments (list[Instrument]): Instruments to stream orders for.

        Returns:
            None.
        """
        auth_url = "wss://stream.bybit.com/v5/private"

        decoder = msgspec.json.Decoder(BybitPrivateMsg[BybitOrderMsg])
        async with aiohttp.ClientSession() as session:
            async with session.ws_connect(auth_url) as ws:
                if not await self._authenticate_ws(ws):
                    raise RuntimeError("Bybit private stream auth failed (order)")
                sub_msg = {"op": "subscribe", "args": ["order"]}
                await ws.send_bytes(msgspec.json.encode(sub_msg))

                async for inc in ws:
                    if inc.type != aiohttp.WSMsgType.TEXT:
                        continue
                    try:
                        payload = msgspec.json.decode(inc.data)
                        if payload.get("topic") != "order":
                            continue
                        decoded_msg = decoder.decode(inc.data)
                        if not decoded_msg.data:
                            continue

                        orders: list[Order] = []
                        instrument: Instrument | None = None
                        for order_update in decoded_msg.data:
                            instrument = self.instrument_collection.get(
                                venue=self.venue, symbol=order_update.symbol
                            )
                            if not instrument:
                                continue
                            orders.append(order_update.to_order())
                        if orders and instrument:
                            self.broadcast(
                                OrderMsg(
                                    moments=Moments(
                                        exch_time_ns=decoded_msg.ts * 1_000_000,
                                        recv_time_ns=time_ns(),
                                    ),
                                    venue=self.venue,
                                    instrument=instrument,
                                    orders=orders,
                                )
                            )
                    except Exception as e:
                        self.logger.error(f"Order stream decode error; {e}")

    async def stream_position(self, instruments: list[Instrument]) -> None:
        """Stream position updates and broadcast messages.

        Args:
            instruments (list[Instrument]): Instruments to stream positions for.

        Returns:
            None.
        """
        auth_url = "wss://stream.bybit.com/v5/private"

        decoder = msgspec.json.Decoder(BybitPrivateMsg[BybitPositionMsg])
        async with aiohttp.ClientSession() as session:
            async with session.ws_connect(auth_url) as ws:
                if not await self._authenticate_ws(ws):
                    raise RuntimeError("Bybit private stream auth failed (position)")
                sub_msg = {"op": "subscribe", "args": ["position"]}
                await ws.send_bytes(msgspec.json.encode(sub_msg))

                async for inc in ws:
                    if inc.type != aiohttp.WSMsgType.TEXT:
                        continue
                    try:
                        payload = msgspec.json.decode(inc.data)
                        if payload.get("topic") != "position":
                            continue
                        decoded_msg = decoder.decode(inc.data)
                        for position_update in decoded_msg.data:
                            msg = position_update.to_position_msg(
                                venue=self.venue,
                                instrument_collection=self.instrument_collection,
                                exch_time_ns=decoded_msg.ts * 1_000_000,
                            )
                            if msg:
                                self.broadcast(msg)
                    except Exception as e:
                        self.logger.error(f"Position stream decode error; {e}")

    async def stream_execution(self, instruments: list[Instrument]) -> None:
        """Stream execution updates and broadcast messages.

        Args:
            instruments (list[Instrument]): Instruments to stream executions for.

        Returns:
            None.
        """
        auth_url = "wss://stream.bybit.com/v5/private"

        decoder = msgspec.json.Decoder(BybitPrivateMsg[BybitExecutionMsg])
        async with aiohttp.ClientSession() as session:
            async with session.ws_connect(auth_url) as ws:
                if not await self._authenticate_ws(ws):
                    raise RuntimeError("Bybit private stream auth failed (execution)")
                sub_msg = {"op": "subscribe", "args": ["execution"]}
                await ws.send_bytes(msgspec.json.encode(sub_msg))

                async for inc in ws:
                    if inc.type != aiohttp.WSMsgType.TEXT:
                        continue
                    try:
                        payload = msgspec.json.decode(inc.data)
                        if payload.get("topic") != "execution":
                            continue
                        decoded_msg = decoder.decode(inc.data)
                        if not decoded_msg.data:
                            continue

                        executions: list[Execution] = []
                        instrument: Instrument | None = None
                        for execution_update in decoded_msg.data:
                            instrument = self.instrument_collection.get(
                                venue=self.venue, symbol=execution_update.symbol
                            )
                            if not instrument:
                                continue
                            executions.append(execution_update.to_execution())
                        if executions and instrument:
                            self.broadcast(
                                ExecutionMsg(
                                    moments=Moments(
                                        exch_time_ns=decoded_msg.ts * 1_000_000,
                                        recv_time_ns=time_ns(),
                                    ),
                                    venue=self.venue,
                                    instrument=instrument,
                                    executions=executions,
                                )
                            )
                    except Exception as e:
                        self.logger.error(f"Execution stream decode error; {e}")

    async def stream_account(self) -> None:
        """Stream account updates and broadcast messages.

        Returns:
            None.
        """
        auth_url = "wss://stream.bybit.com/v5/private"

        decoder = msgspec.json.Decoder(BybitPrivateMsg[BybitWalletMsg])
        async with aiohttp.ClientSession() as session:
            async with session.ws_connect(auth_url) as ws:
                if not await self._authenticate_ws(ws):
                    raise RuntimeError("Bybit private stream auth failed (wallet)")
                sub_msg = {"op": "subscribe", "args": ["wallet"]}
                await ws.send_bytes(msgspec.json.encode(sub_msg))

                async for inc in ws:
                    if inc.type != aiohttp.WSMsgType.TEXT:
                        continue
                    try:
                        payload = msgspec.json.decode(inc.data)
                        if payload.get("topic") != "wallet":
                            continue
                        decoded_msg = decoder.decode(inc.data)
                        if not decoded_msg.data:
                            continue
                        self.broadcast(
                            decoded_msg.data[0].to_account_msg(
                                venue=self.venue,
                                exch_time_ns=decoded_msg.ts * 1_000_000,
                            )
                        )
                    except Exception as e:
                        self.logger.error(f"Wallet stream decode error; {e}")

    async def run(
        self, instruments: list[Instrument], stream_types: set[PrivateDataStreamType]
    ) -> None:
        """Run the Bybit private data stream tasks.

        Args:
            instruments (list[Instrument]): Instruments to stream data for.
            stream_types (set[PrivateDataStreamType]): Stream types to enable.

        Returns:
            None.
        """
        self._instruments = instruments
        self.is_running = True
        tasks: list[asyncio.Task[Any]] = []
        if PrivateDataStreamType.ORDER in stream_types:
            tasks.append(asyncio.create_task(self.stream_order(instruments)))
        if PrivateDataStreamType.POSITION in stream_types:
            tasks.append(asyncio.create_task(self.stream_position(instruments)))
        if PrivateDataStreamType.EXECUTION in stream_types:
            tasks.append(asyncio.create_task(self.stream_execution(instruments)))
        if PrivateDataStreamType.ACCOUNT in stream_types:
            tasks.append(asyncio.create_task(self.stream_account()))
        tasks.append(
            asyncio.create_task(self.broadcast_heartbeat(PrivateDataStreamType.ORDER))
        )

        await asyncio.gather(*tasks)

    async def _authenticate_ws(self, ws: aiohttp.ClientWebSocketResponse) -> bool:
        """Authenticate a websocket session with the Bybit private stream.

        Args:
            ws (aiohttp.ClientWebSocketResponse): Websocket connection to authenticate.

        Returns:
            bool: True if authentication succeeds, False otherwise.
        """
        try:
            expire = str(int((time_ns() / 1_000_000) + 60_000))
            import hashlib
            import hmac

            signature = hmac.new(
                key=self.secret.value.encode("utf-8"),
                msg=f"GET/realtime{expire}".encode("utf-8"),
                digestmod=hashlib.sha256,
            ).hexdigest()
            auth_msg = {"op": "auth", "args": [self.key.value, expire, signature]}
            await ws.send_bytes(msgspec.json.encode(auth_msg))
            resp = await ws.receive()
            if resp.type == aiohttp.WSMsgType.TEXT:
                data = msgspec.json.decode(resp.data)
                return data.get("retCode", 1) == 0
            return False
        except Exception as e:
            self.logger.error(f"WebSocket authentication error: {e}")
            return False
