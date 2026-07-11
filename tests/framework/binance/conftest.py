"""tests.framework.binance.conftest"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import msgspec
import pytest

from framework.base.common import Asset, Instrument, InstrumentType, Symbol, Venue
from framework.base.trading.models import ClientResponseFailure, ClientResponseSuccess


@pytest.fixture
def binance_instrument():
    """Standard BTC/USDT perpetual for Binance tests.

    Returns:
        Instrument: BTCUSDT perpetual contract on Binance USD-M.
    """
    return Instrument(
        venue=Venue.BINANCE_USDM,
        symbol=Symbol("BTCUSDT"),
        base=Asset("BTC"),
        quote=Asset("USDT"),
        code=0,
        instrument_type=InstrumentType.PERPETUAL,
        tick_size=0.01,
        lot_size=0.001,
    )


@pytest.fixture
def binance_exchange_public(test_logger):
    """Binance exchange without secrets (public API only).

    Args:
        test_logger: Logger fixture from root conftest.

    Returns:
        BinanceExchange: Exchange instance configured for public endpoints.
    """
    from framework.binance.trading.exchange import BinanceExchange

    return BinanceExchange(logger=test_logger, load_secrets=False, is_usd_margined=True)


@pytest.fixture
def binance_http_client(test_logger):
    """Binance HTTP client for testing.

    Args:
        test_logger: Logger fixture from root conftest.

    Returns:
        BinanceHttpClient: HTTP client without loaded secrets.
    """
    from framework.binance.trading.client import BinanceHttpClient
    from framework.binance.trading.time_sync import BinanceTimeSync

    return BinanceHttpClient(
        logger=test_logger,
        time_sync=BinanceTimeSync(venue=Venue.BINANCE_USDM, logger=test_logger),
        load_secrets=False,
        is_usd_margined=True,
    )


@pytest.fixture
def binance_ws_client(test_logger):
    """Binance WebSocket client for testing.

    Args:
        test_logger: Logger fixture from root conftest.

    Returns:
        BinanceWsClient: WebSocket client with test credentials.
    """
    from framework.binance.trading.client import BinanceWsClient
    from framework.binance.trading.time_sync import BinanceTimeSync

    return BinanceWsClient(
        logger=test_logger,
        time_sync=BinanceTimeSync(venue=Venue.BINANCE_USDM, logger=test_logger),
        load_secrets=False,
        is_usd_margined=True,
        key="test_api_key",
        secret="test_api_secret",
    )


# Mock data factory functions


def make_binance_http_orderbook_response(
    symbol: str = "BTCUSDT",
    bids: list[list[str]] | None = None,
    asks: list[list[str]] | None = None,
) -> dict:
    """Create mock Binance HTTP orderbook response.

    Args:
        symbol: Trading symbol.
        bids: List of [price, quantity] arrays for bids.
        asks: List of [price, quantity] arrays for asks.

    Returns:
        dict: Mock Binance orderbook response.
    """
    if bids is None:
        bids = [["30000.00", "1.500"], ["29999.00", "2.300"]]
    if asks is None:
        asks = [["30001.00", "1.200"], ["30002.00", "0.800"]]

    return {
        "lastUpdateId": 123456789,
        "E": 1234567890000,
        "T": 1234567890000,
        "bids": bids,
        "asks": asks,
    }


def make_binance_http_exchange_info_response(
    symbol: str = "BTCUSDT",
    base_asset: str = "BTC",
    quote_asset: str = "USDT",
    tick_size: str = "0.1",
    lot_size: str = "0.001",
    max_qty: str = "100",
) -> dict:
    """Create mock exchange info response payload.

    Args:
        symbol: Trading symbol.
        base_asset: Base asset.
        quote_asset: Quote asset.
        tick_size: Tick size string.
        lot_size: Lot size string.
        max_qty: Max quantity string.

    Returns:
        dict: Mock exchange info response payload.
    """
    return {
        "symbols": [
            {
                "symbol": symbol,
                "status": "TRADING",
                "baseAsset": base_asset,
                "quoteAsset": quote_asset,
                "underlyingType": "COIN",
                "filters": [
                    {
                        "filterType": "PRICE_FILTER",
                        "minPrice": "0.0",
                        "maxPrice": "1000000.0",
                        "tickSize": tick_size,
                        "minQty": None,
                        "maxQty": None,
                        "stepSize": None,
                    },
                    {
                        "filterType": "LOT_SIZE",
                        "minPrice": None,
                        "maxPrice": None,
                        "tickSize": None,
                        "minQty": "0.0",
                        "maxQty": max_qty,
                        "stepSize": lot_size,
                    },
                    {
                        "filterType": "MARKET_LOT_SIZE",
                        "minPrice": None,
                        "maxPrice": None,
                        "tickSize": None,
                        "minQty": "0.0",
                        "maxQty": max_qty,
                        "stepSize": lot_size,
                    },
                ],
            }
        ]
    }


def make_binance_http_ticker_24h_response(
    symbol: str = "BTCUSDT",
    price_change: str = "10.0",
    price_change_percent: str = "0.01",
    volume: str = "1000.0",
) -> dict:
    """Create mock 24hr ticker response payload.

    Args:
        symbol: Trading symbol.
        price_change: Price change string.
        price_change_percent: Price change percent string.
        volume: 24h volume string.

    Returns:
        dict: Mock 24hr ticker response payload.
    """
    return {
        "symbol": symbol,
        "priceChange": price_change,
        "priceChangePercent": price_change_percent,
        "weightedAvgPrice": "0",
        "lastPrice": "0",
        "lastQty": "0",
        "openPrice": "0",
        "highPrice": "0",
        "lowPrice": "0",
        "volume": volume,
        "quoteVolume": "0",
        "openTime": 0,
        "closeTime": 0,
        "firstId": 0,
        "lastId": 0,
        "count": 0,
    }


def make_binance_http_mark_price_response(
    symbol: str = "BTCUSDT",
    mark_price: str = "30000.0",
    index_price: str = "29990.0",
    funding_rate: str = "0.0001",
    next_funding_time: int = 1234567890,
) -> dict:
    """Create mock mark price response payload.

    Args:
        symbol: Trading symbol.
        mark_price: Mark price string.
        index_price: Index price string.
        funding_rate: Funding rate string.
        next_funding_time: Next funding time in ms.

    Returns:
        dict: Mock mark price response payload.
    """
    return {
        "symbol": symbol,
        "markPrice": mark_price,
        "indexPrice": index_price,
        "estimatedSettlePrice": "0",
        "lastFundingRate": funding_rate,
        "nextFundingTime": next_funding_time,
        "interestRate": "0",
        "time": 0,
    }


def make_binance_http_open_interest_response(
    open_interest: str = "1000.0",
    symbol: str = "BTCUSDT",
) -> dict:
    """Create mock open interest response payload.

    Args:
        open_interest: Open interest string.
        symbol: Trading symbol.

    Returns:
        dict: Mock open interest response payload.
    """
    return {"openInterest": open_interest, "symbol": symbol, "time": 0}


def make_binance_http_trade_response(
    trade_id: int = 1,
    price: str = "30000.0",
    qty: str = "0.01",
    is_buyer_maker: bool = False,
) -> dict:
    """Create mock trade response payload.

    Args:
        trade_id: Trade ID.
        price: Trade price string.
        qty: Trade quantity string.
        is_buyer_maker: Whether buyer is maker.

    Returns:
        dict: Mock trade response payload.
    """
    return {
        "id": trade_id,
        "price": price,
        "qty": qty,
        "quoteQty": "0",
        "time": 1,
        "isBuyerMaker": is_buyer_maker,
    }


def make_binance_http_orders_response(
    order_id: int = 1,
    symbol: str = "BTCUSDT",
    price: str = "30000.0",
    orig_qty: str = "0.01",
    executed_qty: str = "0.0",
    time_in_force: str = "GTC",
    status: str = "NEW",
) -> dict:
    """Create mock open orders response payload.

    Args:
        order_id: Order ID.
        symbol: Trading symbol.
        price: Order price string.
        orig_qty: Original quantity string.
        executed_qty: Executed quantity string.
        time_in_force: Time in force.
        status: Order status.

    Returns:
        dict: Mock order response payload.
    """
    return {
        "clientOrderId": f"client_{order_id}",
        "executedQty": executed_qty,
        "orderId": order_id,
        "origQty": orig_qty,
        "price": price,
        "reduceOnly": False,
        "side": "BUY",
        "status": status,
        "stopPrice": "0",
        "closePosition": False,
        "symbol": symbol,
        "time": 0,
        "timeInForce": time_in_force,
        "type": "LIMIT",
        "updateTime": 0,
        "cumulativeQuoteQty": "0",
    }


def make_binance_http_position_response(
    symbol: str = "BTCUSDT",
    position_amt: str = "0.01",
    entry_price: str = "30000.0",
) -> dict:
    """Create mock position response payload.

    Args:
        symbol: Trading symbol.
        position_amt: Position amount string.
        entry_price: Entry price string.

    Returns:
        dict: Mock position response payload.
    """
    return {
        "symbol": symbol,
        "positionAmt": position_amt,
        "entryPrice": entry_price,
        "markPrice": entry_price,
        "unrealPnl": "0",
        "liquidationPrice": "0",
        "leverage": "1",
        "maxNotionalValue": "0",
        "marginType": "cross",
        "isolatedMargin": "0",
        "isAutoAddMargin": False,
        "positionSide": "BOTH",
        "notional": "0",
        "isolatedWallet": "0",
        "updateTime": 0,
    }


def make_binance_http_user_trade_response(
    order_id: int = 1,
    side: str = "BUY",
    qty: str = "0.01",
    price: str = "30000.0",
    is_maker: bool = False,
) -> dict:
    """Create mock user trade response payload.

    Args:
        order_id: Order ID.
        side: Trade side.
        qty: Quantity string.
        price: Price string.
        is_maker: Whether maker.

    Returns:
        dict: Mock user trade response payload.
    """
    return {
        "symbol": "BTCUSDT",
        "id": 1,
        "orderId": order_id,
        "side": side,
        "qty": qty,
        "price": price,
        "quoteQty": "0",
        "commission": "0.0",
        "commissionAsset": "USDT",
        "time": 0,
        "isBuyer": side == "BUY",
        "isMaker": is_maker,
        "isIsolated": False,
    }


def make_binance_http_account_response(
    total_wallet_balance: str = "1000.0",
    total_initial_margin: str = "0.0",
    total_maint_margin: str = "0.0",
    total_unrealized_pnl: str = "0.0",
) -> dict:
    """Create mock account response payload.

    Args:
        total_wallet_balance: Total wallet balance string.
        total_initial_margin: Total initial margin string.
        total_maint_margin: Total maintenance margin string.
        total_unrealized_pnl: Total unrealized PnL string.

    Returns:
        dict: Mock account response payload.
    """
    return {
        "feeTier": 0,
        "canTrade": True,
        "canDeposit": True,
        "canWithdraw": True,
        "updateTime": 0,
        "totalInitialMargin": total_initial_margin,
        "totalMaintMargin": total_maint_margin,
        "totalWalletBalance": total_wallet_balance,
        "totalUnrealizedPnl": total_unrealized_pnl,
        "totalMarginBalance": total_wallet_balance,
        "totalPositionInitialMargin": "0",
        "totalOpenOrderInitialMargin": "0",
        "totalCrossWalletBalance": total_wallet_balance,
        "totalCrossUnPnl": "0",
        "availableBalance": total_wallet_balance,
        "maxWithdrawAmount": total_wallet_balance,
    }


def make_binance_listen_key_response(listen_key: str = "listen_key") -> dict:
    """Create mock listen key response payload.

    Args:
        listen_key: Listen key string.

    Returns:
        dict: Mock listen key response payload.
    """
    return {"listenKey": listen_key}


def make_binance_ticker_stream_update(
    symbol: str = "BTCUSDT",
    mark_price: str = "30000.00",
    index_price: str = "29999.50",
    funding_rate: str = "0.00010000",
) -> dict:
    """Create mock Binance mark price stream update.

    Args:
        symbol: Trading symbol.
        mark_price: Mark price.
        index_price: Index price.
        funding_rate: Funding rate.

    Returns:
        dict: Mock Binance mark price update payload.
    """
    return {
        "e": "markPriceUpdate",
        "E": 1234567890000,
        "s": symbol,
        "p": mark_price,
        "i": index_price,
        "P": "30001.00",
        "r": funding_rate,
        "T": 1234598400000,
    }


def make_binance_trade_stream_update(
    symbol: str = "BTCUSDT",
    price: str = "30000.00",
    qty: str = "0.050",
    is_buyer_maker: bool = False,
) -> dict:
    """Create mock Binance trade stream update.

    Args:
        symbol: Trading symbol.
        price: Trade price.
        qty: Trade quantity.
        is_buyer_maker: Whether buyer is maker.

    Returns:
        dict: Mock Binance trade stream update.
    """
    return {
        "e": "aggTrade",
        "E": 1234567890000,
        "a": 123456,
        "s": symbol,
        "p": price,
        "q": qty,
        "f": 123450,
        "l": 123455,
        "T": 1234567890000,
        "m": is_buyer_maker,
    }


def make_binance_orderbook_stream_update(
    symbol: str = "BTCUSDT",
    bids: list[dict] | None = None,
    asks: list[dict] | None = None,
) -> dict:
    """Create mock Binance orderbook stream update.

    Args:
        symbol: Trading symbol.
        bids: List of {"price": ..., "size": ...} dicts for bids.
        asks: List of {"price": ..., "size": ...} dicts for asks.

    Returns:
        dict: Mock Binance depth update payload.
    """
    if bids is None:
        bids = [{"price": "30000.00", "size": "1.500"}]
    if asks is None:
        asks = [{"price": "30001.00", "size": "1.200"}]

    return {
        "e": "depthUpdate",
        "E": 1234567890000,
        "T": 1234567890000,
        "s": symbol,
        "U": 123456,
        "u": 123460,
        "pu": 123455,
        "b": [[b["price"], b["size"]] for b in bids],
        "a": [[a["price"], a["size"]] for a in asks],
    }


def make_binance_ws_order_response(
    req_id: str = "test_req_123",
    status: int = 200,
    order_id: int = 123456789,
    symbol: str = "BTCUSDT",
    side: str = "BUY",
    order_type: str = "LIMIT",
    price: str = "30000.00",
    orig_qty: str = "0.010",
) -> dict:
    """Create mock Binance WebSocket order response.

    Args:
        req_id: Request ID.
        status: Response status (200 = success).
        order_id: Order ID from exchange.
        symbol: Trading symbol.
        side: Order side (BUY/SELL).
        order_type: Order type (LIMIT/MARKET).
        price: Order price.
        orig_qty: Original order quantity.

    Returns:
        dict: Mock Binance WS order response payload.
    """
    return {
        "id": req_id,
        "status": status,
        "result": {
            "orderId": order_id,
            "symbol": symbol,
            "status": "NEW",
            "clientOrderId": f"client_{order_id}",
            "price": price,
            "avgPrice": "0.00",
            "origQty": orig_qty,
            "executedQty": "0.000",
            "cumQty": "0.000",
            "cumQuote": "0.00",
            "timeInForce": "GTC",
            "type": order_type,
            "reduceOnly": False,
            "closePosition": False,
            "side": side,
            "positionSide": "BOTH",
            "stopPrice": "0.00",
            "workingType": "CONTRACT_PRICE",
            "priceProtect": False,
            "origType": order_type,
            "priceMatch": "NONE",
            "selfTradePreventionMode": "NONE",
            "goodTillDate": 0,
            "updateTime": 1234567890000,
        },
    }


def make_binance_ws_amend_order_response(
    req_id: str = "test_req_123",
    status: int = 200,
    order_id: int = 123456789,
    symbol: str = "BTCUSDT",
    side: str = "BUY",
    order_type: str = "LIMIT",
    price: str = "30000.00",
    orig_qty: str = "0.010",
) -> dict:
    """Create mock Binance WS amend order response payload.

    Args:
        req_id: Request ID.
        status: Response status (200 = success).
        order_id: Order ID from exchange.
        symbol: Trading symbol.
        side: Order side (BUY/SELL).
        order_type: Order type (LIMIT/MARKET).
        price: Order price.
        orig_qty: Original order quantity.

    Returns:
        dict: Mock Binance WS amend order response payload.
    """
    return {
        "id": req_id,
        "status": status,
        "result": {
            "orderId": order_id,
            "symbol": symbol,
            "status": "NEW",
            "clientOrderId": f"client_{order_id}",
            "price": price,
            "avgPrice": "0.00",
            "origQty": orig_qty,
            "executedQty": "0.000",
            "cumQty": "0.000",
            "cumQuote": "0.00",
            "timeInForce": "GTC",
            "type": order_type,
            "reduceOnly": False,
            "closePosition": False,
            "side": side,
            "positionSide": "BOTH",
            "stopPrice": "0.00",
            "workingType": "CONTRACT_PRICE",
            "priceProtect": False,
            "origType": order_type,
            "priceMatch": "NONE",
            "selfTradePreventionMode": "NONE",
            "goodTillDate": 0,
            "updateTime": 1234567890000,
        },
    }


def make_binance_ws_cancel_order_response(
    req_id: str = "test_req_123",
    status: int = 200,
    order_id: int = 123456789,
    symbol: str = "BTCUSDT",
    side: str = "BUY",
    price: str = "30000.00",
    orig_qty: str = "0.010",
) -> dict:
    """Create mock Binance WS cancel order response payload.

    Args:
        req_id: Request ID.
        status: Response status (200 = success).
        order_id: Order ID from exchange.
        symbol: Trading symbol.
        side: Order side (BUY/SELL).
        price: Order price.
        orig_qty: Original order quantity.

    Returns:
        dict: Mock Binance WS cancel order response payload.
    """
    return {
        "id": req_id,
        "status": status,
        "result": {
            "orderId": order_id,
            "clientOrderId": f"client_{order_id}",
            "cumQty": "0.000",
            "cumQuote": "0.00",
            "executedQty": "0.000",
            "origQty": orig_qty,
            "origType": "LIMIT",
            "price": price,
            "reduceOnly": False,
            "side": side,
            "positionSide": "BOTH",
            "status": "CANCELED",
            "stopPrice": "0.00",
            "closePosition": False,
            "symbol": symbol,
            "timeInForce": "GTC",
            "type": "LIMIT",
            "activatePrice": "0.00",
            "priceRate": "0.0",
            "updateTime": 1234567890000,
            "workingType": "CONTRACT_PRICE",
            "priceProtect": False,
            "priceMatch": "NONE",
            "selfTradePreventionMode": "NONE",
            "goodTillDate": 0,
        },
    }


def make_binance_position_update(
    symbol: str = "BTCUSDT",
    position_side: str = "BOTH",
    position_amt: str = "0.500",
    entry_price: str = "30000.00",
) -> dict:
    """Create mock Binance position update message.

    Args:
        symbol: Trading symbol.
        position_side: Position side (BOTH/LONG/SHORT).
        position_amt: Position amount.
        entry_price: Entry price.

    Returns:
        dict: Mock Binance position update payload.
    """
    return {
        "e": "ACCOUNT_UPDATE",
        "E": 1234567890000,
        "T": 1234567890000,
        "a": {
            "B": [{"a": "USDT", "wb": "10000.00", "cw": "9950.00"}],
            "P": [
                {
                    "s": symbol,
                    "pa": position_amt,
                    "ep": entry_price,
                    "cr": "0.00",
                    "up": "50.00",
                    "mt": "cross",
                    "iw": "0.00",
                    "ps": position_side,
                }
            ],
        },
    }


@pytest.fixture
def binance_http_router() -> dict[str, Any]:
    """Create a configurable HTTP request stub for Binance tests.

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
def binance_ws_router() -> dict[str, Any]:
    """Create a configurable WS submit stub for Binance tests.

    Returns:
        dict[str, Any]: Router with responses, calls, and handler coroutine.
    """
    responses: dict[str, Any] = {}
    calls: list[dict[str, Any]] = []

    async def _submit(data: dict[str, Any], decoder: msgspec.json.Decoder):
        calls.append({"data": data})
        response = responses.get(data.get("method"))
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
def binance_exchange_mocked(
    binance_http_router,
    binance_ws_router,
    monkeypatch,
    test_logger,
):
    """Create a BinanceExchange with HTTP/WS clients stubbed out.

    Args:
        binance_http_router: Fixture providing HTTP router and handler.
        binance_ws_router: Fixture providing WS router and handler.
        monkeypatch: Pytest monkeypatch fixture.
        test_logger: Logger fixture from root conftest.

    Returns:
        BinanceExchange: Exchange instance with stubbed clients.
    """
    from framework.binance.trading.exchange import BinanceExchange

    exchange = BinanceExchange(
        logger=test_logger,
        load_secrets=False,
        is_usd_margined=True,
    )
    exchange.http_client.is_running = True
    exchange.ws_client.is_running = True
    monkeypatch.setattr(exchange, "ensure_secrets_loaded", lambda: None)
    exchange.http_client.request = binance_http_router["handler"]
    exchange.ws_client.submit = binance_ws_router["handler"]
    return exchange


@pytest.fixture
def binance_payloads():
    """Provide a namespace of Binance payload helper factories.

    Returns:
        SimpleNamespace: Namespace of payload helper callables.
    """
    return SimpleNamespace(
        make_binance_http_account_response=make_binance_http_account_response,
        make_binance_http_exchange_info_response=make_binance_http_exchange_info_response,
        make_binance_http_mark_price_response=make_binance_http_mark_price_response,
        make_binance_http_open_interest_response=make_binance_http_open_interest_response,
        make_binance_http_orderbook_response=make_binance_http_orderbook_response,
        make_binance_http_orders_response=make_binance_http_orders_response,
        make_binance_http_position_response=make_binance_http_position_response,
        make_binance_http_ticker_24h_response=make_binance_http_ticker_24h_response,
        make_binance_http_trade_response=make_binance_http_trade_response,
        make_binance_http_user_trade_response=make_binance_http_user_trade_response,
        make_binance_listen_key_response=make_binance_listen_key_response,
        make_binance_ws_amend_order_response=make_binance_ws_amend_order_response,
        make_binance_ws_cancel_order_response=make_binance_ws_cancel_order_response,
        make_binance_ws_order_response=make_binance_ws_order_response,
    )
