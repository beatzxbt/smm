"""
Bybit-specific test fixtures and utilities.

Provides fixtures for Bybit exchange, clients, instruments, and mock data factories.
These fixtures are automatically available to all tests in the bybit/ directory.
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import msgspec
import pytest

from framework.base.common import Asset, Instrument, InstrumentType, Symbol, Venue
from framework.base.trading.models import ClientResponseFailure, ClientResponseSuccess


@pytest.fixture
def bybit_instrument():
    """Standard BTC/USDT perpetual for Bybit tests.

    Returns:
        Instrument: BTCUSDT perpetual contract on Bybit.
    """
    return Instrument(
        venue=Venue.BYBIT,
        base=Asset("BTC"),
        quote=Asset("USDT"),
        symbol=Symbol("BTCUSDT"),
        code=0,
        instrument_type=InstrumentType.PERPETUAL,
        tick_size=0.01,
        lot_size=0.001,
    )


@pytest.fixture
def bybit_exchange_public(test_logger):
    """Bybit exchange without secrets (public API only).

    Args:
        test_logger: Logger fixture from root conftest.

    Returns:
        BybitExchange: Exchange instance configured for public endpoints.
    """
    from framework.bybit.trading.exchange import BybitExchange

    return BybitExchange(logger=test_logger, load_secrets=False)


@pytest.fixture
def bybit_http_client(test_logger):
    """Bybit HTTP client for testing.

    Args:
        test_logger: Logger fixture from root conftest.

    Returns:
        BybitHttpClient: HTTP client with test credentials.
    """
    from framework.bybit.trading.client import BybitHttpClient
    from framework.bybit.trading.time_sync import BybitTimeSync

    return BybitHttpClient(
        logger=test_logger,
        time_sync=BybitTimeSync(venue=Venue.BYBIT, logger=test_logger),
        load_secrets=False,
        key="test_api_key",
        secret="test_api_secret",
    )


@pytest.fixture
def bybit_ws_client(test_logger):
    """Bybit WebSocket client for testing.

    Args:
        test_logger: Logger fixture from root conftest.

    Returns:
        BybitWsClient: WebSocket client with test credentials.
    """
    from framework.bybit.trading.client import BybitWsClient
    from framework.bybit.trading.time_sync import BybitTimeSync

    return BybitWsClient(
        logger=test_logger,
        time_sync=BybitTimeSync(venue=Venue.BYBIT, logger=test_logger),
        load_secrets=False,
        key="test_api_key",
        secret="test_api_secret",
    )


# Mock data factory functions


def make_bybit_ws_order_response(
    req_id: str = "test_req_123",
    status: int = 0,
    order_id: str = "123456789",
    symbol: str = "BTCUSDT",
    side: str = "Buy",
    order_type: str = "Limit",
    price: str = "30000.00",
    qty: str = "0.01",
) -> dict:
    """Create mock Bybit WebSocket order response.

    Args:
        req_id: Request ID.
        status: Response status (0 = success).
        order_id: Order ID from exchange.
        symbol: Trading symbol.
        side: Order side (Buy/Sell).
        order_type: Order type (Limit/Market).
        price: Order price.
        qty: Order quantity.

    Returns:
        dict: Mock Bybit WS order response payload.
    """
    return {
        "id": req_id,
        "status": status,
        "result": {
            "orderId": order_id,
            "orderLinkId": f"client_{order_id}",
            "symbol": symbol,
            "status": "Created",
            "side": side,
            "orderType": order_type,
            "price": price,
            "avgPrice": "0",
            "qty": qty,
            "cumExecQty": "0",
            "cumExecValue": "0",
            "cumExecFee": "0",
            "timeInForce": "GTC",
            "orderStatus": "Created",
            "reduceOnly": False,
            "closeOnTrigger": False,
            "createdTime": "1234567890000",
            "updatedTime": "1234567890000",
        },
    }


def make_bybit_ws_submit_result(
    order_id: str = "123456789",
    client_order_id: str = "client_123456789",
) -> dict:
    """Create a mock Bybit WS submit result payload.

    Args:
        order_id: Order ID from the exchange.
        client_order_id: Client-generated order ID.

    Returns:
        dict: Mock result payload matching submit() expectations.
    """
    return {"orderId": order_id, "orderLinkId": client_order_id}


def make_bybit_ticker_msg(
    symbol: str = "BTCUSDT",
    mark_price: str = "30000.00",
    index_price: str = "29999.50",
    funding_rate: str = "0.0001",
) -> dict:
    """Create mock Bybit ticker stream message.

    Args:
        symbol: Trading symbol.
        mark_price: Mark price.
        index_price: Index price.
        funding_rate: Funding rate.

    Returns:
        dict: Mock Bybit ticker message payload.
    """
    return {
        "topic": f"tickers.{symbol}",
        "type": "snapshot",
        "ts": 1234567890000,
        "data": {
            "symbol": symbol,
            "tickDirection": "PlusTick",
            "price24hPcnt": "0.0123",
            "lastPrice": mark_price,
            "prevPrice24h": "29500.00",
            "highPrice24h": "31000.00",
            "lowPrice24h": "29000.00",
            "prevPrice1h": "29800.00",
            "markPrice": mark_price,
            "indexPrice": index_price,
            "openInterest": "12345.67",
            "openInterestValue": "370370100.00",
            "turnover24h": "567890123.45",
            "volume24h": "18923.45",
            "nextFundingTime": "1234598400000",
            "fundingRate": funding_rate,
            "bid1Price": "29999.00",
            "bid1Size": "1.234",
            "ask1Price": "30001.00",
            "ask1Size": "2.345",
        },
    }


def make_bybit_instruments_info_payload(
    base_coin: str = "BTC",
    quote_coin: str = "USDT",
    contract_type: str = "LinearPerpetual",
    tick_size: str = "0.1",
    lot_size: str = "0.001",
) -> dict:
    """Create a mock instruments-info response payload.

    Args:
        base_coin: Base asset symbol.
        quote_coin: Quote asset symbol.
        contract_type: Bybit contract type string.
        tick_size: Tick size string.
        lot_size: Lot size string.

    Returns:
        dict: Mock response payload for instruments-info.
    """
    return {
        "list": [
            {
                "contractType": contract_type,
                "baseCoin": base_coin,
                "quoteCoin": quote_coin,
                "priceFilter": {"tickSize": tick_size},
                "lotSizeFilter": {"qtyStep": lot_size},
            }
        ]
    }


def make_bybit_ticker_payload(
    mark_price: str = "30000",
    index_price: str = "29990",
    funding_rate: str = "0.0001",
    next_funding_time: str = "1234567890",
    open_interest: str = "1000",
    volume_24h: str = "5000",
    price_24h_pcnt: str = "0.01",
) -> dict:
    """Create a mock ticker response payload.

    Args:
        mark_price: Mark price string.
        index_price: Index price string.
        funding_rate: Funding rate string.
        next_funding_time: Next funding timestamp string.
        open_interest: Open interest string.
        volume_24h: 24h volume string.
        price_24h_pcnt: 24h price change percent string.

    Returns:
        dict: Mock response payload for ticker endpoint.
    """
    return {
        "list": [
            {
                "markPrice": mark_price,
                "indexPrice": index_price,
                "fundingRate": funding_rate,
                "nextFundingTime": next_funding_time,
                "openInterest": open_interest,
                "volume24h": volume_24h,
                "price24hPcnt": price_24h_pcnt,
            }
        ]
    }


def make_bybit_orderbook_payload(
    bids: list[list[str]] | None = None,
    asks: list[list[str]] | None = None,
) -> dict:
    """Create a mock orderbook response payload.

    Args:
        bids: List of [price, size] bid levels.
        asks: List of [price, size] ask levels.

    Returns:
        dict: Mock response payload for orderbook endpoint.
    """
    if bids is None:
        bids = [["30000", "1.0"]]
    if asks is None:
        asks = [["30001", "1.0"]]
    return {"b": bids, "a": asks}


def make_bybit_trades_payload(
    trades: list[dict] | None = None,
) -> dict:
    """Create a mock trades response payload.

    Args:
        trades: List of trade dicts with time/price/side/size.

    Returns:
        dict: Mock response payload for trades endpoint.
    """
    if trades is None:
        trades = [
            {"time": "1234567890", "price": "30000", "side": "Buy", "size": "0.1"}
        ]
    return {"list": trades}


def make_bybit_orders_payload(
    orders: list[dict] | None = None,
) -> dict:
    """Create a mock orders response payload.

    Args:
        orders: List of order dicts with required fields.

    Returns:
        dict: Mock response payload for orders endpoint.
    """
    if orders is None:
        orders = [
            {
                "createTime": "1234567890",
                "orderId": "order_1",
                "price": "30000",
                "side": "Buy",
                "qty": "1",
                "cumExecQty": "0",
                "timeInForce": "GTC",
                "orderStatus": "New",
                "reduceOnly": False,
                "orderLinkId": "client_1",
            }
        ]
    return {"list": orders}


def make_bybit_position_payload(
    positions: list[dict] | None = None,
) -> dict:
    """Create a mock position response payload.

    Args:
        positions: List of position dicts with size/avgPrice fields.

    Returns:
        dict: Mock response payload for position endpoint.
    """
    if positions is None:
        positions = [{"size": "1", "avgPrice": "30000"}]
    return {"list": positions}


def make_bybit_executions_payload(
    executions: list[dict] | None = None,
) -> dict:
    """Create a mock executions response payload.

    Args:
        executions: List of execution dicts with execTime/price/qty fields.

    Returns:
        dict: Mock response payload for executions endpoint.
    """
    if executions is None:
        executions = [
            {
                "execTime": "1234567890",
                "orderId": "order_1",
                "execPrice": "30000",
                "side": "Buy",
                "execQty": "1",
                "isMaker": False,
                "execFee": "0.01",
                "orderLinkId": "client_1",
            }
        ]
    return {"list": executions}


def make_bybit_account_payload(
    total_equity: str = "1000",
    account_im_rate: str = "0.1",
    account_mm_rate: str = "0.05",
    total_perp_upl: str = "10",
) -> dict:
    """Create a mock account response payload.

    Args:
        total_equity: Total equity string.
        account_im_rate: Initial margin rate string.
        account_mm_rate: Maintenance margin rate string.
        total_perp_upl: Total unrealized PnL string.

    Returns:
        dict: Mock response payload for account endpoint.
    """
    return {
        "list": [
            {
                "totalEquity": total_equity,
                "accountIMRate": account_im_rate,
                "accountMMRate": account_mm_rate,
                "totalPerpUPL": total_perp_upl,
            }
        ]
    }


def make_bybit_orderbook_msg(
    symbol: str = "BTCUSDT",
    bids: list[tuple[str, str]] | None = None,
    asks: list[tuple[str, str]] | None = None,
) -> dict:
    """Create mock Bybit orderbook stream message.

    Args:
        symbol: Trading symbol.
        bids: List of (price, size) tuples for bids.
        asks: List of (price, size) tuples for asks.

    Returns:
        dict: Mock Bybit orderbook message payload.
    """
    if bids is None:
        bids = [("29999.00", "1.5"), ("29998.00", "2.3")]
    if asks is None:
        asks = [("30001.00", "1.2"), ("30002.00", "0.8")]

    return {
        "topic": f"orderbook.1.{symbol}",
        "type": "snapshot",
        "ts": 1234567890000,
        "data": {
            "s": symbol,
            "b": [{"price": price, "size": size} for price, size in bids],
            "a": [{"price": price, "size": size} for price, size in asks],
            "u": 123456,
            "seq": 7890123,
        },
    }


def make_bybit_position_msg(
    symbol: str = "BTCUSDT",
    side: str = "Buy",
    size: str = "0.5",
    entry_price: str = "30000.00",
) -> dict:
    """Create mock Bybit position stream message.

    Args:
        symbol: Trading symbol.
        side: Position side (Buy/Sell).
        size: Position size.
        entry_price: Entry price.

    Returns:
        dict: Mock Bybit position message payload.
    """
    return {
        "topic": "position",
        "id": "pos_update_123",
        "creationTime": 1234567890000,
        "data": [
            {
                "positionIdx": 0,
                "tradeMode": 0,
                "riskId": 1,
                "riskLimitValue": "2000000",
                "symbol": symbol,
                "side": side,
                "size": size,
                "entryPrice": entry_price,
                "leverage": "10",
                "positionValue": "15000.00",
                "positionBalance": "1500.00",
                "markPrice": "30100.00",
                "positionIM": "1500.00",
                "positionMM": "75.00",
                "takeProfit": "0",
                "stopLoss": "0",
                "trailingStop": "0",
                "unrealisedPnl": "50.00",
                "cumRealisedPnl": "-10.00",
                "createdTime": "1234567800000",
                "updatedTime": "1234567890000",
            }
        ],
    }


def make_bybit_private_order_message(
    symbol: str = "BTCUSDT",
    order_id: str = "order_1",
) -> dict:
    """Create a mock Bybit private order stream message.

    Args:
        symbol: Trading symbol.
        order_id: Order ID string.

    Returns:
        dict: Mock Bybit private order message payload.
    """
    return {
        "topic": "order",
        "type": "snapshot",
        "ts": 1234567890000,
        "data": [
            {
                "symbol": symbol,
                "orderId": order_id,
                "side": "Buy",
                "orderType": "Limit",
                "cancelType": "",
                "price": "30000.00",
                "qty": "1",
                "timeInForce": "GTC",
                "orderStatus": "New",
                "orderLinkId": "client_1",
                "lastPriceOnCreated": "30000.00",
                "reduceOnly": False,
                "leavesQty": "1",
                "leavesValue": "30000",
                "cumExecQty": "0",
                "cumExecValue": "0",
                "avgPrice": "0",
                "blockTradeId": "",
                "positionIdx": 0,
                "cumExecFee": "0",
                "closedPnl": "0",
                "createdTime": "1234567890000",
                "updatedTime": "1234567890000",
                "rejectReason": "",
                "stopOrderType": "",
                "triggerDirection": 0,
                "triggerBy": "",
                "closeOnTrigger": False,
                "category": "linear",
                "placeType": "",
            }
        ],
    }


def make_bybit_private_execution_message(
    symbol: str = "BTCUSDT",
    order_id: str = "order_1",
) -> dict:
    """Create a mock Bybit private execution stream message.

    Args:
        symbol: Trading symbol.
        order_id: Order ID string.

    Returns:
        dict: Mock Bybit private execution message payload.
    """
    return {
        "topic": "execution",
        "type": "snapshot",
        "ts": 1234567890000,
        "data": [
            {
                "category": "linear",
                "symbol": symbol,
                "closedSize": "0",
                "execFee": "0.01",
                "execId": "exec_1",
                "execPrice": "30000.00",
                "execQty": "1",
                "execType": "Trade",
                "execValue": "0",
                "feeRate": "0.0001",
                "markPrice": "30000.00",
                "indexPrice": "29999.50",
                "underlyingPrice": "29999.00",
                "leavesQty": "0",
                "orderId": order_id,
                "orderLinkId": "client_1",
                "orderPrice": "30000.00",
                "orderQty": "1",
                "orderType": "Limit",
                "stopOrderType": "",
                "side": "Buy",
                "execTime": "1234567890000",
                "isLeverage": "0",
                "isMaker": True,
                "seq": 1,
                "marketUnit": "",
                "execPnl": "0",
                "createType": "CreateByUser",
            }
        ],
    }


def make_bybit_private_position_message(
    symbol: str = "BTCUSDT",
    side: str = "Buy",
    size: str = "1",
) -> dict:
    """Create a mock Bybit private position stream message.

    Args:
        symbol: Trading symbol.
        side: Position side.
        size: Position size string.

    Returns:
        dict: Mock Bybit private position message payload.
    """
    return {
        "topic": "position",
        "type": "snapshot",
        "ts": 1234567890000,
        "data": [
            {
                "positionIdx": 0,
                "tradeMode": 0,
                "riskId": 1,
                "riskLimitValue": "2000000",
                "symbol": symbol,
                "side": side,
                "size": size,
                "entryPrice": "30000.00",
                "leverage": "10",
                "positionValue": "15000.00",
                "positionBalance": "1500.00",
                "markPrice": "30100.00",
                "positionIm": "1500.00",
                "positionImByMp": "1500.00",
                "positionMm": "75.00",
                "positionMmByMp": "75.00",
                "takeProfit": "0",
                "stopLoss": "0",
                "trailingStop": "0",
                "unrealisedPnl": "50.00",
                "curRealisedPnl": "0.00",
                "cumRealisedPnl": "-10.00",
                "sessionAvgPrice": "30000.00",
                "createdTime": "1234567800000",
                "updatedTime": "1234567890000",
                "tpslMode": "Full",
                "liqPrice": "27000.00",
                "bustPrice": "26500.00",
                "category": "linear",
                "positionStatus": "Normal",
                "adlRankIndicator": 2,
                "autoAddMargin": 0,
                "leverageSysUpdatedTime": "1234567000000",
                "mmrSysUpdatedTime": "1234567000000",
                "seq": 123456,
                "isReduceOnly": False,
            }
        ],
    }


def make_bybit_private_wallet_message(
    total_equity: str = "1000",
    account_im_rate: str = "0.1",
    account_mm_rate: str = "0.05",
    total_perp_upl: str = "10",
) -> dict:
    """Create a mock Bybit private wallet stream message.

    Args:
        total_equity: Total equity string.
        account_im_rate: Initial margin rate string.
        account_mm_rate: Maintenance margin rate string.
        total_perp_upl: Total unrealized PnL string.

    Returns:
        dict: Mock Bybit private wallet message payload.
    """
    return {
        "topic": "wallet",
        "type": "snapshot",
        "ts": 1234567890000,
        "data": [
            {
                "totalEquity": total_equity,
                "accountIMRate": account_im_rate,
                "accountMMRate": account_mm_rate,
                "totalPerpUPL": total_perp_upl,
            }
        ],
    }


@pytest.fixture
def bybit_http_router() -> dict[str, Any]:
    """Create a configurable HTTP request stub for Bybit tests.

    Returns:
        dict[str, Any]: Router with responses, calls, and handler coroutine.
    """
    responses: dict[str, Any] = {}
    calls: list[dict[str, Any]] = []

    async def _request(
        method: Any,
        endpoint: str,
        params: dict,
        data: dict,
        sign: bool,
        decoder: msgspec.json.Decoder,
    ):
        calls.append(
            {
                "method": method,
                "endpoint": endpoint,
                "params": params,
                "data": data,
                "sign": sign,
            }
        )
        response = responses.get(endpoint)
        if isinstance(response, Exception):
            raise response
        if isinstance(response, (ClientResponseSuccess, ClientResponseFailure)):
            return response
        if response is None:
            payload = {}
        else:
            payload = response
        return ClientResponseSuccess(data=decoder.decode(msgspec.json.encode(payload)))

    return {"responses": responses, "calls": calls, "handler": _request}


@pytest.fixture
def bybit_ws_router() -> dict[str, Any]:
    """Create a configurable WS submit stub for Bybit tests.

    Returns:
        dict[str, Any]: Router with responses, calls, and handler coroutine.
    """
    responses: dict[str, Any] = {}
    calls: list[dict[str, Any]] = []

    async def _submit(data: dict[str, Any], decoder: msgspec.json.Decoder):
        calls.append({"data": data})
        key = data.get("op") or data.get("method")
        response = responses.get(key)
        if isinstance(response, Exception):
            raise response
        if isinstance(response, (ClientResponseSuccess, ClientResponseFailure)):
            return response
        if response is None:
            payload = {}
        else:
            payload = response
        return ClientResponseSuccess(data=decoder.decode(msgspec.json.encode(payload)))

    return {"responses": responses, "calls": calls, "handler": _submit}


@pytest.fixture
def bybit_exchange_mocked(
    bybit_http_router,
    bybit_ws_router,
    monkeypatch,
    test_logger,
):
    """Create a BybitExchange with HTTP/WS clients stubbed out.

    Args:
        bybit_http_router: Fixture providing HTTP router and handler.
        bybit_ws_router: Fixture providing WS router and handler.
        monkeypatch: Pytest monkeypatch fixture.
        test_logger: Logger fixture from root conftest.

    Returns:
        BybitExchange: Exchange instance with stubbed clients.
    """
    from framework.bybit.trading.exchange import BybitExchange

    exchange = BybitExchange(logger=test_logger, load_secrets=False)
    exchange.http_client.is_running = True
    exchange.ws_client.is_running = True
    monkeypatch.setattr(exchange, "ensure_secrets_loaded", lambda: None)
    exchange.http_client.request = bybit_http_router["handler"]
    exchange.ws_client.submit = bybit_ws_router["handler"]
    return exchange


@pytest.fixture
def bybit_payloads():
    """Provide a namespace of Bybit payload helper factories.

    Returns:
        SimpleNamespace: Namespace of payload helper callables.
    """
    return SimpleNamespace(
        make_bybit_account_payload=make_bybit_account_payload,
        make_bybit_executions_payload=make_bybit_executions_payload,
        make_bybit_instruments_info_payload=make_bybit_instruments_info_payload,
        make_bybit_orderbook_payload=make_bybit_orderbook_payload,
        make_bybit_orders_payload=make_bybit_orders_payload,
        make_bybit_position_payload=make_bybit_position_payload,
        make_bybit_private_execution_message=make_bybit_private_execution_message,
        make_bybit_private_order_message=make_bybit_private_order_message,
        make_bybit_private_position_message=make_bybit_private_position_message,
        make_bybit_private_wallet_message=make_bybit_private_wallet_message,
        make_bybit_ticker_payload=make_bybit_ticker_payload,
        make_bybit_trades_payload=make_bybit_trades_payload,
        make_bybit_ws_submit_result=make_bybit_ws_submit_result,
    )
