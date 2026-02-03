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
from mm_toolbox.time import time_ms
from framework.base.stream.models import Moments, Trade, Execution
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
from framework.bybit.trading.client import BybitHttpClient, BybitWsClient


RECV_WINDOW = 5000

ENDPOINT_GET_TRADES = "/v5/market/recent-trade"
ENDPOINT_GET_ORDERBOOK = "/v5/market/orderbook"
ENDPOINT_GET_TICKERS = "/v5/market/tickers"
ENDPOINT_GET_ORDERS = "/v5/order/realtime"
ENDPOINT_GET_POSITION = "/v5/position/list"
ENDPOINT_GET_EXECUTIONS = "/v5/execution/list"
ENDPOINT_GET_ACCOUNT = "/v5/account/wallet-balance"
ENDPOINT_GET_INSTRUMENTS_INFO = "/v5/market/instruments-info"
ENDPOINT_POST_CANCEL_ALL = "/v5/order/cancel-all"


class BybitExchange(Exchange):
    def __init__(self, logger: Logger, load_secrets: bool) -> None:
        super().__init__(
            venue=Venue.BYBIT,
            logger=logger,
            load_secrets=load_secrets,
            http_client=BybitHttpClient(
                logger=logger,
                load_secrets=load_secrets,
            ),
            ws_client=BybitWsClient(
                logger=logger,
                load_secrets=load_secrets,
            ),
        )

        self._tif_map = EnumMap(
            enum_class=OrderTimeInForce,
            mapping={
                OrderTimeInForce.GTC: "GTC",
                OrderTimeInForce.IOC: "IOC",
                OrderTimeInForce.FOK: "FOK",
                OrderTimeInForce.PO: "PostOnly",
            },
        )

    def instrument_to_symbol(self, instrument: Instrument) -> str:
        return f"{instrument.base}{instrument.quote}".upper()

    async def get_instrument_collection(self) -> ClientResponse[InstrumentCollection]:
        """Gets all instruments for the exchange."""
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
        self.ensure_secrets_loaded()
        self.ensure_running(ws_only=True)

        params: dict[str, str | bool] = {
            "category": "linear",
            "symbol": self.instrument_to_symbol(create_order.instrument),
            "side": "Buy" if create_order.is_buy else "Sell",
            "orderType": "Limit" if create_order.is_maker else "Market",
            "timeInForce": self._tif_map.enum_to_str(create_order.tif),
            "qty": str(create_order.size),
            "reduceOnly": create_order.reduce_only,
        }
        if create_order.client_order_id:
            params["orderLinkId"] = create_order.client_order_id
        if create_order.is_maker and create_order.price is not None:
            params["price"] = str(create_order.price)

        payload = {
            "op": "order.create",
            "header": {
                "X-BAPI-TIMESTAMP": int(time_ms()),
                "X-BAPI-RECV-WINDOW": RECV_WINDOW,
            },
            "args": [params],
        }

        response = await self.ws_client.submit(
            data=payload, decoder=msgspec.json.Decoder(dict)
        )
        if not response.is_successful:
            return ClientResponseFailure(
                is_successful=False, err_no=response.err_no, err_msg=response.err_msg
            )

        result = cast(dict, response.data)
        order_id = str(result.get("orderId", ""))
        cloid = result.get("orderLinkId")
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
        self.ensure_secrets_loaded()
        self.ensure_running(ws_only=True)

        params: dict[str, str] = {
            "category": "linear",
            "symbol": self.instrument_to_symbol(amend_order.instrument),
        }
        if amend_order.order_id:
            params["orderId"] = amend_order.order_id
        if amend_order.client_order_id:
            params["orderLinkId"] = amend_order.client_order_id
        params["qty"] = str(amend_order.size)
        if amend_order.price is not None:
            params["price"] = str(amend_order.price)

        payload = {
            "op": "order.amend",
            "header": {
                "X-BAPI-TIMESTAMP": int(time_ms()),
                "X-BAPI-RECV-WINDOW": RECV_WINDOW,
            },
            "args": [params],
        }

        response = await self.ws_client.submit(
            data=payload, decoder=msgspec.json.Decoder(dict)
        )
        if not response.is_successful:
            return ClientResponseFailure(
                is_successful=False, err_no=response.err_no, err_msg=response.err_msg
            )

        result = cast(dict, response.data)
        order_id = str(result.get("orderId", ""))
        cloid = result.get("orderLinkId")
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
        self.ensure_secrets_loaded()
        self.ensure_running(ws_only=True)

        params: dict[str, str] = {
            "category": "linear",
            "symbol": self.instrument_to_symbol(cancel_order.instrument),
        }
        if cancel_order.order_id:
            params["orderId"] = cancel_order.order_id
        if cancel_order.client_order_id:
            params["orderLinkId"] = cancel_order.client_order_id

        payload = {
            "op": "order.cancel",
            "header": {
                "X-BAPI-TIMESTAMP": int(time_ms()),
                "X-BAPI-RECV-WINDOW": RECV_WINDOW,
            },
            "args": [params],
        }

        response = await self.ws_client.submit(
            data=payload, decoder=msgspec.json.Decoder(dict)
        )
        if not response.is_successful:
            return ClientResponseFailure(
                is_successful=False, err_no=response.err_no, err_msg=response.err_msg
            )

        result = cast(dict, response.data)
        order_id = str(result.get("orderId", ""))
        cloid = result.get("orderLinkId")
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
        self.ensure_secrets_loaded()
        self.ensure_running(http_only=True)

        params = {
            "category": "linear",
            "symbol": self.instrument_to_symbol(cancel_all_orders.instrument),
        }
        decoder = msgspec.json.Decoder(dict)
        response = await self.http_client.request(
            method=HttpMethod.POST,
            endpoint=ENDPOINT_POST_CANCEL_ALL,
            params=params,
            data={},
            sign=True,
            decoder=decoder,
        )

        if not response.is_successful:
            return ClientResponseFailure(
                is_successful=False, err_no=response.err_no, err_msg=response.err_msg
            )

        base_resp = CancelAllOrdersResponse(
            moments=None,  # type: ignore[arg-type]
            venue=self.venue,
            instrument=cancel_all_orders.instrument,
            trigger=cancel_all_orders,
        )
        return ClientResponseSuccess(is_successful=True, data=base_resp)

    async def get_trades(
        self, instruments: list[Instrument]
    ) -> ClientResponse[list[TradesResponse]]:
        async def fetch_trades(instrument: Instrument) -> TradesResponse:
            params = {
                "category": "linear",
                "symbol": self.instrument_to_symbol(instrument),
                "limit": 200,
            }
            decoder = msgspec.json.Decoder(dict)
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
            payload = cast(dict, response.data)
            items = payload.get("list", payload.get("result", {}).get("list", []))
            trades = [
                Trade(
                    time_ms=int(t.get("time", 0)),
                    price=float(t.get("price", 0.0)),
                    is_buy=(t.get("side", "Buy") == "Buy"),
                    size=float(t.get("size", 0.0)),
                )
                for t in items[::-1]
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
        async def fetch_orderbook(instrument: Instrument) -> OrderbookResponse:
            params = {
                "category": "linear",
                "symbol": self.instrument_to_symbol(instrument),
                "limit": 200,
            }
            decoder = msgspec.json.Decoder(dict)
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
            payload = cast(dict, response.data)
            bids = payload.get("b") or payload.get("result", {}).get("b", [])
            asks = payload.get("a") or payload.get("result", {}).get("a", [])
            bid_lvls = [
                OrderbookLevel(price=float(px), size=float(sz)) for px, sz in bids
            ]
            ask_lvls = [
                OrderbookLevel(price=float(px), size=float(sz)) for px, sz in asks
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
        async def fetch_ticker(instrument: Instrument) -> TickerResponse:
            params = {
                "category": "linear",
                "symbol": self.instrument_to_symbol(instrument),
            }
            decoder = msgspec.json.Decoder(dict)
            response = await self.http_client.request(
                method=HttpMethod.GET,
                endpoint=ENDPOINT_GET_TICKERS,
                params=params,
                data={},
                sign=False,
                decoder=decoder,
            )
            if not response.is_successful:
                raise RuntimeError(response.err_msg)
            payload = cast(dict, response.data)
            item = (payload.get("list") or payload.get("result", {}).get("list", [{}]))[
                0
            ]
            return TickerResponse(
                moments=Moments(),
                venue=self.venue,
                instrument=instrument,
                mark_price=float(item.get("markPrice", 0.0)),
                index_price=float(item.get("indexPrice", 0.0)),
                funding_rate=float(item.get("fundingRate", 0.0)),
                next_funding_time_ms=int(item.get("nextFundingTime", 0)),
                open_interest=float(item.get("openInterest", 0.0))
                if item.get("openInterest") is not None
                else None,
                avg_volume_24h=float(item.get("volume24h", 0.0))
                if item.get("volume24h") is not None
                else None,
                price_chg_24h=float(item.get("price24hPcnt", 0.0))
                if item.get("price24hPcnt") is not None
                else None,
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
        decoder = msgspec.json.Decoder(dict)
        response = await self.http_client.request(
            method=HttpMethod.GET,
            endpoint=ENDPOINT_GET_INSTRUMENTS_INFO,
            params={"category": "linear"},
            data={},
            sign=False,
            decoder=decoder,
        )
        if not response.is_successful:
            return ClientResponseFailure(is_successful=False, err_msg=response.err_msg)
        payload = cast(dict, response.data)
        symbols = payload.get("list") or payload.get("result", {}).get("list", [])

        results: list[InstrumentInfoResponse] = []
        for s in symbols:
            if s.get("contractType", "LinearPerpetual") != "LinearPerpetual":
                continue
            tick_size = float(s.get("priceFilter", {}).get("tickSize", 0.0))
            lot_size = float(s.get("lotSizeFilter", {}).get("qtyStep", 0.0))
            info = InstrumentInfoResponse(
                moments=Moments(),
                venue=self.venue,
                instrument=Instrument(
                    venue=self.venue,
                    base=s.get("baseCoin", ""),
                    quote=s.get("quoteCoin", ""),
                    symbol=f"{s.get('baseCoin', '')}{s.get('quoteCoin', '')}".upper(),
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
                r
                for r in results
                if f"{r.instrument.base}{r.instrument.quote}".upper() in wanted
            ]
        return ClientResponseSuccess(is_successful=True, data=results)

    async def get_orders(
        self, instruments: list[Instrument]
    ) -> ClientResponse[list[OrdersResponse]]:
        self.ensure_secrets_loaded()

        async def fetch_orders(instrument: Instrument) -> OrdersResponse:
            params = {
                "category": "linear",
                "symbol": self.instrument_to_symbol(instrument),
            }
            decoder = msgspec.json.Decoder(dict)
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
            payload = cast(dict, response.data)
            items = payload.get("list") or payload.get("result", {}).get("list", [])
            orders = [
                Order(
                    create_time_ms=float(it.get("createTime", 0)),
                    order_id=str(it.get("orderId", "")),
                    price=float(it.get("price", 0.0)),
                    is_buy=(it.get("side", "Buy") == "Buy"),
                    size=float(it.get("qty", 0.0)),
                    size_remaining=max(
                        0.0,
                        float(it.get("qty", 0.0)) - float(it.get("cumExecQty", 0.0)),
                    ),
                    tif=self._tif_map.str_to_enum(
                        it.get("timeInForce", "GTC"), OrderTimeInForce.GTC
                    ),
                    is_cancelled=(
                        it.get("orderStatus", "New")
                        in ["Cancelled", "Rejected", "Deactivated"]
                    ),
                    is_reduce_only=bool(it.get("reduceOnly", False)),
                    client_order_id=it.get("orderLinkId"),
                )
                for it in items
            ]
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
        self.ensure_secrets_loaded()

        async def fetch_position(instrument: Instrument) -> PositionResponse:
            params = {
                "category": "linear",
                "symbol": self.instrument_to_symbol(instrument),
            }
            decoder = msgspec.json.Decoder(dict)
            response = await self.http_client.request(
                method=HttpMethod.GET,
                endpoint=ENDPOINT_GET_POSITION,
                params=params,
                data={},
                sign=True,
                decoder=decoder,
            )
            if not response.is_successful:
                raise RuntimeError(response.err_msg)
            payload = cast(dict, response.data)
            items = payload.get("list") or payload.get("result", {}).get("list", [])
            total_size = 0.0
            w_notional = 0.0
            for it in items:
                sz = float(it.get("size", 0.0))
                if sz == 0:
                    continue
                px = float(it.get("avgPrice", 0.0))
                total_size += sz
                w_notional += abs(sz) * px
            avg_px = (w_notional / abs(total_size)) if total_size != 0 else 0.0
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
        self.ensure_secrets_loaded()

        async def fetch_exec(instrument: Instrument) -> ExecutionResponse:
            params = {
                "category": "linear",
                "symbol": self.instrument_to_symbol(instrument),
                "limit": 200,
            }
            decoder = msgspec.json.Decoder(dict)
            response = await self.http_client.request(
                method=HttpMethod.GET,
                endpoint=ENDPOINT_GET_EXECUTIONS,
                params=params,
                data={},
                sign=True,
                decoder=decoder,
            )
            if not response.is_successful:
                raise RuntimeError(response.err_msg)
            payload = cast(dict, response.data)
            items = payload.get("list") or payload.get("result", {}).get("list", [])
            executions = [
                Execution(
                    exec_time_ms=float(it.get("execTime", 0)),
                    order_id=str(it.get("orderId", "")),
                    price=float(it.get("execPrice", 0.0)),
                    is_buy=(it.get("side", "Buy") == "Buy"),
                    size=float(it.get("execQty", 0.0)),
                    is_maker=bool(it.get("isMaker", False)),
                    fee_paid=float(it.get("execFee", 0.0)),
                    client_order_id=it.get("orderLinkId"),
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
        self.ensure_secrets_loaded()
        decoder = msgspec.json.Decoder(dict)
        response = await self.http_client.request(
            method=HttpMethod.GET,
            endpoint=ENDPOINT_GET_ACCOUNT,
            params={"accountType": "UNIFIED"},
            data={},
            sign=True,
            decoder=decoder,
        )
        if not response.is_successful:
            return ClientResponseFailure(is_successful=False, err_msg=response.err_msg)
        payload = cast(dict, response.data)
        item = (payload.get("list") or payload.get("result", {}).get("list", [{}]))[0]
        acc = AccountResponse(
            moments=Moments(),
            venue=self.venue,
            instrument=Instrument.empty(),
            balance=float(item.get("totalEquity", 0.0)),
            initial_margin=float(item.get("accountIMRate", 0.0)),
            maintenance_margin=float(item.get("accountMMRate", 0.0)),
            unrealized_pnl=float(item.get("totalPerpUPL", 0.0)),
        )
        return ClientResponseSuccess(is_successful=True, data=acc)
