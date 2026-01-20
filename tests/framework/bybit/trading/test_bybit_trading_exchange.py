"""Tests for framework.bybit.trading.exchange.BybitExchange."""

from __future__ import annotations

import pytest

from framework.base.trading.models import (
    AmendOrder,
    CancelAllOrders,
    CancelOrder,
    CreateOrder,
    InstrumentInfoResponse,
    OrderTimeInForce,
    OrderbookResponse,
    OrdersResponse,
    PositionResponse,
    TickerResponse,
    TradesResponse,
)
from framework.bybit.trading.exchange import (
    ENDPOINT_GET_ACCOUNT,
    ENDPOINT_GET_EXECUTIONS,
    ENDPOINT_GET_INSTRUMENTS_INFO,
    ENDPOINT_GET_ORDERBOOK,
    ENDPOINT_GET_ORDERS,
    ENDPOINT_GET_POSITION,
    ENDPOINT_GET_TICKERS,
    ENDPOINT_GET_TRADES,
    ENDPOINT_POST_CANCEL_ALL,
    BybitExchange,
)


class TestBybitExchangePublic:
    """Layer 2: Public endpoint mapping."""

    @pytest.mark.asyncio
    async def test_get_instrument_info(
        self,
        bybit_exchange_mocked: BybitExchange,
        bybit_http_router: dict,
        bybit_payloads,
        bybit_instrument,
    ) -> None:
        """Test instrument info mapping from HTTP payload.

        Args:
            bybit_exchange_mocked: Bybit exchange fixture with stubbed clients.
            bybit_http_router: HTTP router fixture for response control.
            bybit_payloads: Payload factory namespace fixture.
            bybit_instrument: Instrument fixture for Bybit.
        """
        bybit_http_router["responses"][ENDPOINT_GET_INSTRUMENTS_INFO] = (
            bybit_payloads.make_bybit_instruments_info_payload()
        )

        resp = await bybit_exchange_mocked.get_instrument_info([bybit_instrument])

        assert resp.is_successful
        assert isinstance(resp.data, list)
        info = resp.data[0]
        assert isinstance(info, InstrumentInfoResponse)
        assert info.instrument.base == "BTC"
        assert info.tick_size > 0.0
        assert info.lot_size > 0.0

    @pytest.mark.asyncio
    async def test_get_instrument_collection(
        self,
        bybit_exchange_mocked: BybitExchange,
        bybit_http_router: dict,
        bybit_payloads,
    ) -> None:
        """Test instrument collection is built from instrument info.

        Args:
            bybit_exchange_mocked: Bybit exchange fixture with stubbed clients.
            bybit_http_router: HTTP router fixture for response control.
            bybit_payloads: Payload factory namespace fixture.
        """
        bybit_http_router["responses"][ENDPOINT_GET_INSTRUMENTS_INFO] = (
            bybit_payloads.make_bybit_instruments_info_payload()
        )

        resp = await bybit_exchange_mocked.get_instrument_collection()
        assert resp.is_successful
        assert resp.data.get(bybit_exchange_mocked.venue, "BTCUSDT") is not None

    @pytest.mark.asyncio
    async def test_get_ticker(
        self,
        bybit_exchange_mocked: BybitExchange,
        bybit_http_router: dict,
        bybit_payloads,
        bybit_instrument,
    ) -> None:
        """Test ticker mapping from HTTP payload.

        Args:
            bybit_exchange_mocked: Bybit exchange fixture with stubbed clients.
            bybit_http_router: HTTP router fixture for response control.
            bybit_payloads: Payload factory namespace fixture.
            bybit_instrument: Instrument fixture for Bybit.
        """
        bybit_http_router["responses"][ENDPOINT_GET_TICKERS] = (
            bybit_payloads.make_bybit_ticker_payload()
        )

        resp = await bybit_exchange_mocked.get_ticker([bybit_instrument])

        assert resp.is_successful
        ticker = resp.data[0]
        assert isinstance(ticker, TickerResponse)
        assert ticker.instrument.symbol == "BTCUSDT"
        assert ticker.mark_price > 0.0
        assert ticker.index_price > 0.0

    @pytest.mark.asyncio
    async def test_get_orderbook(
        self,
        bybit_exchange_mocked: BybitExchange,
        bybit_http_router: dict,
        bybit_payloads,
        bybit_instrument,
    ) -> None:
        """Test orderbook mapping from HTTP payload.

        Args:
            bybit_exchange_mocked: Bybit exchange fixture with stubbed clients.
            bybit_http_router: HTTP router fixture for response control.
            bybit_payloads: Payload factory namespace fixture.
            bybit_instrument: Instrument fixture for Bybit.
        """
        bybit_http_router["responses"][ENDPOINT_GET_ORDERBOOK] = (
            bybit_payloads.make_bybit_orderbook_payload()
        )

        resp = await bybit_exchange_mocked.get_orderbook([bybit_instrument])

        assert resp.is_successful
        orderbook = resp.data[0]
        assert isinstance(orderbook, OrderbookResponse)
        assert orderbook.bids[0].price > 0.0
        assert orderbook.asks[0].price > 0.0

    @pytest.mark.asyncio
    async def test_get_trades(
        self,
        bybit_exchange_mocked: BybitExchange,
        bybit_http_router: dict,
        bybit_payloads,
        bybit_instrument,
    ) -> None:
        """Test trades mapping from HTTP payload.

        Args:
            bybit_exchange_mocked: Bybit exchange fixture with stubbed clients.
            bybit_http_router: HTTP router fixture for response control.
            bybit_payloads: Payload factory namespace fixture.
            bybit_instrument: Instrument fixture for Bybit.
        """
        bybit_http_router["responses"][ENDPOINT_GET_TRADES] = (
            bybit_payloads.make_bybit_trades_payload()
        )

        resp = await bybit_exchange_mocked.get_trades([bybit_instrument])

        assert resp.is_successful
        trades = resp.data[0]
        assert isinstance(trades, TradesResponse)
        assert trades.trades[0].price > 0.0


class TestBybitExchangeOrderActions:
    """Layer 2: Order action payload mapping."""

    @pytest.mark.asyncio
    async def test_create_order_maps_fields(
        self,
        bybit_exchange_mocked: BybitExchange,
        bybit_ws_router: dict,
        bybit_payloads,
        bybit_instrument,
    ) -> None:
        """Test create_order builds correct WS payload.

        Args:
            bybit_exchange_mocked: Bybit exchange fixture with stubbed clients.
            bybit_ws_router: WS router fixture for response control.
            bybit_payloads: Payload factory namespace fixture.
            bybit_instrument: Instrument fixture for Bybit.
        """
        bybit_ws_router["responses"]["order.create"] = (
            bybit_payloads.make_bybit_ws_submit_result()
        )

        create_order = CreateOrder(
            instrument=bybit_instrument,
            size=1.0,
            is_buy=True,
            price=30000.0,
            is_maker=True,
            tif=OrderTimeInForce.PO,
            reduce_only=False,
            client_order_id="client_1",
        )

        resp = await bybit_exchange_mocked.create_order(create_order)

        assert resp.is_successful
        assert resp.data.order_id == "123456789"
        payload = bybit_ws_router["calls"][-1]["data"]["args"][0]
        assert payload["orderType"] == "Limit"
        assert payload["timeInForce"] == "PostOnly"
        assert payload["side"] == "Buy"
        assert payload["symbol"] == "BTCUSDT"

    @pytest.mark.asyncio
    async def test_amend_order_maps_fields(
        self,
        bybit_exchange_mocked: BybitExchange,
        bybit_ws_router: dict,
        bybit_payloads,
        bybit_instrument,
    ) -> None:
        """Test amend_order builds correct WS payload.

        Args:
            bybit_exchange_mocked: Bybit exchange fixture with stubbed clients.
            bybit_ws_router: WS router fixture for response control.
            bybit_payloads: Payload factory namespace fixture.
            bybit_instrument: Instrument fixture for Bybit.
        """
        bybit_ws_router["responses"]["order.amend"] = (
            bybit_payloads.make_bybit_ws_submit_result(
                order_id="order_1",
                client_order_id="client_1",
            )
        )

        amend_order = AmendOrder(
            instrument=bybit_instrument,
            size=2.0,
            price=30100.0,
            order_id="order_1",
        )

        resp = await bybit_exchange_mocked.amend_order(amend_order)

        assert resp.is_successful
        assert resp.data.order_id == "order_1"
        payload = bybit_ws_router["calls"][-1]["data"]["args"][0]
        assert payload["orderId"] == "order_1"
        assert payload["qty"] == "2.0"

    @pytest.mark.asyncio
    async def test_cancel_order_maps_fields(
        self,
        bybit_exchange_mocked: BybitExchange,
        bybit_ws_router: dict,
        bybit_payloads,
        bybit_instrument,
    ) -> None:
        """Test cancel_order builds correct WS payload.

        Args:
            bybit_exchange_mocked: Bybit exchange fixture with stubbed clients.
            bybit_ws_router: WS router fixture for response control.
            bybit_payloads: Payload factory namespace fixture.
            bybit_instrument: Instrument fixture for Bybit.
        """
        bybit_ws_router["responses"]["order.cancel"] = (
            bybit_payloads.make_bybit_ws_submit_result(
                order_id="order_1",
                client_order_id="client_1",
            )
        )

        cancel_order = CancelOrder(
            instrument=bybit_instrument,
            order_id="order_1",
        )

        resp = await bybit_exchange_mocked.cancel_order(cancel_order)

        assert resp.is_successful
        assert resp.data.order_id == "order_1"
        payload = bybit_ws_router["calls"][-1]["data"]["args"][0]
        assert payload["orderId"] == "order_1"


class TestBybitExchangePrivateEndpoints:
    """Layer 2: Private endpoint mapping."""

    @pytest.mark.asyncio
    async def test_cancel_all_orders(
        self,
        bybit_exchange_mocked: BybitExchange,
        bybit_http_router: dict,
        bybit_instrument,
    ) -> None:
        """Test cancel_all_orders uses signed HTTP request.

        Args:
            bybit_exchange_mocked: Bybit exchange fixture with stubbed clients.
            bybit_http_router: HTTP router fixture for response control.
            bybit_payloads: Payload factory namespace fixture.
            bybit_instrument: Instrument fixture for Bybit.
        """
        bybit_http_router["responses"][ENDPOINT_POST_CANCEL_ALL] = {}

        resp = await bybit_exchange_mocked.cancel_all_orders(
            CancelAllOrders(instrument=bybit_instrument)
        )

        assert resp.is_successful
        assert bybit_http_router["calls"][-1]["sign"] is True

    @pytest.mark.asyncio
    async def test_get_orders(
        self,
        bybit_exchange_mocked: BybitExchange,
        bybit_http_router: dict,
        bybit_payloads,
        bybit_instrument,
    ) -> None:
        """Test open orders mapping from HTTP payload.

        Args:
            bybit_exchange_mocked: Bybit exchange fixture with stubbed clients.
            bybit_http_router: HTTP router fixture for response control.
            bybit_payloads: Payload factory namespace fixture.
            bybit_instrument: Instrument fixture for Bybit.
        """
        bybit_http_router["responses"][ENDPOINT_GET_ORDERS] = (
            bybit_payloads.make_bybit_orders_payload()
        )

        resp = await bybit_exchange_mocked.get_orders([bybit_instrument])

        assert resp.is_successful
        orders = resp.data[0]
        assert isinstance(orders, OrdersResponse)
        assert orders.orders[0].order_id == "order_1"

    @pytest.mark.asyncio
    async def test_get_position(
        self,
        bybit_exchange_mocked: BybitExchange,
        bybit_http_router: dict,
        bybit_payloads,
        bybit_instrument,
    ) -> None:
        """Test position aggregation across entries.

        Args:
            bybit_exchange_mocked: Bybit exchange fixture with stubbed clients.
            bybit_http_router: HTTP router fixture for response control.
            bybit_payloads: Payload factory namespace fixture.
            bybit_instrument: Instrument fixture for Bybit.
        """
        bybit_http_router["responses"][ENDPOINT_GET_POSITION] = (
            bybit_payloads.make_bybit_position_payload(
                positions=[
                    {"size": "2", "avgPrice": "100"},
                    {"size": "1", "avgPrice": "200"},
                ]
            )
        )

        resp = await bybit_exchange_mocked.get_position([bybit_instrument])

        assert resp.is_successful
        position = resp.data[0]
        assert isinstance(position, PositionResponse)
        assert position.size == pytest.approx(3.0)
        assert position.price == pytest.approx(133.3333333333, rel=1e-6)

    @pytest.mark.asyncio
    async def test_get_executions(
        self,
        bybit_exchange_mocked: BybitExchange,
        bybit_http_router: dict,
        bybit_payloads,
        bybit_instrument,
    ) -> None:
        """Test execution mapping from HTTP payload.

        Args:
            bybit_exchange_mocked: Bybit exchange fixture with stubbed clients.
            bybit_http_router: HTTP router fixture for response control.
            bybit_payloads: Payload factory namespace fixture.
            bybit_instrument: Instrument fixture for Bybit.
        """
        bybit_http_router["responses"][ENDPOINT_GET_EXECUTIONS] = (
            bybit_payloads.make_bybit_executions_payload()
        )

        resp = await bybit_exchange_mocked.get_executions([bybit_instrument])

        assert resp.is_successful
        executions = resp.data[0]
        assert executions.executions[0].order_id == "order_1"

    @pytest.mark.asyncio
    async def test_get_account(
        self,
        bybit_exchange_mocked: BybitExchange,
        bybit_http_router: dict,
        bybit_payloads,
    ) -> None:
        """Test account mapping from HTTP payload.

        Args:
            bybit_exchange_mocked: Bybit exchange fixture with stubbed clients.
            bybit_http_router: HTTP router fixture for response control.
            bybit_payloads: Payload factory namespace fixture.
        """
        bybit_http_router["responses"][ENDPOINT_GET_ACCOUNT] = (
            bybit_payloads.make_bybit_account_payload()
        )

        resp = await bybit_exchange_mocked.get_account()

        assert resp.is_successful
        assert resp.data.balance == 1000.0
