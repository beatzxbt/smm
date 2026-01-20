"""framework.binance.trading.exchange"""

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
from framework.base.tools import EnumMap as EnumMap
from mm_toolbox.logging.standard import Logger
from framework.base.stream.models import (
    Moments,
    Trade,
    OrderbookLevel,
    Order,
    OrderTimeInForce,
    Execution,
)
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
    OrderbookResponse,
    OrdersResponse,
    PositionResponse,
    TickerResponse,
    TradesResponse,
)
from framework.binance.trading.client import BinanceHttpClient, BinanceWsClient
from framework.binance.trading.structs import (
    BinanceWsOrderResponse,
    BinanceWsCreateOrderResult,
    BinanceWsAmendOrderResult,
    BinanceWsCancelOrderResult,
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
    ) -> None:
        """Initialize the Binance exchange client.

        Args:
            logger: Logger instance for diagnostics.
            load_secrets: Whether to load API secrets.
            is_usd_margined: True for USD-M, False for COIN-M.
        """
        super().__init__(
            venue=Venue.BINANCE_USDM if is_usd_margined else Venue.BINANCE_COINM,
            logger=logger,
            load_secrets=load_secrets,
            http_client=BinanceHttpClient(
                logger=logger,
                load_secrets=load_secrets,
                is_usd_margined=is_usd_margined,
            ),
            ws_client=BinanceWsClient(
                logger=logger,
                load_secrets=load_secrets,
                is_usd_margined=is_usd_margined,
            ),
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

    def instrument_to_symbol(self, instrument: Instrument) -> str:
        """Return the Binance symbol for an instrument.

        Args:
            instrument: Instrument to format.

        Returns:
            str: Binance symbol string.
        """
        return instrument.symbol

    async def get_instrument_collection(self) -> ClientResponse[InstrumentCollection]:
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

        decoder = msgspec.json.Decoder(
            BinanceWsOrderResponse[BinanceWsCreateOrderResult]
        )
        response = await self.ws_client.submit(data=payload, decoder=decoder)

        if not response.is_successful:
            return ClientResponseFailure(
                err_no=response.err_no,
                err_msg=response.err_msg,
            )

        order_response = cast(BinanceWsOrderResponse, response.data)
        return ClientResponseSuccess(
            data=CreateOrderResponse(
                moments=Moments(),
                venue=create_order.instrument.venue,
                instrument=create_order.instrument,
                trigger=create_order,
                order_id=str(order_response.result.order_id),
                client_order_id=order_response.result.client_order_id,
            ),
        )

    async def amend_order(
        self, amend_order: AmendOrder
    ) -> ClientResponse[AmendOrderResponse]:
        self.ensure_secrets_loaded()
        self.ensure_running(ws_only=True)

        params = {
            "symbol": amend_order.instrument.symbol,
            "qty": str(amend_order.size),
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

        decoder = msgspec.json.Decoder(
            BinanceWsOrderResponse[BinanceWsAmendOrderResult]
        )
        response = await self.ws_client.submit(data=payload, decoder=decoder)

        if not response.is_successful:
            return ClientResponseFailure(
                err_no=response.err_no,
                err_msg=response.err_msg,
            )

        return ClientResponseSuccess(
            data=AmendOrderResponse(
                moments=Moments(),
                venue=amend_order.instrument.venue,
                instrument=amend_order.instrument,
                trigger=amend_order,
                order_id=str(response.data.result.order_id),
                client_order_id=response.data.result.client_order_id,
            ),
        )

    async def cancel_order(
        self, cancel_order: CancelOrder
    ) -> ClientResponse[CancelOrderResponse]:
        self.ensure_secrets_loaded()
        self.ensure_running(ws_only=True)

        params = {
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

        decoder = msgspec.json.Decoder(
            BinanceWsOrderResponse[BinanceWsCancelOrderResult]
        )
        response = await self.ws_client.submit(data=payload, decoder=decoder)

        if not response.is_successful:
            return ClientResponseFailure(
                err_no=response.err_no,
                err_msg=response.err_msg,
            )

        return ClientResponseSuccess(
            data=CancelOrderResponse(
                moments=Moments(),
                venue=cancel_order.instrument.venue,
                instrument=cancel_order.instrument,
                trigger=cancel_order,
                order_id=str(response.data.result.order_id),
                client_order_id=response.data.result.client_order_id,
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

        if not response.is_successful:
            return ClientResponseFailure(
                err_no=response.err_no,
                err_msg=response.err_msg,
            )

        # Binance returns list of cancelled orders; we optionally extract IDs
        order_ids: list[str] | None = None
        client_ids: list[str] | None = None
        try:
            data_list = cast(list[dict], response.data)
            order_ids = [str(item.get("orderId", "")) for item in data_list]
            client_ids = [str(item.get("clientOrderId", "")) for item in data_list]
        except Exception:
            pass

        return ClientResponseSuccess(
            data=CancelAllOrdersResponse(
                moments=Moments(),
                venue=cancel_all_orders.instrument.venue,
                instrument=cancel_all_orders.instrument,
                trigger=cancel_all_orders,
                order_ids=order_ids,
                client_order_ids=client_ids,
            ),
        )

    async def get_trades(
        self, instruments: list[Instrument]
    ) -> ClientResponse[list[TradesResponse]]:
        async def fetch_trades(
            instrument: Instrument,
        ) -> ClientResponse[TradesResponse]:
            """Fetch recent trades for a single instrument."""
            params = {"symbol": instrument.symbol, "limit": 500}

            decoder = msgspec.json.Decoder(list[BinanceHttpTradeResponse])

            response = await self.http_client.request(
                method=HttpMethod.GET,
                endpoint=ENDPOINT_GET_TRADES,
                params=params,
                data={},
                sign=False,
                decoder=decoder,
            )

            if response.is_successful:
                trades = [
                    Trade(
                        time_ms=trade.time,
                        price=float(trade.price),
                        is_buy=not trade.is_buyer_maker,  # buyer_maker=False == taker=buyer
                        size=float(trade.qty),
                    )
                    for trade in response.data
                ]

                return ClientResponseSuccess(
                    data=TradesResponse(
                        moments=Moments(),
                        venue=instrument.venue,
                        instrument=instrument,
                        trades=trades,
                    ),
                )
            else:
                return ClientResponseFailure(
                    err_no=response.err_no,
                    err_msg=response.err_msg,
                )

        responses = await asyncio.gather(
            *[fetch_trades(instrument) for instrument in instruments]
        )
        for response in responses:
            if not response.is_successful:
                return ClientResponseFailure(
                    err_no=response.err_no,
                    err_msg=response.err_msg,
                )
        return ClientResponseSuccess(
            data=[response.data for response in responses if response.data is not None],
        )

    async def get_orderbook(
        self, instruments: list[Instrument]
    ) -> ClientResponse[list[OrderbookResponse]]:
        """Gets orderbook snapshots for instruments using parallel requests."""

        async def fetch_orderbook(instrument: Instrument) -> OrderbookResponse:
            """Fetch orderbook for a single instrument."""
            params = {"symbol": instrument.symbol, "limit": 100}

            decoder = msgspec.json.Decoder(BinanceHttpOrderbookResponse)

            response = await self.http_client.request(
                method=HttpMethod.GET,
                endpoint=ENDPOINT_GET_ORDERBOOK,
                params=params,
                data={},
                sign=False,
                decoder=decoder,
            )

            if response.is_successful:
                orderbook_data = cast(BinanceHttpOrderbookResponse, response.data)

                bids = [
                    OrderbookLevel(
                        price=float(level[0]),
                        size=float(level[1]),
                    )
                    for level in orderbook_data.bids
                ]

                asks = [
                    OrderbookLevel(
                        price=float(level[0]),
                        size=float(level[1]),
                    )
                    for level in orderbook_data.asks
                ]

                return OrderbookResponse(
                    moments=Moments(),
                    venue=self.venue,
                    instrument=instrument,
                    bids=bids,
                    asks=asks,
                    is_snapshot=True,
                )
            else:
                raise Exception(
                    f"Failed to get orderbook for {instrument}; {response.err_msg}"
                )

        try:
            orderbook_responses = await asyncio.gather(
                *[fetch_orderbook(instrument) for instrument in instruments]
            )

            return ClientResponseSuccess(
                is_successful=True,
                data=orderbook_responses,
            )
        except Exception as e:
            return ClientResponseFailure(
                is_successful=False,
                err_msg=str(e),
            )

    async def get_ticker(
        self, instruments: list[Instrument]
    ) -> ClientResponse[list[TickerResponse]]:
        """Gets ticker data for instruments using parallel requests."""

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

            if not ticker_response.is_successful:
                raise Exception(
                    f"Failed to get 24hr ticker for {instrument}; {ticker_response.err_msg}"
                )
            if not mark_price_response.is_successful:
                raise Exception(
                    f"Failed to get mark price for {instrument}; {mark_price_response.err_msg}"
                )
            if not oi_response.is_successful:
                raise Exception(
                    f"Failed to get open interest for {instrument}; {oi_response.err_msg}"
                )

            ticker_data = cast(BinanceHttpTicker24hrResponse, ticker_response.data)
            mark_price_data = cast(
                BinanceHttpMarkPriceResponse, mark_price_response.data
            )
            oi_data = cast(BinanceHttpOpenInterestResponse, oi_response.data)

            return TickerResponse(
                moments=Moments(),
                venue=self.venue,
                instrument=instrument,
                mark_price=float(mark_price_data.mark_price),
                index_price=float(mark_price_data.index_price),
                funding_rate=float(mark_price_data.last_funding_rate),
                next_funding_time_ms=mark_price_data.next_funding_time,
                open_interest=float(oi_data.open_interest),
                avg_volume_24h=float(ticker_data.volume)
                if ticker_data.volume
                else None,
                price_chg_24h=float(ticker_data.price_change)
                if ticker_data.price_change
                else None,
            )

        try:
            ticker_responses = await asyncio.gather(
                *[fetch_ticker(instrument) for instrument in instruments]
            )

            return ClientResponseSuccess(
                is_successful=True,
                data=ticker_responses,
            )
        except Exception as e:
            return ClientResponseFailure(
                is_successful=False,
                err_msg=str(e),
            )

    async def get_orders(
        self, instruments: list[Instrument]
    ) -> ClientResponse[list[OrdersResponse]]:
        """Gets open orders for instruments using parallel requests."""
        self.ensure_secrets_loaded()

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

            if not response.is_successful:
                raise Exception(
                    f"Failed to get orders for {instrument}; {response.err_msg}"
                )

            orders_data = cast(list[HttpOrder], response.data)
            orders = [
                Order(
                    create_time_ms=float(order.time),
                    order_id=str(order.order_id),
                    price=float(order.price),
                    is_buy=order.side.upper() == "BUY",
                    size=float(order.orig_qty),
                    size_remaining=float(order.orig_qty) - float(order.executed_qty),
                    tif=self._tif_map.str_to_enum(
                        order.time_in_force, OrderTimeInForce.GTC
                    ),
                    is_cancelled=order.status == "CANCELED",
                    is_reduce_only=order.reduce_only,
                    client_order_id=order.client_order_id
                    if order.client_order_id
                    else None,
                )
                for order in orders_data
            ]

            return OrdersResponse(
                moments=Moments(),
                venue=self.venue,
                instrument=instrument,
                orders=orders,
            )

        try:
            # Execute all requests in parallel
            orders_responses = await asyncio.gather(
                *[fetch_orders(instrument) for instrument in instruments]
            )

            return ClientResponseSuccess(
                is_successful=True,
                data=orders_responses,
            )
        except Exception as e:
            return ClientResponseFailure(
                is_successful=False,
                err_msg=str(e),
            )

    async def get_position(
        self, instruments: list[Instrument]
    ) -> ClientResponse[list[PositionResponse]]:
        """Gets position data for instruments using parallel requests."""
        self.ensure_secrets_loaded()

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

            if not response.is_successful:
                raise Exception(
                    f"Failed to get position for {instrument}; {response.err_msg}"
                )

            positions_data = cast(list[HttpPosition], response.data)

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

            return PositionResponse(
                moments=Moments(),
                venue=self.venue,
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

            return ClientResponseSuccess(
                is_successful=True,
                data=position_responses,
            )
        except Exception as e:
            return ClientResponseFailure(
                is_successful=False,
                err_msg=str(e),
            )

    async def get_executions(
        self, instruments: list[Instrument]
    ) -> ClientResponse[list[ExecutionResponse]]:
        """Gets executions (user trades) for instruments using parallel requests."""
        self.ensure_secrets_loaded()

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

            if not response.is_successful:
                raise Exception(
                    f"Failed to get executions for {instrument}; {response.err_msg}"
                )

            executions_data = cast(list[HttpUserTrade], response.data)
            executions = [
                Execution(
                    exec_time_ms=float(trade.time),
                    order_id=str(trade.order_id),
                    price=float(trade.price),
                    is_buy=trade.side.upper() == "BUY",
                    size=float(trade.qty),
                    is_maker=trade.is_maker,
                    fee_paid=float(trade.commission),
                    client_order_id=None,  # Not available in this endpoint
                )
                for trade in executions_data
            ]

            return ExecutionResponse(
                moments=Moments(),
                venue=self.venue,
                instrument=instrument,
                executions=executions,
            )

        try:
            # Execute all requests in parallel
            execution_responses = await asyncio.gather(
                *[fetch_executions(instrument) for instrument in instruments]
            )

            return ClientResponseSuccess(
                is_successful=True,
                data=execution_responses,
            )
        except Exception as e:
            return ClientResponseFailure(
                is_successful=False,
                err_msg=str(e),
            )

    async def get_account(self) -> ClientResponse[AccountResponse]:
        """Gets account data from the exchange."""
        self.ensure_secrets_loaded()

        decoder = msgspec.json.Decoder(HttpAccount)

        response = await self.http_client.request(
            method=HttpMethod.GET,
            endpoint=ENDPOINT_GET_ACCOUNT,
            params={},
            data={},
            sign=True,
            decoder=decoder,
        )

        if not response.is_successful:
            return ClientResponseFailure(
                is_successful=False,
                err_msg=response.err_msg,
            )

        account_data = cast(HttpAccount, response.data)

        account_response = AccountResponse(
            moments=Moments(),
            venue=self.venue,
            instrument=Instrument(  # Account is not instrument-specific, but required by schema
                venue=self.venue,
                base="",
                quote="",
                symbol="",
                code=0,
                instrument_type=InstrumentType.PERPETUAL,
            ),
            balance=float(account_data.total_wallet_balance),
            initial_margin=float(account_data.total_initial_margin),
            maintenance_margin=float(account_data.total_maint_margin),
            unrealized_pnl=float(account_data.total_unrealized_pnl),
        )

        return ClientResponseSuccess(
            is_successful=True,
            data=account_response,
        )

    async def get_instrument_info(
        self, instruments: list[Instrument]
    ) -> ClientResponse[list[InstrumentInfoResponse]]:
        """Gets instrument information by fetching all instruments and filtering locally."""

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
                if f.filter_type == "PRICE_FILTER" and f.tick_size is not None:
                    tick_size = float(f.tick_size)
                elif f.filter_type == "LOT_SIZE" and f.step_size is not None:
                    lot_size = float(f.step_size)
                    if f.max_qty is not None:
                        max_maker_size = float(f.max_qty)
                elif f.filter_type == "MARKET_LOT_SIZE" and f.max_qty is not None:
                    max_taker_size = float(f.max_qty)

            return InstrumentInfoResponse(
                moments=Moments(),
                venue=self.venue,
                instrument=Instrument(
                    venue=self.venue,
                    base=symbol.base_asset,
                    quote=symbol.quote_asset,
                    symbol=f"{symbol.base_asset}{symbol.quote_asset}",
                    code=0,
                    instrument_type=InstrumentType.PERPETUAL,
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

            if not response.is_successful:
                raise Exception(f"Failed to get instrument info; {response.err_msg}")

            response_data = cast(BinanceHttpExchangeInformationResponse, response.data)

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
                return ClientResponseSuccess(
                    is_successful=True,
                    data=filtered_infos,
                )
            else:
                return ClientResponseSuccess(
                    is_successful=True,
                    data=all_instrument_infos,
                )
        except Exception as e:
            return ClientResponseFailure(
                is_successful=False,
                err_msg=str(e),
            )

    async def get_open_interest(
        self, instruments: list[Instrument]
    ) -> ClientResponse[list[float]]:
        """Gets the open interest for instruments using parallel requests."""

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

            if not response.is_successful:
                raise Exception(
                    f"Failed to get open interest for {instrument}; {response.err_msg}"
                )

            open_interest_data = cast(BinanceHttpOpenInterestResponse, response.data)
            return float(open_interest_data.open_interest)

        try:
            # Execute all requests in parallel
            open_interests = await asyncio.gather(
                *[fetch_open_interest(instrument) for instrument in instruments]
            )

            return ClientResponseSuccess(
                is_successful=True,
                data=open_interests,
            )
        except Exception as e:
            return ClientResponseFailure(
                is_successful=False,
                err_msg=str(e),
            )

    async def get_listen_key(self) -> ClientResponse[str]:
        """Get listen key from Binance REST API for authenticated websocket connection."""
        self.ensure_secrets_loaded()

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

        if not response.is_successful:
            return ClientResponseFailure(
                is_successful=False,
                err_msg=response.err_msg,
            )

        response_data = cast(dict, response.data)
        listen_key = response_data.get("listenKey", "")
        return ClientResponseSuccess(
            is_successful=True,
            data=listen_key,
        )
