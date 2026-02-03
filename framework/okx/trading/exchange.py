"""OKX Exchange implementation for SWAP (perpetual) trading.

Implements the Exchange interface for OKX V5 API, handling order operations
via WebSocket and market/account queries via HTTP REST API.
"""

from __future__ import annotations

import asyncio
from typing import cast

import msgspec

from framework.base.common import (
    Instrument,
    InstrumentCollection,
    InstrumentType,
    Venue,
)
from framework.base.stream.models import Execution, Moments, Trade
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
    ClientResponseFailure,
    ClientResponseSuccess,
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
)
from framework.okx.trading.client import OkxHttpClient, OkxWsClient
from mm_toolbox.logging.standard import Logger

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

        if not response.is_successful or response.data is None:
            return ClientResponseFailure(
                err_no=response.err_no,
                err_msg=response.err_msg,
            )

        return ClientResponseSuccess(
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
            data=payload, decoder=msgspec.json.Decoder(list)
        )

        if not response.is_successful:
            return ClientResponseFailure(
                is_successful=False, err_no=response.err_no, err_msg=response.err_msg
            )

        result_list = cast(list, response.data)
        if not result_list:
            return ClientResponseFailure(
                is_successful=False, err_no=1, err_msg="Empty response from OKX"
            )

        result = result_list[0]
        order_id = str(result.get("ordId", ""))
        cloid = result.get("clOrdId")

        base_resp = CreateOrderResponse(
            moments=None,  # type: ignore[arg-type]
            venue=self.venue,
            instrument=create_order.instrument,
            trigger=create_order,
            order_id=order_id,
            client_order_id=cloid,
        )
        return ClientResponseSuccess(is_successful=True, data=base_resp)

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
            data=payload, decoder=msgspec.json.Decoder(list)
        )

        if not response.is_successful:
            return ClientResponseFailure(
                is_successful=False, err_no=response.err_no, err_msg=response.err_msg
            )

        result_list = cast(list, response.data)
        if not result_list:
            return ClientResponseFailure(
                is_successful=False, err_no=1, err_msg="Empty response from OKX"
            )

        result = result_list[0]
        order_id = str(result.get("ordId", ""))
        cloid = result.get("clOrdId")

        base_resp = AmendOrderResponse(
            moments=None,  # type: ignore[arg-type]
            venue=self.venue,
            instrument=amend_order.instrument,
            trigger=amend_order,
            order_id=order_id,
            client_order_id=cloid,
        )
        return ClientResponseSuccess(is_successful=True, data=base_resp)

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
            data=payload, decoder=msgspec.json.Decoder(list)
        )

        if not response.is_successful:
            return ClientResponseFailure(
                is_successful=False, err_no=response.err_no, err_msg=response.err_msg
            )

        result_list = cast(list, response.data)
        if not result_list:
            return ClientResponseFailure(
                is_successful=False, err_no=1, err_msg="Empty response from OKX"
            )

        result = result_list[0]
        order_id = str(result.get("ordId", ""))
        cloid = result.get("clOrdId")

        base_resp = CancelOrderResponse(
            moments=None,  # type: ignore[arg-type]
            venue=self.venue,
            instrument=cancel_order.instrument,
            trigger=cancel_order,
            order_id=order_id,
            client_order_id=cloid,
        )
        return ClientResponseSuccess(is_successful=True, data=base_resp)

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

        # Get pending orders first
        orders_response = await self.get_orders([cancel_all_orders.instrument])
        if not orders_response.is_successful or not orders_response.data:
            return ClientResponseFailure(
                is_successful=False,
                err_no=orders_response.err_no,
                err_msg=orders_response.err_msg,
            )

        orders = orders_response.data[0].orders
        if not orders:
            # No orders to cancel
            base_resp = CancelAllOrdersResponse(
                moments=None,  # type: ignore[arg-type]
                venue=self.venue,
                instrument=cancel_all_orders.instrument,
                trigger=cancel_all_orders,
                order_ids=[],
                client_order_ids=[],
            )
            return ClientResponseSuccess(is_successful=True, data=base_resp)

        # Build batch cancel request
        cancel_args = []
        for order in orders:
            cancel_args.append(
                {
                    "instId": self.instrument_to_symbol(cancel_all_orders.instrument),
                    "ordId": order.order_id,
                }
            )

        decoder = msgspec.json.Decoder(list)
        response = await self.http_client.request(
            method=HttpMethod.POST,
            endpoint=ENDPOINT_BATCH_CANCEL,
            params={},
            data=cancel_args,  # type: ignore[arg-type]
            sign=True,
            decoder=decoder,
        )

        if not response.is_successful:
            return ClientResponseFailure(
                is_successful=False, err_no=response.err_no, err_msg=response.err_msg
            )

        cancelled_ids = [order.order_id for order in orders]
        base_resp = CancelAllOrdersResponse(
            moments=None,  # type: ignore[arg-type]
            venue=self.venue,
            instrument=cancel_all_orders.instrument,
            trigger=cancel_all_orders,
            order_ids=cancelled_ids,
        )
        return ClientResponseSuccess(is_successful=True, data=base_resp)

    async def get_trades(
        self, instruments: list[Instrument]
    ) -> ClientResponse[list[TradesResponse]]:
        """Fetch recent public trades for instruments via HTTP REST.

        Args:
            instruments (list[Instrument]): Instruments to fetch trades for.

        Returns:
            ClientResponse[list[TradesResponse]]: Trade history for each instrument.
        """

        async def fetch_trades(instrument: Instrument) -> TradesResponse:
            params = {
                "instId": self.instrument_to_symbol(instrument),
                "limit": "100",
            }
            decoder = msgspec.json.Decoder(list)
            response = await self.http_client.request(
                method=HttpMethod.GET,
                endpoint=ENDPOINT_GET_TRADES,
                params=params,
                data={},
                sign=False,
                decoder=decoder,
            )
            if not response.is_successful:
                raise RuntimeError(response.err_msg)

            items = cast(list, response.data)
            trades = [
                Trade(
                    time_ms=int(t.get("ts", 0)),
                    price=float(t.get("px", 0.0)),
                    is_buy=(t.get("side", "buy") == "buy"),
                    size=float(t.get("sz", 0.0)),
                )
                for t in items
            ]
            return TradesResponse(
                moments=Moments(),
                venue=self.venue,
                instrument=instrument,
                trades=trades,
            )

        try:
            results = await asyncio.gather(
                *(fetch_trades(inst) for inst in instruments)
            )
            return ClientResponseSuccess(is_successful=True, data=results)
        except Exception as e:
            return ClientResponseFailure(is_successful=False, err_msg=str(e))

    async def get_orderbook(
        self, instruments: list[Instrument]
    ) -> ClientResponse[list[OrderbookResponse]]:
        """Fetch orderbook snapshots for instruments via HTTP REST.

        Args:
            instruments (list[Instrument]): Instruments to fetch orderbooks for.

        Returns:
            ClientResponse[list[OrderbookResponse]]: Orderbook for each instrument.
        """

        async def fetch_orderbook(instrument: Instrument) -> OrderbookResponse:
            params = {
                "instId": self.instrument_to_symbol(instrument),
                "sz": "200",
            }
            decoder = msgspec.json.Decoder(list)
            response = await self.http_client.request(
                method=HttpMethod.GET,
                endpoint=ENDPOINT_GET_ORDERBOOK,
                params=params,
                data={},
                sign=False,
                decoder=decoder,
            )
            if not response.is_successful:
                raise RuntimeError(response.err_msg)

            items = cast(list, response.data)
            if not items:
                raise RuntimeError("Empty orderbook response")

            book = items[0]
            bids = book.get("bids", [])
            asks = book.get("asks", [])

            bid_lvls = [
                OrderbookLevel(price=float(px), size=float(sz)) for px, sz, *_ in bids
            ]
            ask_lvls = [
                OrderbookLevel(price=float(px), size=float(sz)) for px, sz, *_ in asks
            ]

            return OrderbookResponse(
                moments=Moments(),
                venue=self.venue,
                instrument=instrument,
                bids=bid_lvls,
                asks=ask_lvls,
                is_bbo=False,
                is_snapshot=True,
            )

        try:
            results = await asyncio.gather(
                *(fetch_orderbook(inst) for inst in instruments)
            )
            return ClientResponseSuccess(is_successful=True, data=results)
        except Exception as e:
            return ClientResponseFailure(is_successful=False, err_msg=str(e))

    async def get_ticker(
        self, instruments: list[Instrument]
    ) -> ClientResponse[list[TickerResponse]]:
        """Fetch ticker data for instruments via HTTP REST.

        Args:
            instruments (list[Instrument]): Instruments to fetch tickers for.

        Returns:
            ClientResponse[list[TickerResponse]]: Ticker data for each instrument.
        """

        async def fetch_ticker(instrument: Instrument) -> TickerResponse:
            params = {
                "instId": self.instrument_to_symbol(instrument),
            }
            decoder = msgspec.json.Decoder(list)
            response = await self.http_client.request(
                method=HttpMethod.GET,
                endpoint=ENDPOINT_GET_TICKER,
                params=params,
                data={},
                sign=False,
                decoder=decoder,
            )
            if not response.is_successful:
                raise RuntimeError(response.err_msg)

            items = cast(list, response.data)
            if not items:
                raise RuntimeError("Empty ticker response")

            item = items[0]
            return TickerResponse(
                moments=Moments(),
                venue=self.venue,
                instrument=instrument,
                mark_price=float(item.get("markPx", 0.0)),
                index_price=float(item.get("idxPx", 0.0)),
                funding_rate=float(item.get("fundingRate", 0.0)),
                next_funding_time_ms=int(item.get("nextFundingTime", 0)),
                open_interest=float(item.get("openInterest", 0.0))
                if item.get("openInterest")
                else None,
                avg_volume_24h=float(item.get("vol24h", 0.0))
                if item.get("vol24h")
                else None,
                price_chg_24h=None,  # OKX doesn't provide 24h % change in ticker endpoint
            )

        try:
            results = await asyncio.gather(
                *(fetch_ticker(inst) for inst in instruments)
            )
            return ClientResponseSuccess(is_successful=True, data=results)
        except Exception as e:
            return ClientResponseFailure(is_successful=False, err_msg=str(e))

    async def get_instrument_info(
        self, instruments: list[Instrument]
    ) -> ClientResponse[list[InstrumentInfoResponse]]:
        """Fetch instrument metadata via HTTP REST.

        Args:
            instruments (list[Instrument]): Instruments to fetch info for (empty for all).

        Returns:
            ClientResponse[list[InstrumentInfoResponse]]: Metadata for each instrument.
        """
        decoder = msgspec.json.Decoder(list)
        response = await self.http_client.request(
            method=HttpMethod.GET,
            endpoint=ENDPOINT_GET_INSTRUMENTS,
            params={"instType": "SWAP"},
            data={},
            sign=False,
            decoder=decoder,
        )

        if not response.is_successful:
            return ClientResponseFailure(is_successful=False, err_msg=response.err_msg)

        items = cast(list, response.data)

        results: list[InstrumentInfoResponse] = []
        for item in items:
            # Parse instId format: BTC-USDT-SWAP
            inst_id = item.get("instId", "")
            parts = inst_id.split("-")
            if len(parts) != 3 or parts[2] != "SWAP":
                continue

            base = parts[0]
            quote = parts[1]

            tick_size = float(item.get("tickSz", 0.0))
            lot_size = float(item.get("lotSz", 0.0))

            info = InstrumentInfoResponse(
                moments=Moments(),
                venue=self.venue,
                instrument=Instrument(
                    venue=self.venue,
                    base=base,
                    quote=quote,
                    symbol=f"{base}{quote}".upper(),
                    code=0,
                    instrument_type=InstrumentType.PERPETUAL,
                    tick_size=tick_size,
                    lot_size=lot_size,
                ),
                tick_size=tick_size,
                lot_size=lot_size,
                max_taker_size=0.0,
                max_maker_size=0.0,
            )
            results.append(info)

        if instruments:
            wanted = {self.instrument_to_symbol(i) for i in instruments}
            results = [
                r for r in results if self.instrument_to_symbol(r.instrument) in wanted
            ]

        return ClientResponseSuccess(is_successful=True, data=results)

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

        async def fetch_orders(instrument: Instrument) -> OrdersResponse:
            params = {
                "instType": "SWAP",
                "instId": self.instrument_to_symbol(instrument),
            }
            decoder = msgspec.json.Decoder(list)
            response = await self.http_client.request(
                method=HttpMethod.GET,
                endpoint=ENDPOINT_GET_ORDERS,
                params=params,
                data={},
                sign=True,
                decoder=decoder,
            )
            if not response.is_successful:
                raise RuntimeError(response.err_msg)

            items = cast(list, response.data)
            orders = []
            for it in items:
                # Map OKX order type to TIF
                ord_type = it.get("ordType", "limit")
                if ord_type == "market":
                    tif = OrderTimeInForce.IOC
                elif ord_type == "post_only":
                    tif = OrderTimeInForce.PO
                elif ord_type == "fok":
                    tif = OrderTimeInForce.FOK
                elif ord_type == "ioc":
                    tif = OrderTimeInForce.IOC
                else:
                    tif = OrderTimeInForce.GTC

                order = Order(
                    create_time_ms=float(it.get("cTime", 0)),
                    order_id=str(it.get("ordId", "")),
                    price=float(it.get("px", 0.0)),
                    is_buy=(it.get("side", "buy") == "buy"),
                    size=float(it.get("sz", 0.0)),
                    size_remaining=max(
                        0.0,
                        float(it.get("sz", 0.0)) - float(it.get("accFillSz", 0.0)),
                    ),
                    tif=tif,
                    is_cancelled=(it.get("state", "live") in ["canceled", "rejected"]),
                    is_reduce_only=bool(it.get("reduceOnly", False)),
                    client_order_id=it.get("clOrdId"),
                )
                orders.append(order)

            return OrdersResponse(
                moments=Moments(),
                venue=self.venue,
                instrument=instrument,
                orders=orders,
            )

        try:
            results = await asyncio.gather(
                *(fetch_orders(inst) for inst in instruments)
            )
            return ClientResponseSuccess(is_successful=True, data=results)
        except Exception as e:
            return ClientResponseFailure(is_successful=False, err_msg=str(e))

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

        async def fetch_position(instrument: Instrument) -> PositionResponse:
            params = {
                "instType": "SWAP",
                "instId": self.instrument_to_symbol(instrument),
            }
            decoder = msgspec.json.Decoder(list)
            response = await self.http_client.request(
                method=HttpMethod.GET,
                endpoint=ENDPOINT_GET_POSITIONS,
                params=params,
                data={},
                sign=True,
                decoder=decoder,
            )
            if not response.is_successful:
                raise RuntimeError(response.err_msg)

            items = cast(list, response.data)
            total_size = 0.0
            avg_px = 0.0

            for it in items:
                pos = float(it.get("pos", 0.0))
                if pos != 0:
                    total_size = pos
                    avg_px = float(it.get("avgPx", 0.0))
                    break

            return PositionResponse(
                moments=Moments(),
                venue=self.venue,
                instrument=instrument,
                price=avg_px,
                is_long=total_size > 0,
                size=abs(total_size),
            )

        try:
            results = await asyncio.gather(
                *(fetch_position(inst) for inst in instruments)
            )
            return ClientResponseSuccess(is_successful=True, data=results)
        except Exception as e:
            return ClientResponseFailure(is_successful=False, err_msg=str(e))

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

        async def fetch_exec(instrument: Instrument) -> ExecutionResponse:
            params = {
                "instType": "SWAP",
                "instId": self.instrument_to_symbol(instrument),
                "limit": "100",
            }
            decoder = msgspec.json.Decoder(list)
            response = await self.http_client.request(
                method=HttpMethod.GET,
                endpoint=ENDPOINT_GET_FILLS,
                params=params,
                data={},
                sign=True,
                decoder=decoder,
            )
            if not response.is_successful:
                raise RuntimeError(response.err_msg)

            items = cast(list, response.data)
            executions = [
                Execution(
                    exec_time_ms=float(it.get("ts", 0)),
                    order_id=str(it.get("ordId", "")),
                    price=float(it.get("fillPx", 0.0)),
                    is_buy=(it.get("side", "buy") == "buy"),
                    size=float(it.get("fillSz", 0.0)),
                    is_maker=(it.get("execType", "T") == "M"),
                    fee_paid=abs(float(it.get("fee", 0.0))),
                    client_order_id=it.get("clOrdId"),
                )
                for it in items
            ]
            return ExecutionResponse(
                moments=Moments(),
                venue=self.venue,
                instrument=instrument,
                executions=executions,
            )

        try:
            results = await asyncio.gather(*(fetch_exec(inst) for inst in instruments))
            return ClientResponseSuccess(is_successful=True, data=results)
        except Exception as e:
            return ClientResponseFailure(is_successful=False, err_msg=str(e))

    async def get_account(self) -> ClientResponse[AccountResponse]:
        """Fetch account balance and margin data via HTTP REST.

        Returns:
            ClientResponse[AccountResponse]: Account balance and margin information.
        """
        self.ensure_secrets_loaded()
        decoder = msgspec.json.Decoder(list)
        response = await self.http_client.request(
            method=HttpMethod.GET,
            endpoint=ENDPOINT_GET_ACCOUNT,
            params={},
            data={},
            sign=True,
            decoder=decoder,
        )

        if not response.is_successful:
            return ClientResponseFailure(is_successful=False, err_msg=response.err_msg)

        items = cast(list, response.data)
        if not items:
            return ClientResponseFailure(
                is_successful=False, err_msg="Empty account response"
            )

        item = items[0]
        details = item.get("details", [])

        # Aggregate across all currencies (typically USDT for SWAP)
        total_equity = 0.0
        total_im = 0.0
        total_mm = 0.0
        total_upl = 0.0

        for detail in details:
            total_equity += float(detail.get("eq", 0.0))
            total_im += float(detail.get("frozenBal", 0.0))
            total_mm += float(detail.get("mmr", 0.0))
            total_upl += float(detail.get("upl", 0.0))

        acc = AccountResponse(
            moments=Moments(),
            venue=self.venue,
            instrument=Instrument.empty(),
            balance=total_equity,
            initial_margin=total_im,
            maintenance_margin=total_mm,
            unrealized_pnl=total_upl,
        )
        return ClientResponseSuccess(is_successful=True, data=acc)
