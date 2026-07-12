"""framework.binance.trading.exchange"""

from __future__ import annotations

import asyncio

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
from framework.base.tools import EnumMap as EnumMap
from mm_toolbox.logging.standard import Logger
from mm_toolbox.time import time_ns
from framework.base.stream.models import (
    Trade,
    OrderbookLevel,
    Order,
    OrderTimeInForce,
    Execution,
)
from framework.base.trading.client import HttpMethod
from framework.base.trading.exchange import Exchange, VenueEndpoints
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
    OrderbookResponse,
    OrdersResponse,
    PositionResponse,
    TickerResponse,
    TradesResponse,
    is_success,
)
from framework.binance.trading.client import BinanceHttpClient, BinanceWsClient
from framework.binance.trading.time_sync import BinanceTimeSync
from framework.binance.trading.models import (
    BinanceHttpOrderbookResponse,
    BinanceHttpTicker24hrResponse,
    BinanceHttpMarkPriceResponse,
    BinanceHttpOpenInterestResponse,
    BinanceHttpTradeResponse,
    HttpOrder,
    HttpPosition,
    HttpUserTrade,
    HttpAccount,
    SymbolInformation,
    PriceFilter,
    LotSizeFilter,
    MarketLotSizeFilter,
    BinanceHttpExchangeInformationResponse,
)

ENDPOINT_GET_INSTRUMENT_INFO = "/v1/exchangeInfo"
ENDPOINT_GET_OPEN_INTEREST = "/v1/openInterest"
ENDPOINT_GET_ORDERBOOK = "/v1/depth"
ENDPOINT_GET_TICKER = "/v1/ticker/24hr"
ENDPOINT_GET_TRADES = "/v1/trades"
ENDPOINT_GET_MARK_PRICE = "/v1/premiumIndex"
ENDPOINT_GET_ORDERS = "/v1/openOrders"
ENDPOINT_GET_POSITION = "/v2/positionRisk"
ENDPOINT_GET_EXECUTIONS = "/v1/userTrades"
ENDPOINT_GET_ACCOUNT = "/v2/account"
ENDPOINT_POST_ORDER = "/v1/order"
ENDPOINT_PUT_ORDER = "/v1/order"
ENDPOINT_DELETE_ORDER = "/v1/order"
ENDPOINT_DELETE_ALL_ORDERS = "/v1/allOpenOrders"
ENDPOINT_POST_LISTEN_KEY = "/v1/listenKey"
RECV_WINDOW = 5000


class BinanceExchange(Exchange):
    """Binance exchange implementation for trading and market data."""

    def __init__(
        self,
        logger: Logger,
        load_secrets: bool,
        is_usd_margined: bool,
        endpoints: VenueEndpoints | None = None,
    ) -> None:
        """Initialize the Binance exchange client.

        Args:
            logger: Logger instance for diagnostics.
            load_secrets: Whether to load API secrets.
            is_usd_margined: True for USD-M, False for COIN-M.
        """
        venue = Venue.BINANCE_USDM if is_usd_margined else Venue.BINANCE_COINM
        default_root = "fapi" if is_usd_margined else "dapi"
        default_ws = "fstream" if is_usd_margined else "dstream"
        ws_api = "ws-fapi" if is_usd_margined else "ws-dapi"
        ws_api_path = "ws-fapi" if is_usd_margined else "ws-dapi"
        endpoints = endpoints or VenueEndpoints(
            http=f"https://{default_root}.binance.com/{default_root}",
            trading_ws=f"wss://{ws_api}.binance.com/{ws_api_path}/v1",
            public_ws=f"wss://{default_ws}.binance.com/public/ws",
            market_ws=f"wss://{default_ws}.binance.com/market/ws",
            private_ws=f"wss://{default_ws}.binance.com/private/ws",
            time=f"https://{default_root}.binance.com/{default_root}/v1/time",
        )
        time_sync = BinanceTimeSync(venue=venue, logger=logger, url=endpoints.time)
        super().__init__(
            venue=venue,
            logger=logger,
            load_secrets=load_secrets,
            http_client=BinanceHttpClient(
                logger=logger,
                load_secrets=load_secrets,
                time_sync=time_sync,
                is_usd_margined=is_usd_margined,
                base_url=endpoints.http,
            ),
            ws_client=BinanceWsClient(
                logger=logger,
                time_sync=time_sync,
                load_secrets=load_secrets,
                is_usd_margined=is_usd_margined,
                base_url=endpoints.trading_ws,
            ),
            time_sync=time_sync,
            endpoints=endpoints,
        )

        self._tif_map = EnumMap(
            enum_class=OrderTimeInForce,
            mapping={
                OrderTimeInForce.GTC: "GTC",
                OrderTimeInForce.PO: "GTX",
                OrderTimeInForce.IOC: "IOC",
                OrderTimeInForce.FOK: "FOK",
            },
        )

    def instrument_to_symbol(self, instrument: Instrument) -> Symbol:
        """Return the Binance symbol for an instrument.

        Args:
            instrument: Instrument to format.

        Returns:
            Symbol: Binance symbol string.
        """
        return instrument.symbol

    async def get_instrument_collection(self) -> ClientResponse[InstrumentCollection]:
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
        """Creates an order on the exchange via WebSocket API."""
        self.ensure_secrets_loaded()
        self.ensure_running(ws_only=True)

        params = {
            "symbol": create_order.instrument.symbol,
            "side": "BUY" if create_order.is_buy else "SELL",
            "type": "LIMIT" if create_order.is_maker else "MARKET",
            "timeInForce": self._tif_map.enum_to_str(create_order.tif),
            "quantity": str(create_order.size),
        }
        if create_order.is_maker and create_order.price is not None:
            params["price"] = str(create_order.price)
        if create_order.reduce_only:
            params["reduceOnly"] = True
        if create_order.client_order_id:
            params["clientOrderId"] = create_order.client_order_id

        payload = {
            "method": "order.place",
            "params": params,
        }

        decoder = msgspec.json.Decoder(dict)
        response = await self.ws_client.submit(data=payload, decoder=decoder)

        if not is_success(response):
            return self.make_failure(
                meta=response.meta,
                err_no=response.err_no,
                err_msg=response.err_msg,
            )

        order_response = response.data.get("result", response.data)
        moments = Moments()
        response_id = MessageId(recv_time_ns=moments.recv_time_ns)
        return self.make_success(
            meta=response.meta,
            data=CreateOrderResponse(
                id=response_id,
                origin_id=create_order.origin_id or create_order.id,
                moments=moments,
                instrument=create_order.instrument,
                order_id=OrderId(str(order_response["orderId"])),
                client_order_id=ClientOrderId(str(order_response["clientOrderId"])),
            ),
        )

    async def amend_order(
        self, amend_order: AmendOrder
    ) -> ClientResponse[AmendOrderResponse]:
        self.ensure_secrets_loaded()
        self.ensure_running(ws_only=True)

        params = {
            "symbol": amend_order.instrument.symbol,
            "quantity": str(amend_order.size),
        }
        if amend_order.order_id:
            params["orderId"] = amend_order.order_id
        if amend_order.client_order_id:
            params["origClientOrderId"] = amend_order.client_order_id
        if amend_order.price is not None:
            params["price"] = str(amend_order.price)

        payload = {
            "method": "order.modify",
            "params": params,
        }

        decoder = msgspec.json.Decoder(dict)
        response = await self.ws_client.submit(data=payload, decoder=decoder)

        if not is_success(response):
            return self.make_failure(
                meta=response.meta,
                err_no=response.err_no,
                err_msg=response.err_msg,
            )

        amend_response = response.data.get("result", response.data)
        moments = Moments()
        response_id = MessageId(recv_time_ns=moments.recv_time_ns)
        return self.make_success(
            meta=response.meta,
            data=AmendOrderResponse(
                id=response_id,
                origin_id=amend_order.origin_id or amend_order.id,
                moments=moments,
                instrument=amend_order.instrument,
                order_id=OrderId(str(amend_response["orderId"])),
                client_order_id=ClientOrderId(str(amend_response["clientOrderId"])),
            ),
        )

    async def cancel_order(
        self, cancel_order: CancelOrder
    ) -> ClientResponse[CancelOrderResponse]:
        self.ensure_secrets_loaded()
        self.ensure_running(ws_only=True)

        params: dict[str, str] = {
            "symbol": cancel_order.instrument.symbol,
        }
        if cancel_order.order_id:
            params["orderId"] = cancel_order.order_id
        if cancel_order.client_order_id:
            params["origClientOrderId"] = cancel_order.client_order_id

        payload = {
            "method": "order.cancel",
            "params": params,
        }

        decoder = msgspec.json.Decoder(dict)
        response = await self.ws_client.submit(data=payload, decoder=decoder)

        if not is_success(response):
            return self.make_failure(
                meta=response.meta,
                err_no=response.err_no,
                err_msg=response.err_msg,
            )

        cancel_response = response.data.get("result", response.data)
        moments = Moments()
        response_id = MessageId(recv_time_ns=moments.recv_time_ns)
        return self.make_success(
            meta=response.meta,
            data=CancelOrderResponse(
                id=response_id,
                origin_id=cancel_order.origin_id or cancel_order.id,
                moments=moments,
                instrument=cancel_order.instrument,
                order_id=OrderId(str(cancel_response["orderId"])),
                client_order_id=ClientOrderId(str(cancel_response["clientOrderId"])),
            ),
        )

    async def cancel_all_orders(
        self, cancel_all_orders: CancelAllOrders
    ) -> ClientResponse[CancelAllOrdersResponse]:
        self.ensure_secrets_loaded()
        self.ensure_running(http_only=True)

        params = {
            "symbol": cancel_all_orders.instrument.symbol,
            "recvWindow": str(RECV_WINDOW),
        }

        decoder = msgspec.json.Decoder(list[dict])
        response = await self.http_client.request(
            method=HttpMethod.DELETE,
            endpoint=ENDPOINT_DELETE_ALL_ORDERS,
            params=params,
            data={},
            sign=True,
            decoder=decoder,
        )

        if not is_success(response):
            return self.make_failure(
                meta=response.meta,
                err_no=response.err_no,
                err_msg=response.err_msg,
            )

        # Binance returns list of cancelled orders; we optionally extract IDs
        order_ids = None
        client_ids = None
        try:
            data_list = response.data
            order_ids = tuple(
                OrderId(str(item.get("orderId", ""))) for item in data_list
            )
            client_ids = tuple(
                ClientOrderId(str(item.get("clientOrderId", ""))) for item in data_list
            )
        except Exception:
            pass

        moments = Moments()
        response_id = MessageId(recv_time_ns=moments.recv_time_ns)
        return self.make_success(
            meta=response.meta,
            data=CancelAllOrdersResponse(
                id=response_id,
                origin_id=cancel_all_orders.origin_id or cancel_all_orders.id,
                moments=moments,
                instrument=cancel_all_orders.instrument,
                order_ids=order_ids,
                client_order_ids=client_ids,
            ),
        )

    async def get_trades(
        self, instruments: list[Instrument]
    ) -> ClientResponse[list[TradesResponse]]:
        started_ns = time_ns()

        async def fetch_trades(instrument: Instrument) -> TradesResponse:
            """Fetch recent trades for a single instrument."""
            decoder = msgspec.json.Decoder(list[BinanceHttpTradeResponse])

            response = await self.http_client.request(
                method=HttpMethod.GET,
                endpoint=ENDPOINT_GET_TRADES,
                params={"symbol": instrument.symbol, "limit": 1000},
                data={},
                sign=False,
                decoder=decoder,
            )

            if not is_success(response):
                raise RuntimeError(response.err_msg)

            trades = [
                Trade(
                    time_ms=trade.time,
                    price=float(trade.price),
                    is_buy=not trade.is_buyer_maker,  # buyer_maker=False == taker=buyer
                    size=float(trade.qty),
                )
                for trade in response.data
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
            responses = await asyncio.gather(
                *[fetch_trades(instrument) for instrument in instruments]
            )
            return self.make_success(
                data=responses,
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
        """Gets orderbook snapshots for instruments using parallel requests."""
        started_ns = time_ns()

        async def fetch_orderbook(instrument: Instrument) -> OrderbookResponse:
            """Fetch orderbook for a single instrument."""
            params = {"symbol": instrument.symbol, "limit": 1000}

            decoder = msgspec.json.Decoder(BinanceHttpOrderbookResponse)

            response = await self.http_client.request(
                method=HttpMethod.GET,
                endpoint=ENDPOINT_GET_ORDERBOOK,
                params=params,
                data={},
                sign=False,
                decoder=decoder,
            )

            if is_success(response):
                orderbook_data = response.data

                bids = tuple(
                    sorted(
                        (
                            OrderbookLevel(
                                price=float(level[0]),
                                size=float(level[1]),
                            )
                            for level in orderbook_data.bids
                        ),
                        key=lambda x: x.price,
                    )
                )

                asks = tuple(
                    sorted(
                        (
                            OrderbookLevel(
                                price=float(level[0]),
                                size=float(level[1]),
                            )
                            for level in orderbook_data.asks
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
                    bids=bids,
                    asks=asks,
                )
            else:
                raise Exception(
                    f"Failed to get orderbook for {instrument}; {response.err_msg}"
                )

        try:
            orderbook_responses = await asyncio.gather(
                *[fetch_orderbook(instrument) for instrument in instruments]
            )

            return self.make_success(
                data=orderbook_responses,
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
        """Gets ticker data for instruments using parallel requests."""
        started_ns = time_ns()

        async def fetch_ticker(instrument: Instrument) -> TickerResponse:
            """Fetch ticker data for a single instrument by combining 24hr stats and mark price."""
            symbol = instrument.symbol

            ticker_decoder = msgspec.json.Decoder(BinanceHttpTicker24hrResponse)
            mark_price_decoder = msgspec.json.Decoder(BinanceHttpMarkPriceResponse)
            oi_decoder = msgspec.json.Decoder(BinanceHttpOpenInterestResponse)

            ticker_response, mark_price_response, oi_response = await asyncio.gather(
                self.http_client.request(
                    method=HttpMethod.GET,
                    endpoint=ENDPOINT_GET_TICKER,
                    params={"symbol": symbol},
                    data={},
                    sign=False,
                    decoder=ticker_decoder,
                ),
                self.http_client.request(
                    method=HttpMethod.GET,
                    endpoint=ENDPOINT_GET_MARK_PRICE,
                    params={"symbol": symbol},
                    data={},
                    sign=False,
                    decoder=mark_price_decoder,
                ),
                self.http_client.request(
                    method=HttpMethod.GET,
                    endpoint=ENDPOINT_GET_OPEN_INTEREST,
                    params={"symbol": symbol},
                    data={},
                    sign=False,
                    decoder=oi_decoder,
                ),
            )

            if not is_success(ticker_response):
                raise Exception(
                    f"Failed to get 24hr ticker for {instrument}; {ticker_response.err_msg}"
                )
            if not is_success(mark_price_response):
                raise Exception(
                    f"Failed to get mark price for {instrument}; {mark_price_response.err_msg}"
                )
            if not is_success(oi_response):
                raise Exception(
                    f"Failed to get open interest for {instrument}; {oi_response.err_msg}"
                )

            ticker_data = ticker_response.data
            mark_price_data = mark_price_response.data
            oi_data = oi_response.data

            moments = Moments()
            response_id = MessageId(recv_time_ns=moments.recv_time_ns)
            return TickerResponse(
                id=response_id,
                origin_id=response_id,
                moments=moments,
                instrument=instrument,
                mark_price=float(mark_price_data.mark_price),
                index_price=float(mark_price_data.index_price),
                funding_rate=float(mark_price_data.last_funding_rate),
                next_funding_time_ms=mark_price_data.next_funding_time,
                open_interest=float(oi_data.open_interest),
                avg_volume_24h=float(ticker_data.volume) if ticker_data.volume else 0.0,
                price_chg_24h=float(ticker_data.price_change)
                if ticker_data.price_change
                else 0.0,
            )

        try:
            ticker_responses = await asyncio.gather(
                *[fetch_ticker(instrument) for instrument in instruments]
            )

            return self.make_success(
                data=ticker_responses,
                meta=self.make_meta(
                    operation=f"{ENDPOINT_GET_TICKER}|{ENDPOINT_GET_MARK_PRICE}|{ENDPOINT_GET_OPEN_INTEREST}",
                    started_ns=started_ns,
                    finished_ns=time_ns(),
                ),
            )
        except Exception as e:
            return self.make_failure(
                meta=self.make_meta(
                    operation=f"{ENDPOINT_GET_TICKER}|{ENDPOINT_GET_MARK_PRICE}|{ENDPOINT_GET_OPEN_INTEREST}",
                    started_ns=started_ns,
                    finished_ns=time_ns(),
                ),
                err_no=1,
                err_msg=str(e),
            )

    async def get_orders(
        self, instruments: list[Instrument]
    ) -> ClientResponse[list[OrdersResponse]]:
        """Gets open orders for instruments using parallel requests."""
        self.ensure_secrets_loaded()
        started_ns = time_ns()

        async def fetch_orders(instrument: Instrument) -> OrdersResponse:
            """Fetch open orders for a single instrument."""
            params = {
                "symbol": instrument.symbol,
            }

            decoder = msgspec.json.Decoder(list[HttpOrder])

            response = await self.http_client.request(
                method=HttpMethod.GET,
                endpoint=ENDPOINT_GET_ORDERS,
                params=params,
                data={},
                sign=True,
                decoder=decoder,
            )

            if not is_success(response):
                raise Exception(
                    f"Failed to get orders for {instrument}; {response.err_msg}"
                )

            orders_data = response.data
            orders = [
                Order(
                    create_time_ms=max(
                        float(order.time if order.time > 0 else order.update_time),
                        1.0,
                    ),
                    order_id=OrderId(str(order.order_id)),
                    price=float(order.price),
                    is_buy=order.side.upper() == "BUY",
                    size=float(order.orig_qty),
                    size_remaining=float(order.orig_qty) - float(order.executed_qty),
                    tif=self._tif_map.str_to_enum(
                        order.time_in_force, OrderTimeInForce.GTC
                    ),
                    is_cancelled=order.status == "CANCELED",
                    is_reduce_only=order.reduce_only,
                    client_order_id=ClientOrderId(str(order.client_order_id))
                    if order.client_order_id
                    else None,
                )
                for order in orders_data
            ]

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
            # Execute all requests in parallel
            orders_responses = await asyncio.gather(
                *[fetch_orders(instrument) for instrument in instruments]
            )

            return self.make_success(
                data=orders_responses,
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
        """Gets position data for instruments using parallel requests."""
        self.ensure_secrets_loaded()
        started_ns = time_ns()

        async def fetch_position(instrument: Instrument) -> PositionResponse:
            """Fetch position for a single instrument."""
            params = {
                "symbol": instrument.symbol,
            }

            decoder = msgspec.json.Decoder(list[HttpPosition])

            response = await self.http_client.request(
                method=HttpMethod.GET,
                endpoint=ENDPOINT_GET_POSITION,
                params=params,
                data={},
                sign=True,
                decoder=decoder,
            )

            if not is_success(response):
                raise Exception(
                    f"Failed to get position for {instrument}; {response.err_msg}"
                )

            positions_data = response.data

            # Find the relevant position (there may be multiple position sides)
            total_size = 0.0
            avg_price = 0.0
            total_notional = 0.0

            for pos in positions_data:
                if pos.symbol.upper() == instrument.symbol.upper():
                    position_size = float(pos.position_amt)
                    if position_size != 0:
                        entry_price = float(pos.entry_price)
                        notional = abs(position_size * entry_price)
                        total_notional += notional
                        total_size += position_size

            # Calculate weighted average price
            if total_notional > 0:
                avg_price = total_notional / abs(total_size) if total_size != 0 else 0.0

            moments = Moments()
            response_id = MessageId(recv_time_ns=moments.recv_time_ns)
            return PositionResponse(
                id=response_id,
                origin_id=response_id,
                moments=moments,
                instrument=instrument,
                price=avg_price,
                is_long=total_size > 0,
                size=abs(total_size),
            )

        try:
            # Execute all requests in parallel
            position_responses = await asyncio.gather(
                *[fetch_position(instrument) for instrument in instruments]
            )

            return self.make_success(
                data=position_responses,
                meta=self.make_meta(
                    operation=ENDPOINT_GET_POSITION,
                    started_ns=started_ns,
                    finished_ns=time_ns(),
                ),
            )
        except Exception as e:
            return self.make_failure(
                meta=self.make_meta(
                    operation=ENDPOINT_GET_POSITION,
                    started_ns=started_ns,
                    finished_ns=time_ns(),
                ),
                err_no=1,
                err_msg=str(e),
            )

    async def get_executions(
        self, instruments: list[Instrument]
    ) -> ClientResponse[list[ExecutionResponse]]:
        """Gets executions (user trades) for instruments using parallel requests."""
        self.ensure_secrets_loaded()
        started_ns = time_ns()

        async def fetch_executions(instrument: Instrument) -> ExecutionResponse:
            """Fetch executions for a single instrument."""
            params = {
                "symbol": instrument.symbol,
                "limit": 500,  # Get recent executions
            }

            decoder = msgspec.json.Decoder(list[HttpUserTrade])

            response = await self.http_client.request(
                method=HttpMethod.GET,
                endpoint=ENDPOINT_GET_EXECUTIONS,
                params=params,
                data={},
                sign=True,
                decoder=decoder,
            )

            if not is_success(response):
                raise Exception(
                    f"Failed to get executions for {instrument}; {response.err_msg}"
                )

            executions_data = response.data
            executions = [
                Execution(
                    exec_time_ms=max(float(trade.time), 1.0),
                    order_id=OrderId(str(trade.order_id)),
                    price=float(trade.price),
                    is_buy=trade.side.upper() == "BUY",
                    size=float(trade.qty),
                    is_maker=trade.is_maker,
                    fee_paid=float(trade.commission),
                    client_order_id=None,  # Not available in this endpoint
                )
                for trade in executions_data
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
            # Execute all requests in parallel
            execution_responses = await asyncio.gather(
                *[fetch_executions(instrument) for instrument in instruments]
            )

            return self.make_success(
                data=execution_responses,
                meta=self.make_meta(
                    operation=ENDPOINT_GET_EXECUTIONS,
                    started_ns=started_ns,
                    finished_ns=time_ns(),
                ),
            )
        except Exception as e:
            return self.make_failure(
                meta=self.make_meta(
                    operation=ENDPOINT_GET_EXECUTIONS,
                    started_ns=started_ns,
                    finished_ns=time_ns(),
                ),
                err_no=1,
                err_msg=str(e),
            )

    async def get_account(self) -> ClientResponse[AccountResponse]:
        """Gets account data from the exchange."""
        self.ensure_secrets_loaded()
        started_ns = time_ns()

        decoder = msgspec.json.Decoder(HttpAccount)

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

        account_data = response.data

        moments = Moments()
        response_id = MessageId(recv_time_ns=moments.recv_time_ns)
        account_response = AccountResponse(
            id=response_id,
            origin_id=response_id,
            moments=moments,
            instrument=Instrument.empty_with(venue=self.venue),
            balance=float(account_data.total_wallet_balance),
            initial_margin=float(account_data.total_initial_margin),
            maintenance_margin=float(account_data.total_maint_margin),
            unrealized_pnl=float(account_data.total_unrealized_pnl),
        )

        return self.make_success(
            data=account_response,
            meta=self.make_meta(
                operation=ENDPOINT_GET_ACCOUNT,
                started_ns=started_ns,
                finished_ns=time_ns(),
                status_code=response.meta.status_code,
            ),
        )

    async def get_instrument_info(
        self, instruments: list[Instrument]
    ) -> ClientResponse[list[InstrumentInfoResponse]]:
        """Gets instrument information by fetching all instruments and filtering locally."""
        started_ns = time_ns()

        def parse_symbol_data(
            symbol: SymbolInformation,
        ) -> InstrumentInfoResponse | None:
            """Parse symbol data into InstrumentInfoResponse."""
            if symbol.status != "TRADING":
                return None

            tick_size = 0.0
            lot_size = 0.0
            max_taker_size = 0.0
            max_maker_size = 0.0

            for f in symbol.filters:
                if isinstance(f, PriceFilter):
                    tick_size = float(f.tick_size)
                elif isinstance(f, LotSizeFilter):
                    lot_size = float(f.step_size)
                    max_maker_size = float(f.max_qty)
                elif isinstance(f, MarketLotSizeFilter):
                    max_taker_size = float(f.max_qty)

            moments = Moments()
            response_id = MessageId(recv_time_ns=moments.recv_time_ns)
            return InstrumentInfoResponse(
                id=response_id,
                origin_id=response_id,
                moments=moments,
                instrument=Instrument(
                    venue=self.venue,
                    base=Asset(symbol.base_asset),
                    quote=Asset(symbol.quote_asset),
                    symbol=Symbol(f"{symbol.base_asset}{symbol.quote_asset}"),
                    code=0,
                    instrument_type=InstrumentType.PERPETUAL,
                    tick_size=tick_size,
                    lot_size=lot_size,
                ),
                tick_size=tick_size,
                lot_size=lot_size,
                max_taker_size=max_taker_size,
                max_maker_size=max_maker_size,
            )

        try:
            decoder = msgspec.json.Decoder(BinanceHttpExchangeInformationResponse)

            response = await self.http_client.request(
                method=HttpMethod.GET,
                endpoint=ENDPOINT_GET_INSTRUMENT_INFO,
                params={},  # No symbol parameter = get all
                data={},
                sign=False,
                decoder=decoder,
            )

            if not is_success(response):
                raise Exception(f"Failed to get instrument info; {response.err_msg}")

            response_data = response.data

            all_instrument_infos = []
            for symbol in response_data.symbols:
                if parsed := parse_symbol_data(symbol):
                    all_instrument_infos.append(parsed)

            if instruments:
                requested_symbols = {
                    self.instrument_to_symbol(inst).upper() for inst in instruments
                }
                filtered_infos = [
                    info
                    for info in all_instrument_infos
                    if f"{info.instrument.base}{info.instrument.quote}".upper()
                    in requested_symbols
                ]
                return self.make_success(
                    data=filtered_infos,
                    meta=self.make_meta(
                        operation=ENDPOINT_GET_INSTRUMENT_INFO,
                        started_ns=started_ns,
                        finished_ns=time_ns(),
                        status_code=response.meta.status_code,
                    ),
                )
            else:
                return self.make_success(
                    data=all_instrument_infos,
                    meta=self.make_meta(
                        operation=ENDPOINT_GET_INSTRUMENT_INFO,
                        started_ns=started_ns,
                        finished_ns=time_ns(),
                        status_code=response.meta.status_code,
                    ),
                )
        except Exception as e:
            return self.make_failure(
                meta=self.make_meta(
                    operation=ENDPOINT_GET_INSTRUMENT_INFO,
                    started_ns=started_ns,
                    finished_ns=time_ns(),
                ),
                err_no=1,
                err_msg=str(e),
            )

    async def get_open_interest(
        self, instruments: list[Instrument]
    ) -> ClientResponse[list[float]]:
        """Gets the open interest for instruments using parallel requests."""
        started_ns = time_ns()

        async def fetch_open_interest(instrument: Instrument) -> float:
            """Fetch open interest for a single instrument."""
            params = {
                "symbol": instrument.symbol,
            }

            decoder = msgspec.json.Decoder(BinanceHttpOpenInterestResponse)

            response = await self.http_client.request(
                method=HttpMethod.GET,
                endpoint=ENDPOINT_GET_OPEN_INTEREST,
                params=params,
                data={},
                sign=False,
                decoder=decoder,
            )

            if not is_success(response):
                raise Exception(
                    f"Failed to get open interest for {instrument}; {response.err_msg}"
                )

            open_interest_data = response.data
            return float(open_interest_data.open_interest)

        try:
            # Execute all requests in parallel
            open_interests = await asyncio.gather(
                *[fetch_open_interest(instrument) for instrument in instruments]
            )

            return self.make_success(
                data=open_interests,
                meta=self.make_meta(
                    operation=ENDPOINT_GET_OPEN_INTEREST,
                    started_ns=started_ns,
                    finished_ns=time_ns(),
                ),
            )
        except Exception as e:
            return self.make_failure(
                meta=self.make_meta(
                    operation=ENDPOINT_GET_OPEN_INTEREST,
                    started_ns=started_ns,
                    finished_ns=time_ns(),
                ),
                err_no=1,
                err_msg=str(e),
            )

    async def get_listen_key(self) -> ClientResponse[str]:
        """Get listen key from Binance REST API for authenticated websocket connection."""
        self.ensure_secrets_loaded()
        started_ns = time_ns()

        decoder = msgspec.json.Decoder(dict)

        # Use client's base URL + relative endpoint; Binance listenKey does NOT require signature
        response = await self.http_client.request(
            method=HttpMethod.POST,
            endpoint=ENDPOINT_POST_LISTEN_KEY,
            params={},
            data={},
            sign=False,
            decoder=decoder,
        )

        if not is_success(response):
            return self.make_failure(
                meta=self.make_meta(
                    operation=ENDPOINT_POST_LISTEN_KEY,
                    started_ns=started_ns,
                    finished_ns=time_ns(),
                    status_code=response.meta.status_code,
                ),
                err_no=response.err_no,
                err_msg=response.err_msg,
            )

        response_data = response.data
        listen_key = response_data.get("listenKey", "")
        return self.make_success(
            data=listen_key,
            meta=self.make_meta(
                operation=ENDPOINT_POST_LISTEN_KEY,
                started_ns=started_ns,
                finished_ns=time_ns(),
                status_code=response.meta.status_code,
            ),
        )
