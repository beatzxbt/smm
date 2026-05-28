"""OKX Exchange implementation for SWAP (perpetual) trading.

Implements the Exchange interface for OKX V5 API, handling order operations
via WebSocket and market/account queries via HTTP REST API.
"""

from __future__ import annotations

import asyncio
from typing import cast

import msgspec

from framework.base.common import (
    Asset,
    ClientOrderId,
    Instrument,
    InstrumentCollection,
    InstrumentType,
    OrderId,
    Symbol,
    Venue,
)
from framework.base.schema import Moments, MessageId
from framework.base.stream.models import Execution, Trade
from framework.base.tools import EnumMap
from framework.base.trading.client import HttpMethod
from framework.base.trading.exchange import Exchange
from framework.base.trading.models import (
    AccountResponse,
    AmendOrder,
    AmendOrderResponse,
    CancelAllOrders,
    CancelAllOrdersResponse,
    CancelOrder,
    CancelOrderResponse,
    ClientResponse,
    CreateOrder,
    CreateOrderResponse,
    ExecutionResponse,
    InstrumentInfoResponse,
    Order,
    OrderTimeInForce,
    OrderbookLevel,
    OrderbookResponse,
    OrdersResponse,
    PositionResponse,
    TickerResponse,
    TradesResponse,
    is_success,
)
from framework.okx.trading.client import OkxHttpClient, OkxWsClient
from framework.okx.trading.models import (
    OkxWsOrderResult,
    OkxHttpInstrument,
    OkxHttpTicker,
    OkxHttpOrderbook,
    OkxHttpOrderbookLevel,
    OkxHttpTrade,
    OkxHttpOrder,
    OkxHttpPosition,
    OkxHttpFill,
    OkxHttpAccount,
    OkxHttpBatchCancelResult,
)
from mm_toolbox.logging.standard import Logger
from mm_toolbox.time import time_ns

ENDPOINT_GET_INSTRUMENTS = "/api/v5/public/instruments"
ENDPOINT_GET_TICKER = "/api/v5/market/ticker"
ENDPOINT_GET_ORDERBOOK = "/api/v5/market/books"
ENDPOINT_GET_TRADES = "/api/v5/market/trades"
ENDPOINT_GET_ACCOUNT = "/api/v5/account/balance"
ENDPOINT_GET_POSITIONS = "/api/v5/account/positions"
ENDPOINT_GET_ORDERS = "/api/v5/trade/orders-pending"
ENDPOINT_GET_FILLS = "/api/v5/trade/fills"
ENDPOINT_BATCH_CANCEL = "/api/v5/trade/cancel-batch-orders"


class OkxExchange(Exchange):
    """Exchange implementation for OKX V5 API.

    Handles SWAP (perpetual) instruments with cross margin and net position mode.
    Uses WebSocket for order operations and HTTP REST for queries.

    Attributes:
        venue (Venue): OKX venue identifier.
        logger (Logger): Logger for status and error output.
        load_secrets (bool): Whether secrets are loaded for authenticated calls.
        http_client (OkxHttpClient): HTTP client for REST API.
        ws_client (OkxWsClient): WebSocket client for trading operations.
    """

    def __init__(self, logger: Logger, load_secrets: bool) -> None:
        """Initialize OKX exchange with clients and configuration.

        Args:
            logger (Logger): Logger instance for status and error output.
            load_secrets (bool): Whether to load API secrets from environment.
        """
        super().__init__(
            venue=Venue.OKX,
            logger=logger,
            load_secrets=load_secrets,
            http_client=OkxHttpClient(
                logger=logger,
                load_secrets=load_secrets,
            ),
            ws_client=OkxWsClient(
                logger=logger,
                load_secrets=load_secrets,
            ),
        )

        self._tif_map = EnumMap(
            enum_class=OrderTimeInForce,
            mapping={
                OrderTimeInForce.GTC: "normal",
                OrderTimeInForce.IOC: "ioc",
                OrderTimeInForce.FOK: "fok",
                OrderTimeInForce.PO: "post_only",
            },
        )

    def instrument_to_symbol(self, instrument: Instrument) -> str:
        """Convert Instrument to OKX symbol format.

        Args:
            instrument (Instrument): Instrument to convert.

        Returns:
            str: OKX symbol in format {BASE}-{QUOTE}-SWAP.
        """
        return f"{instrument.base}-{instrument.quote}-SWAP".upper()

    async def get_instrument_collection(self) -> ClientResponse[InstrumentCollection]:
        """Get all SWAP instruments from OKX.

        Returns:
            ClientResponse[InstrumentCollection]: Collection of available instruments.
        """
        response = await self.get_instrument_info([])

        if not is_success(response):
            return self.make_failure(
                meta=response.meta,
                err_no=response.err_no,
                err_msg=response.err_msg,
            )

        return self.make_success(
            meta=response.meta,
            data=InstrumentCollection(
                instruments=[info.instrument for info in response.data]
            ),
        )

    async def create_order(
        self, create_order: CreateOrder
    ) -> ClientResponse[CreateOrderResponse]:
        """Create an order via WebSocket.

        Args:
            create_order (CreateOrder): Order creation parameters.

        Returns:
            ClientResponse[CreateOrderResponse]: Response with order ID.
        """
        self.ensure_secrets_loaded()
        self.ensure_running(ws_only=True)

        # Determine order type
        ord_type = self._tif_map.enum_to_str(create_order.tif)
        if not create_order.is_maker:
            ord_type = "market"

        params: dict[str, str | int | float] = {
            "instId": self.instrument_to_symbol(create_order.instrument),
            "tdMode": "cross",
            "side": "buy" if create_order.is_buy else "sell",
            "ordType": ord_type,
            "sz": str(create_order.size),
        }

        if create_order.client_order_id:
            params["clOrdId"] = create_order.client_order_id
        if create_order.is_maker and create_order.price is not None:
            params["px"] = str(create_order.price)
        if create_order.reduce_only:
            params["reduceOnly"] = "true"

        payload = {
            "op": "order",
            "args": [params],
        }

        response = await self.ws_client.submit(
            data=payload, decoder=msgspec.json.Decoder(list[OkxWsOrderResult])
        )

        if not is_success(response):
            return self.make_failure(
                meta=response.meta,
                err_no=response.err_no,
                err_msg=response.err_msg,
            )

        results = cast(list[OkxWsOrderResult], response.data)
        if not results:
            return self.make_failure(
                meta=response.meta,
                err_no=1,
                err_msg="Empty response from OKX",
            )

        result = results[0]
        moments = Moments()
        resp_id = MessageId(recv_time_ns=moments.recv_time_ns)
        base_resp = CreateOrderResponse(
            id=resp_id,
            origin_id=create_order.origin_id or create_order.id,
            moments=moments,
            instrument=create_order.instrument,
            order_id=OrderId(str(result.ord_id)),
            client_order_id=ClientOrderId(str(result.cl_ord_id))
            if result.cl_ord_id
            else None,
        )
        return self.make_success(data=base_resp, meta=response.meta)

    async def amend_order(
        self, amend_order: AmendOrder
    ) -> ClientResponse[AmendOrderResponse]:
        """Amend an existing order via WebSocket.

        Args:
            amend_order (AmendOrder): Order amendment parameters.

        Returns:
            ClientResponse[AmendOrderResponse]: Response with order ID.
        """
        self.ensure_secrets_loaded()
        self.ensure_running(ws_only=True)

        params: dict[str, str] = {
            "instId": self.instrument_to_symbol(amend_order.instrument),
        }

        if amend_order.order_id:
            params["ordId"] = amend_order.order_id
        if amend_order.client_order_id:
            params["clOrdId"] = amend_order.client_order_id

        params["newSz"] = str(amend_order.size)
        if amend_order.price is not None:
            params["newPx"] = str(amend_order.price)

        payload = {
            "op": "amend-order",
            "args": [params],
        }

        response = await self.ws_client.submit(
            data=payload, decoder=msgspec.json.Decoder(list[OkxWsOrderResult])
        )

        if not is_success(response):
            return self.make_failure(
                meta=response.meta,
                err_no=response.err_no,
                err_msg=response.err_msg,
            )

        results = cast(list[OkxWsOrderResult], response.data)
        if not results:
            return self.make_failure(
                meta=response.meta,
                err_no=1,
                err_msg="Empty response from OKX",
            )

        result = results[0]
        moments = Moments()
        resp_id = MessageId(recv_time_ns=moments.recv_time_ns)
        base_resp = AmendOrderResponse(
            id=resp_id,
            origin_id=amend_order.origin_id or amend_order.id,
            moments=moments,
            instrument=amend_order.instrument,
            order_id=OrderId(str(result.ord_id)),
            client_order_id=ClientOrderId(str(result.cl_ord_id))
            if result.cl_ord_id
            else None,
        )
        return self.make_success(data=base_resp, meta=response.meta)

    async def cancel_order(
        self, cancel_order: CancelOrder
    ) -> ClientResponse[CancelOrderResponse]:
        """Cancel a single order via WebSocket.

        Args:
            cancel_order (CancelOrder): Order cancellation parameters.

        Returns:
            ClientResponse[CancelOrderResponse]: Response with order ID.
        """
        self.ensure_secrets_loaded()
        self.ensure_running(ws_only=True)

        params: dict[str, str] = {
            "instId": self.instrument_to_symbol(cancel_order.instrument),
        }

        if cancel_order.order_id:
            params["ordId"] = cancel_order.order_id
        if cancel_order.client_order_id:
            params["clOrdId"] = cancel_order.client_order_id

        payload = {
            "op": "cancel-order",
            "args": [params],
        }

        response = await self.ws_client.submit(
            data=payload, decoder=msgspec.json.Decoder(list[OkxWsOrderResult])
        )

        if not is_success(response):
            return self.make_failure(
                meta=response.meta,
                err_no=response.err_no,
                err_msg=response.err_msg,
            )

        results = cast(list[OkxWsOrderResult], response.data)
        if not results:
            return self.make_failure(
                meta=response.meta,
                err_no=1,
                err_msg="Empty response from OKX",
            )

        result = results[0]
        moments = Moments()
        resp_id = MessageId(recv_time_ns=moments.recv_time_ns)
        base_resp = CancelOrderResponse(
            id=resp_id,
            origin_id=cancel_order.origin_id or cancel_order.id,
            moments=moments,
            instrument=cancel_order.instrument,
            order_id=OrderId(str(result.ord_id)),
            client_order_id=ClientOrderId(str(result.cl_ord_id))
            if result.cl_ord_id
            else None,
        )
        return self.make_success(data=base_resp, meta=response.meta)

    async def cancel_all_orders(
        self, cancel_all_orders: CancelAllOrders
    ) -> ClientResponse[CancelAllOrdersResponse]:
        """Cancel all orders for an instrument via HTTP REST.

        Args:
            cancel_all_orders (CancelAllOrders): Cancellation scope parameters.

        Returns:
            ClientResponse[CancelAllOrdersResponse]: Response confirmation.
        """
        self.ensure_secrets_loaded()
        self.ensure_running(http_only=True)
        started_ns = time_ns()

        # Get pending orders first
        orders_response = await self.get_orders([cancel_all_orders.instrument])
        if not is_success(orders_response):
            return self.make_failure(
                meta=self.make_meta(
                    operation=ENDPOINT_BATCH_CANCEL,
                    started_ns=started_ns,
                    finished_ns=time_ns(),
                ),
                err_no=orders_response.err_no,
                err_msg=orders_response.err_msg,
            )
        if not orders_response.data:
            return self.make_failure(
                meta=self.make_meta(
                    operation=ENDPOINT_BATCH_CANCEL,
                    started_ns=started_ns,
                    finished_ns=time_ns(),
                ),
                err_no=1,
                err_msg="Empty orders response from OKX",
            )

        orders = orders_response.data[0].orders
        if not orders:
            # No orders to cancel
            moments = Moments()
            resp_id = MessageId(recv_time_ns=moments.recv_time_ns)
            base_resp = CancelAllOrdersResponse(
                id=resp_id,
                origin_id=cancel_all_orders.origin_id or cancel_all_orders.id,
                moments=moments,
                instrument=cancel_all_orders.instrument,
                order_ids=(),
                client_order_ids=(),
            )
            return self.make_success(
                data=base_resp,
                meta=self.make_meta(
                    operation=ENDPOINT_BATCH_CANCEL,
                    started_ns=started_ns,
                    finished_ns=time_ns(),
                ),
            )

        # Build batch cancel request
        cancel_args = []
        for order in orders:
            cancel_args.append(
                {
                    "instId": self.instrument_to_symbol(cancel_all_orders.instrument),
                    "ordId": order.order_id,
                }
            )

        decoder = msgspec.json.Decoder(list[OkxHttpBatchCancelResult])
        response = await self.http_client.request(
            method=HttpMethod.POST,
            endpoint=ENDPOINT_BATCH_CANCEL,
            params={},
            data=cancel_args,  # type: ignore[arg-type]
            sign=True,
            decoder=decoder,
        )

        if not is_success(response):
            return self.make_failure(
                meta=self.make_meta(
                    operation=ENDPOINT_BATCH_CANCEL,
                    started_ns=started_ns,
                    finished_ns=time_ns(),
                    status_code=response.meta.status_code,
                ),
                err_no=response.err_no,
                err_msg=response.err_msg,
            )

        cancelled_ids = tuple(order.order_id for order in orders)
        moments = Moments()
        resp_id = MessageId(recv_time_ns=moments.recv_time_ns)
        base_resp = CancelAllOrdersResponse(
            id=resp_id,
            origin_id=cancel_all_orders.origin_id or cancel_all_orders.id,
            moments=moments,
            instrument=cancel_all_orders.instrument,
            order_ids=cancelled_ids,
        )
        return self.make_success(
            data=base_resp,
            meta=self.make_meta(
                operation=ENDPOINT_BATCH_CANCEL,
                started_ns=started_ns,
                finished_ns=time_ns(),
                status_code=response.meta.status_code,
            ),
        )

    async def get_trades(
        self, instruments: list[Instrument]
    ) -> ClientResponse[list[TradesResponse]]:
        """Fetch recent public trades for instruments via HTTP REST.

        Args:
            instruments (list[Instrument]): Instruments to fetch trades for.

        Returns:
            ClientResponse[list[TradesResponse]]: Trade history for each instrument.
        """
        started_ns = time_ns()

        async def fetch_trades(instrument: Instrument) -> TradesResponse:
            params = {
                "instId": self.instrument_to_symbol(instrument),
                "limit": "100",
            }
            decoder = msgspec.json.Decoder(list[OkxHttpTrade])
            response = await self.http_client.request(
                method=HttpMethod.GET,
                endpoint=ENDPOINT_GET_TRADES,
                params=params,
                data={},
                sign=False,
                decoder=decoder,
            )
            if not is_success(response):
                raise RuntimeError(response.err_msg)

            items = cast(list[OkxHttpTrade], response.data)
            trades = [
                Trade(
                    time_ms=int(t.ts),
                    price=float(t.px),
                    is_buy=(t.side == "buy"),
                    size=float(t.sz),
                )
                for t in items
            ]
            moments = Moments()
            response_id = MessageId(recv_time_ns=moments.recv_time_ns)
            return TradesResponse(
                id=response_id,
                origin_id=response_id,
                moments=moments,
                instrument=instrument,
                trades=tuple(trades),
            )

        try:
            results = await asyncio.gather(
                *(fetch_trades(inst) for inst in instruments)
            )
            return self.make_success(
                data=results,
                meta=self.make_meta(
                    operation=ENDPOINT_GET_TRADES,
                    started_ns=started_ns,
                    finished_ns=time_ns(),
                ),
            )
        except Exception as e:
            return self.make_failure(
                meta=self.make_meta(
                    operation=ENDPOINT_GET_TRADES,
                    started_ns=started_ns,
                    finished_ns=time_ns(),
                ),
                err_no=1,
                err_msg=str(e),
            )

    async def get_orderbook(
        self, instruments: list[Instrument]
    ) -> ClientResponse[list[OrderbookResponse]]:
        """Fetch orderbook snapshots for instruments via HTTP REST.

        Args:
            instruments (list[Instrument]): Instruments to fetch orderbooks for.

        Returns:
            ClientResponse[list[OrderbookResponse]]: Orderbook for each instrument.
        """
        started_ns = time_ns()

        async def fetch_orderbook(instrument: Instrument) -> OrderbookResponse:
            params = {
                "instId": self.instrument_to_symbol(instrument),
                "sz": "200",
            }
            decoder = msgspec.json.Decoder(list[OkxHttpOrderbook])
            response = await self.http_client.request(
                method=HttpMethod.GET,
                endpoint=ENDPOINT_GET_ORDERBOOK,
                params=params,
                data={},
                sign=False,
                decoder=decoder,
            )
            if not is_success(response):
                raise RuntimeError(response.err_msg)

            items = cast(list[OkxHttpOrderbook], response.data)
            if not items:
                raise RuntimeError("Empty orderbook response")

            book = items[0]
            bids: list[OkxHttpOrderbookLevel] = book.bids
            asks: list[OkxHttpOrderbookLevel] = book.asks
            bid_lvls = tuple(
                sorted(
                    (
                        OrderbookLevel(price=float(level.price), size=float(level.size))
                        for level in bids
                    ),
                    key=lambda x: x.price,
                )
            )
            ask_lvls = tuple(
                sorted(
                    (
                        OrderbookLevel(price=float(level.price), size=float(level.size))
                        for level in asks
                    ),
                    key=lambda x: x.price,
                )
            )

            moments = Moments()
            response_id = MessageId(recv_time_ns=moments.recv_time_ns)
            return OrderbookResponse(
                id=response_id,
                origin_id=response_id,
                moments=moments,
                instrument=instrument,
                bids=bid_lvls,
                asks=ask_lvls,
                is_bbo=False,
            )

        try:
            results = await asyncio.gather(
                *(fetch_orderbook(inst) for inst in instruments)
            )
            return self.make_success(
                data=results,
                meta=self.make_meta(
                    operation=ENDPOINT_GET_ORDERBOOK,
                    started_ns=started_ns,
                    finished_ns=time_ns(),
                ),
            )
        except Exception as e:
            return self.make_failure(
                meta=self.make_meta(
                    operation=ENDPOINT_GET_ORDERBOOK,
                    started_ns=started_ns,
                    finished_ns=time_ns(),
                ),
                err_no=1,
                err_msg=str(e),
            )

    async def get_ticker(
        self, instruments: list[Instrument]
    ) -> ClientResponse[list[TickerResponse]]:
        """Fetch ticker data for instruments via HTTP REST.

        Args:
            instruments (list[Instrument]): Instruments to fetch tickers for.

        Returns:
            ClientResponse[list[TickerResponse]]: Ticker data for each instrument.
        """
        started_ns = time_ns()

        async def fetch_ticker(instrument: Instrument) -> TickerResponse:
            params = {
                "instId": self.instrument_to_symbol(instrument),
            }
            decoder = msgspec.json.Decoder(list[OkxHttpTicker])
            response = await self.http_client.request(
                method=HttpMethod.GET,
                endpoint=ENDPOINT_GET_TICKER,
                params=params,
                data={},
                sign=False,
                decoder=decoder,
            )
            if not is_success(response):
                raise RuntimeError(response.err_msg)

            items = cast(list[OkxHttpTicker], response.data)
            if not items:
                raise RuntimeError("Empty ticker response")

            item = items[0]
            moments = Moments()
            response_id = MessageId(recv_time_ns=moments.recv_time_ns)
            return TickerResponse(
                id=response_id,
                origin_id=response_id,
                moments=moments,
                instrument=instrument,
                mark_price=float(item.mark_px),
                index_price=float(item.idx_px),
                funding_rate=float(item.funding_rate),
                next_funding_time_ms=int(item.next_funding_time),
                open_interest=float(item.open_interest) if item.open_interest else 0.0,
                avg_volume_24h=float(item.vol_24h) if item.vol_24h else 0.0,
                price_chg_24h=0.0,  # OKX doesn't provide 24h % change in ticker endpoint
            )

        try:
            results = await asyncio.gather(
                *(fetch_ticker(inst) for inst in instruments)
            )
            return self.make_success(
                data=results,
                meta=self.make_meta(
                    operation=ENDPOINT_GET_TICKER,
                    started_ns=started_ns,
                    finished_ns=time_ns(),
                ),
            )
        except Exception as e:
            return self.make_failure(
                meta=self.make_meta(
                    operation=ENDPOINT_GET_TICKER,
                    started_ns=started_ns,
                    finished_ns=time_ns(),
                ),
                err_no=1,
                err_msg=str(e),
            )

    async def get_instrument_info(
        self, instruments: list[Instrument]
    ) -> ClientResponse[list[InstrumentInfoResponse]]:
        """Fetch instrument metadata via HTTP REST.

        Args:
            instruments (list[Instrument]): Instruments to fetch info for (empty for all).

        Returns:
            ClientResponse[list[InstrumentInfoResponse]]: Metadata for each instrument.
        """
        started_ns = time_ns()
        decoder = msgspec.json.Decoder(list[OkxHttpInstrument])
        response = await self.http_client.request(
            method=HttpMethod.GET,
            endpoint=ENDPOINT_GET_INSTRUMENTS,
            params={"instType": "SWAP"},
            data={},
            sign=False,
            decoder=decoder,
        )

        if not is_success(response):
            return self.make_failure(
                meta=self.make_meta(
                    operation=ENDPOINT_GET_INSTRUMENTS,
                    started_ns=started_ns,
                    finished_ns=time_ns(),
                    status_code=response.meta.status_code,
                ),
                err_no=response.err_no,
                err_msg=response.err_msg,
            )

        items = cast(list[OkxHttpInstrument], response.data)

        results: list[InstrumentInfoResponse] = []
        for item in items:
            # Parse instId format: BTC-USDT-SWAP
            parts = item.inst_id.split("-")
            if len(parts) != 3 or parts[2] != "SWAP":
                continue

            base = parts[0]
            quote = parts[1]

            moments = Moments()
            response_id = MessageId(recv_time_ns=moments.recv_time_ns)
            info = InstrumentInfoResponse(
                id=response_id,
                origin_id=response_id,
                moments=moments,
                instrument=Instrument(
                    venue=self.venue,
                    base=Asset(base),
                    quote=Asset(quote),
                    symbol=Symbol(f"{base}{quote}".upper()),
                    code=0,
                    instrument_type=InstrumentType.PERPETUAL,
                    tick_size=float(item.tick_sz),
                    lot_size=float(item.lot_sz),
                ),
                tick_size=float(item.tick_sz),
                lot_size=float(item.lot_sz),
                max_taker_size=0.0,
                max_maker_size=0.0,
            )
            results.append(info)

        if instruments:
            wanted = {self.instrument_to_symbol(i) for i in instruments}
            results = [
                r for r in results if self.instrument_to_symbol(r.instrument) in wanted
            ]

        return self.make_success(
            data=results,
            meta=self.make_meta(
                operation=ENDPOINT_GET_INSTRUMENTS,
                started_ns=started_ns,
                finished_ns=time_ns(),
                status_code=response.meta.status_code,
            ),
        )

    async def get_orders(
        self, instruments: list[Instrument]
    ) -> ClientResponse[list[OrdersResponse]]:
        """Fetch pending orders for instruments via HTTP REST.

        Args:
            instruments (list[Instrument]): Instruments to fetch orders for.

        Returns:
            ClientResponse[list[OrdersResponse]]: Pending orders for each instrument.
        """
        self.ensure_secrets_loaded()
        started_ns = time_ns()

        async def fetch_orders(instrument: Instrument) -> OrdersResponse:
            params = {
                "instType": "SWAP",
                "instId": self.instrument_to_symbol(instrument),
            }
            decoder = msgspec.json.Decoder(list[OkxHttpOrder])
            response = await self.http_client.request(
                method=HttpMethod.GET,
                endpoint=ENDPOINT_GET_ORDERS,
                params=params,
                data={},
                sign=True,
                decoder=decoder,
            )
            if not is_success(response):
                raise RuntimeError(response.err_msg)

            items = cast(list[OkxHttpOrder], response.data)
            orders = []
            for it in items:
                # Map OKX order type to TIF
                if it.ord_type == "market":
                    tif = OrderTimeInForce.IOC
                elif it.ord_type == "post_only":
                    tif = OrderTimeInForce.PO
                elif it.ord_type == "fok":
                    tif = OrderTimeInForce.FOK
                elif it.ord_type == "ioc":
                    tif = OrderTimeInForce.IOC
                else:
                    tif = OrderTimeInForce.GTC

                order = Order(
                    create_time_ms=float(it.c_time),
                    order_id=OrderId(str(it.ord_id)),
                    price=float(it.px),
                    is_buy=(it.side == "buy"),
                    size=float(it.sz),
                    size_remaining=max(0.0, float(it.sz) - float(it.acc_fill_sz)),
                    tif=tif,
                    is_cancelled=(it.state in ["canceled", "rejected"]),
                    is_reduce_only=(it.reduce_only == "true"),
                    client_order_id=ClientOrderId(str(it.cl_ord_id))
                    if it.cl_ord_id
                    else None,
                )
                orders.append(order)

            moments = Moments()
            response_id = MessageId(recv_time_ns=moments.recv_time_ns)
            return OrdersResponse(
                id=response_id,
                origin_id=response_id,
                moments=moments,
                instrument=instrument,
                orders=tuple(orders),
            )

        try:
            results = await asyncio.gather(
                *(fetch_orders(inst) for inst in instruments)
            )
            return self.make_success(
                data=results,
                meta=self.make_meta(
                    operation=ENDPOINT_GET_ORDERS,
                    started_ns=started_ns,
                    finished_ns=time_ns(),
                ),
            )
        except Exception as e:
            return self.make_failure(
                meta=self.make_meta(
                    operation=ENDPOINT_GET_ORDERS,
                    started_ns=started_ns,
                    finished_ns=time_ns(),
                ),
                err_no=1,
                err_msg=str(e),
            )

    async def get_position(
        self, instruments: list[Instrument]
    ) -> ClientResponse[list[PositionResponse]]:
        """Fetch position data for instruments via HTTP REST.

        Args:
            instruments (list[Instrument]): Instruments to fetch positions for.

        Returns:
            ClientResponse[list[PositionResponse]]: Position for each instrument.
        """
        self.ensure_secrets_loaded()
        started_ns = time_ns()

        async def fetch_position(instrument: Instrument) -> PositionResponse:
            params = {
                "instType": "SWAP",
                "instId": self.instrument_to_symbol(instrument),
            }
            decoder = msgspec.json.Decoder(list[OkxHttpPosition])
            response = await self.http_client.request(
                method=HttpMethod.GET,
                endpoint=ENDPOINT_GET_POSITIONS,
                params=params,
                data={},
                sign=True,
                decoder=decoder,
            )
            if not is_success(response):
                raise RuntimeError(response.err_msg)

            items = cast(list[OkxHttpPosition], response.data)
            total_size = 0.0
            avg_px = 0.0

            for it in items:
                pos = float(it.pos)
                if pos != 0:
                    total_size = pos
                    avg_px = float(it.avg_px)
                    break

            moments = Moments()
            response_id = MessageId(recv_time_ns=moments.recv_time_ns)
            return PositionResponse(
                id=response_id,
                origin_id=response_id,
                moments=moments,
                instrument=instrument,
                price=avg_px,
                is_long=total_size > 0,
                size=abs(total_size),
            )

        try:
            results = await asyncio.gather(
                *(fetch_position(inst) for inst in instruments)
            )
            return self.make_success(
                data=results,
                meta=self.make_meta(
                    operation=ENDPOINT_GET_POSITIONS,
                    started_ns=started_ns,
                    finished_ns=time_ns(),
                ),
            )
        except Exception as e:
            return self.make_failure(
                meta=self.make_meta(
                    operation=ENDPOINT_GET_POSITIONS,
                    started_ns=started_ns,
                    finished_ns=time_ns(),
                ),
                err_no=1,
                err_msg=str(e),
            )

    async def get_executions(
        self, instruments: list[Instrument]
    ) -> ClientResponse[list[ExecutionResponse]]:
        """Fetch executions (fills) for instruments via HTTP REST.

        Args:
            instruments (list[Instrument]): Instruments to fetch executions for.

        Returns:
            ClientResponse[list[ExecutionResponse]]: Executions for each instrument.
        """
        self.ensure_secrets_loaded()
        started_ns = time_ns()

        async def fetch_exec(instrument: Instrument) -> ExecutionResponse:
            params = {
                "instType": "SWAP",
                "instId": self.instrument_to_symbol(instrument),
                "limit": "100",
            }
            decoder = msgspec.json.Decoder(list[OkxHttpFill])
            response = await self.http_client.request(
                method=HttpMethod.GET,
                endpoint=ENDPOINT_GET_FILLS,
                params=params,
                data={},
                sign=True,
                decoder=decoder,
            )
            if not is_success(response):
                raise RuntimeError(response.err_msg)

            items = cast(list[OkxHttpFill], response.data)
            executions = [
                Execution(
                    exec_time_ms=float(it.ts),
                    order_id=OrderId(str(it.ord_id)),
                    price=float(it.fill_px),
                    is_buy=(it.side == "buy"),
                    size=float(it.fill_sz),
                    is_maker=(it.exec_type == "M"),
                    fee_paid=abs(float(it.fee)),
                    client_order_id=ClientOrderId(str(it.cl_ord_id))
                    if it.cl_ord_id
                    else None,
                )
                for it in items
            ]
            moments = Moments()
            response_id = MessageId(recv_time_ns=moments.recv_time_ns)
            return ExecutionResponse(
                id=response_id,
                origin_id=response_id,
                moments=moments,
                instrument=instrument,
                executions=tuple(executions),
            )

        try:
            results = await asyncio.gather(*(fetch_exec(inst) for inst in instruments))
            return self.make_success(
                data=results,
                meta=self.make_meta(
                    operation=ENDPOINT_GET_FILLS,
                    started_ns=started_ns,
                    finished_ns=time_ns(),
                ),
            )
        except Exception as e:
            return self.make_failure(
                meta=self.make_meta(
                    operation=ENDPOINT_GET_FILLS,
                    started_ns=started_ns,
                    finished_ns=time_ns(),
                ),
                err_no=1,
                err_msg=str(e),
            )

    async def get_account(self) -> ClientResponse[AccountResponse]:
        """Fetch account balance and margin data via HTTP REST.

        Returns:
            ClientResponse[AccountResponse]: Account balance and margin information.
        """
        self.ensure_secrets_loaded()
        started_ns = time_ns()
        decoder = msgspec.json.Decoder(list[OkxHttpAccount])
        response = await self.http_client.request(
            method=HttpMethod.GET,
            endpoint=ENDPOINT_GET_ACCOUNT,
            params={},
            data={},
            sign=True,
            decoder=decoder,
        )

        if not is_success(response):
            return self.make_failure(
                meta=self.make_meta(
                    operation=ENDPOINT_GET_ACCOUNT,
                    started_ns=started_ns,
                    finished_ns=time_ns(),
                    status_code=response.meta.status_code,
                ),
                err_no=response.err_no,
                err_msg=response.err_msg,
            )

        items = cast(list[OkxHttpAccount], response.data)
        if not items:
            return self.make_failure(
                meta=self.make_meta(
                    operation=ENDPOINT_GET_ACCOUNT,
                    started_ns=started_ns,
                    finished_ns=time_ns(),
                    status_code=response.meta.status_code,
                ),
                err_no=1,
                err_msg="Empty account response",
            )

        item = items[0]

        # Aggregate across all currencies (typically USDT for SWAP)
        total_equity = 0.0
        total_im = 0.0
        total_upl = 0.0

        for detail in item.details:
            total_equity += float(detail.eq)
            total_im += float(detail.frozen_bal)
            total_upl += float(detail.upl)

        moments = Moments()
        response_id = MessageId(recv_time_ns=moments.recv_time_ns)
        acc = AccountResponse(
            id=response_id,
            origin_id=response_id,
            moments=moments,
            instrument=Instrument.empty_with(venue=self.venue),
            balance=total_equity,
            initial_margin=total_im,
            maintenance_margin=0.0,  # OKX doesn't provide mmr in balance endpoint details
            unrealized_pnl=total_upl,
        )
        return self.make_success(
            data=acc,
            meta=self.make_meta(
                operation=ENDPOINT_GET_ACCOUNT,
                started_ns=started_ns,
                finished_ns=time_ns(),
                status_code=response.meta.status_code,
            ),
        )
