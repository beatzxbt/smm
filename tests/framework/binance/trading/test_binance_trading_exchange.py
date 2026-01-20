"""tests.framework.binance.trading.test_binance_trading_exchange"""

from __future__ import annotations

import pytest

from framework.base.common import Instrument, InstrumentType, Venue
from framework.base.trading.models import (
    AmendOrder,
    CancelAllOrders,
    CancelOrder,
    CreateOrder,
    OrderTimeInForce,
    OrderbookResponse,
    OrdersResponse,
    TickerResponse,
    TradesResponse,
)
from framework.binance.trading.exchange import (
    ENDPOINT_DELETE_ALL_ORDERS,
    ENDPOINT_GET_ACCOUNT,
    ENDPOINT_GET_EXECUTIONS,
    ENDPOINT_GET_INSTRUMENT_INFO,
    ENDPOINT_GET_MARK_PRICE,
    ENDPOINT_GET_OPEN_INTEREST,
    ENDPOINT_GET_ORDERBOOK,
    ENDPOINT_GET_ORDERS,
    ENDPOINT_GET_POSITION,
    ENDPOINT_GET_TICKER,
    ENDPOINT_GET_TRADES,
    ENDPOINT_POST_LISTEN_KEY,
    BinanceExchange,
)


def make_instrument() -> Instrument:
    """Create a standard Binance instrument for tests.

    Returns:
        Instrument: BTCUSDT perpetual contract.
    """
    return Instrument(
        venue=Venue.BINANCE_USDM,
        symbol="BTCUSDT",
        base="BTC",
        quote="USDT",
        code=0,
        instrument_type=InstrumentType.PERPETUAL,
    )


class TestBinanceExchangeOrderActions:
    """Layer 2: Order action payload mapping."""

    @pytest.mark.asyncio
    async def test_create_order_maps_fields(
        self,
        binance_exchange_mocked: BinanceExchange,
        binance_ws_router: dict,
        binance_payloads,
    ) -> None:
        """Test create_order builds correct WS payload.

        Args:
            binance_exchange_mocked: Binance exchange fixture with stubbed clients.
            binance_ws_router: WS router fixture for response control.
            binance_payloads: Payload factory namespace fixture.
        """
        binance_ws_router["responses"]["order.place"] = (
            binance_payloads.make_binance_ws_order_response()
        )

        create_order = CreateOrder(
            instrument=make_instrument(),
            size=1.0,
            is_buy=True,
            price=30000.0,
            is_maker=True,
            tif=OrderTimeInForce.GTC,
            reduce_only=False,
            client_order_id="client_1",
        )

        resp = await binance_exchange_mocked.create_order(create_order)

        assert resp.is_successful
        payload = binance_ws_router["calls"][-1]["data"]["params"]
        assert payload["symbol"] == "BTCUSDT"
        assert payload["type"] == "LIMIT"
        assert payload["timeInForce"] == "GTC"

    @pytest.mark.asyncio
    async def test_amend_order_maps_fields(
        self,
        binance_exchange_mocked: BinanceExchange,
        binance_ws_router: dict,
        binance_payloads,
    ) -> None:
        """Test amend_order builds correct WS payload.

        Args:
            binance_exchange_mocked: Binance exchange fixture with stubbed clients.
            binance_ws_router: WS router fixture for response control.
            binance_payloads: Payload factory namespace fixture.
        """
        binance_ws_router["responses"]["order.modify"] = (
            binance_payloads.make_binance_ws_amend_order_response()
        )

        amend_order = AmendOrder(
            instrument=make_instrument(),
            size=2.0,
            price=30100.0,
            order_id="order_1",
        )

        resp = await binance_exchange_mocked.amend_order(amend_order)

        assert resp.is_successful
        payload = binance_ws_router["calls"][-1]["data"]["params"]
        assert payload["orderId"] == "order_1"
        assert payload["qty"] == "2.0"

    @pytest.mark.asyncio
    async def test_cancel_order_maps_fields(
        self,
        binance_exchange_mocked: BinanceExchange,
        binance_ws_router: dict,
        binance_payloads,
    ) -> None:
        """Test cancel_order builds correct WS payload.

        Args:
            binance_exchange_mocked: Binance exchange fixture with stubbed clients.
            binance_ws_router: WS router fixture for response control.
            binance_payloads: Payload factory namespace fixture.
        """
        binance_ws_router["responses"]["order.cancel"] = (
            binance_payloads.make_binance_ws_cancel_order_response()
        )

        cancel_order = CancelOrder(
            instrument=make_instrument(),
            order_id="order_1",
        )

        resp = await binance_exchange_mocked.cancel_order(cancel_order)

        assert resp.is_successful
        payload = binance_ws_router["calls"][-1]["data"]["params"]
        assert payload["orderId"] == "order_1"

    @pytest.mark.asyncio
    async def test_cancel_all_orders_extracts_ids(
        self,
        binance_exchange_mocked: BinanceExchange,
        binance_http_router: dict,
    ) -> None:
        """Test cancel_all_orders extracts IDs from response list.

        Args:
            binance_exchange_mocked: Binance exchange fixture with stubbed clients.
            binance_http_router: HTTP router fixture for response control.
        """
        binance_http_router["responses"][ENDPOINT_DELETE_ALL_ORDERS] = [
            {"orderId": 1, "clientOrderId": "client_1"}
        ]

        resp = await binance_exchange_mocked.cancel_all_orders(
            CancelAllOrders(instrument=make_instrument())
        )

        assert resp.is_successful
        assert resp.data.order_ids == ["1"]
        assert resp.data.client_order_ids == ["client_1"]


class TestBinanceExchangePublicEndpoints:
    """Layer 2: Public endpoint mapping."""

    @pytest.mark.asyncio
    async def test_get_orderbook(
        self,
        binance_exchange_mocked: BinanceExchange,
        binance_http_router: dict,
        binance_payloads,
    ) -> None:
        """Test orderbook mapping from HTTP payload.

        Args:
            binance_exchange_mocked: Binance exchange fixture with stubbed clients.
            binance_http_router: HTTP router fixture for response control.
            binance_payloads: Payload factory namespace fixture.
        """
        binance_http_router["responses"][ENDPOINT_GET_ORDERBOOK] = (
            binance_payloads.make_binance_http_orderbook_response()
        )

        resp = await binance_exchange_mocked.get_orderbook([make_instrument()])

        assert resp.is_successful
        orderbook = resp.data[0]
        assert isinstance(orderbook, OrderbookResponse)
        assert orderbook.bids[0].price > 0.0

    @pytest.mark.asyncio
    async def test_get_ticker(
        self,
        binance_exchange_mocked: BinanceExchange,
        binance_http_router: dict,
        binance_payloads,
    ) -> None:
        """Test ticker combines 24h, mark price, and open interest data.

        Args:
            binance_exchange_mocked: Binance exchange fixture with stubbed clients.
            binance_http_router: HTTP router fixture for response control.
            binance_payloads: Payload factory namespace fixture.
        """
        binance_http_router["responses"][ENDPOINT_GET_TICKER] = (
            binance_payloads.make_binance_http_ticker_24h_response()
        )
        binance_http_router["responses"][ENDPOINT_GET_MARK_PRICE] = (
            binance_payloads.make_binance_http_mark_price_response()
        )
        binance_http_router["responses"][ENDPOINT_GET_OPEN_INTEREST] = (
            binance_payloads.make_binance_http_open_interest_response()
        )

        resp = await binance_exchange_mocked.get_ticker([make_instrument()])

        assert resp.is_successful
        ticker = resp.data[0]
        assert isinstance(ticker, TickerResponse)
        assert ticker.mark_price > 0.0
        assert ticker.open_interest == pytest.approx(1000.0)

    @pytest.mark.asyncio
    async def test_get_trades_returns_client_response(
        self,
        binance_exchange_mocked: BinanceExchange,
        binance_http_router: dict,
        binance_payloads,
    ) -> None:
        """Test get_trades returns ClientResponseSuccess with trades list.

        Args:
            binance_exchange_mocked: Binance exchange fixture with stubbed clients.
            binance_http_router: HTTP router fixture for response control.
            binance_payloads: Payload factory namespace fixture.
        """
        binance_http_router["responses"][ENDPOINT_GET_TRADES] = [
            binance_payloads.make_binance_http_trade_response()
        ]

        resp = await binance_exchange_mocked.get_trades([make_instrument()])
        assert resp.is_successful
        trades = resp.data[0]
        assert isinstance(trades, TradesResponse)

    @pytest.mark.asyncio
    async def test_get_instrument_info_maps_fields(
        self,
        binance_exchange_mocked: BinanceExchange,
        binance_http_router: dict,
        binance_payloads,
    ) -> None:
        """Test instrument info mapping from exchange info.

        Args:
            binance_exchange_mocked: Binance exchange fixture with stubbed clients.
            binance_http_router: HTTP router fixture for response control.
            binance_payloads: Payload factory namespace fixture.
        """
        binance_http_router["responses"][ENDPOINT_GET_INSTRUMENT_INFO] = (
            binance_payloads.make_binance_http_exchange_info_response()
        )

        resp = await binance_exchange_mocked.get_instrument_info([make_instrument()])
        assert resp.is_successful
        assert resp.data[0].tick_size > 0.0


class TestBinanceExchangePrivateEndpoints:
    """Layer 2: Private endpoint mapping."""

    @pytest.mark.asyncio
    async def test_get_orders(
        self,
        binance_exchange_mocked: BinanceExchange,
        binance_http_router: dict,
        binance_payloads,
    ) -> None:
        """Test orders mapping from HTTP payload.

        Args:
            binance_exchange_mocked: Binance exchange fixture with stubbed clients.
            binance_http_router: HTTP router fixture for response control.
            binance_payloads: Payload factory namespace fixture.
        """
        binance_http_router["responses"][ENDPOINT_GET_ORDERS] = [
            binance_payloads.make_binance_http_orders_response()
        ]

        resp = await binance_exchange_mocked.get_orders([make_instrument()])

        assert resp.is_successful
        orders = resp.data[0]
        assert isinstance(orders, OrdersResponse)
        assert orders.orders[0].order_id == "1"

    @pytest.mark.asyncio
    async def test_get_position(
        self,
        binance_exchange_mocked: BinanceExchange,
        binance_http_router: dict,
        binance_payloads,
    ) -> None:
        """Test position aggregation from HTTP payload.

        Args:
            binance_exchange_mocked: Binance exchange fixture with stubbed clients.
            binance_http_router: HTTP router fixture for response control.
            binance_payloads: Payload factory namespace fixture.
        """
        binance_http_router["responses"][ENDPOINT_GET_POSITION] = [
            binance_payloads.make_binance_http_position_response()
        ]

        resp = await binance_exchange_mocked.get_position([make_instrument()])
        assert resp.is_successful

    @pytest.mark.asyncio
    async def test_get_executions(
        self,
        binance_exchange_mocked: BinanceExchange,
        binance_http_router: dict,
        binance_payloads,
    ) -> None:
        """Test executions mapping from HTTP payload.

        Args:
            binance_exchange_mocked: Binance exchange fixture with stubbed clients.
            binance_http_router: HTTP router fixture for response control.
            binance_payloads: Payload factory namespace fixture.
        """
        binance_http_router["responses"][ENDPOINT_GET_EXECUTIONS] = [
            binance_payloads.make_binance_http_user_trade_response()
        ]

        resp = await binance_exchange_mocked.get_executions([make_instrument()])

        assert resp.is_successful
        assert resp.data[0].executions[0].order_id == "1"

    @pytest.mark.asyncio
    async def test_get_open_interest(
        self,
        binance_exchange_mocked: BinanceExchange,
        binance_http_router: dict,
        binance_payloads,
    ) -> None:
        """Test open interest mapping from HTTP payload.

        Args:
            binance_exchange_mocked: Binance exchange fixture with stubbed clients.
            binance_http_router: HTTP router fixture for response control.
            binance_payloads: Payload factory namespace fixture.
        """
        binance_http_router["responses"][ENDPOINT_GET_OPEN_INTEREST] = (
            binance_payloads.make_binance_http_open_interest_response()
        )

        resp = await binance_exchange_mocked.get_open_interest([make_instrument()])
        assert resp.is_successful
        assert resp.data[0] == pytest.approx(1000.0)

    @pytest.mark.asyncio
    async def test_get_listen_key(
        self,
        binance_exchange_mocked: BinanceExchange,
        binance_http_router: dict,
        binance_payloads,
    ) -> None:
        """Test listen key extraction from HTTP payload.

        Args:
            binance_exchange_mocked: Binance exchange fixture with stubbed clients.
            binance_http_router: HTTP router fixture for response control.
            binance_payloads: Payload factory namespace fixture.
        """
        binance_http_router["responses"][ENDPOINT_POST_LISTEN_KEY] = (
            binance_payloads.make_binance_listen_key_response()
        )

        resp = await binance_exchange_mocked.get_listen_key()
        assert resp.is_successful
        assert resp.data == "listen_key"

    @pytest.mark.asyncio
    async def test_get_account(
        self,
        binance_exchange_mocked: BinanceExchange,
        binance_http_router: dict,
        binance_payloads,
    ) -> None:
        """Test account mapping from HTTP payload.

        Args:
            binance_exchange_mocked: Binance exchange fixture with stubbed clients.
            binance_http_router: HTTP router fixture for response control.
            binance_payloads: Payload factory namespace fixture.
        """
        binance_http_router["responses"][ENDPOINT_GET_ACCOUNT] = (
            binance_payloads.make_binance_http_account_response()
        )

        resp = await binance_exchange_mocked.get_account()
        assert resp.is_successful
