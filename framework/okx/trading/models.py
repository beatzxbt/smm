"""Structs for OKX V5 Trade API responses.

This module provides dataclass-like structs for deserializing order operations
and market data responses from OKX V5 API into strongly-typed Python objects.
Covers both WebSocket trading operations and HTTP REST endpoints.
"""

from __future__ import annotations

from msgspec import Struct, field

from framework.base.common import Asset, Symbol


# =============================================================================
# WebSocket Order Operation Results
# =============================================================================


class OkxWsOrderResult(Struct, frozen=True):
    """Result from WebSocket order/amend/cancel operations.

    Used for responses from op: "order", "amend-order", "cancel-order".
    Each item in the data array contains order ID and status code.

    Docs: https://www.okx.com/docs-v5/en/#order-book-trading-trade-ws-place-order

    Example payload (single item from data array)::

        {
          "ordId": "12345678",
          "clOrdId": "client123",
          "sCode": "0",
          "sMsg": ""
        }
    """

    ord_id: str = field(name="ordId")
    cl_ord_id: str = field(name="clOrdId", default="")
    s_code: str = field(name="sCode")
    s_msg: str = field(name="sMsg", default="")


# =============================================================================
# HTTP REST - Public Market Data
# =============================================================================


class OkxHttpInstrument(Struct, frozen=True):
    """Instrument information from /api/v5/public/instruments.

    Provides trading pair metadata including tick size, lot size, and
    contract specifications for SWAP instruments.

    Docs: https://www.okx.com/docs-v5/en/#public-data-rest-api-get-instruments

    Example payload::

        {
          "instId": "BTC-USDT-SWAP",
          "instType": "SWAP",
          "baseCcy": "",
          "quoteCcy": "",
          "settleCcy": "USDT",
          "ctVal": "0.01",
          "ctMult": "1",
          "ctValCcy": "BTC",
          "tickSz": "0.1",
          "lotSz": "1",
          "minSz": "1",
          "state": "live"
        }
    """

    inst_id: Symbol = field(name="instId")
    inst_type: str = field(name="instType")
    tick_sz: str = field(name="tickSz")
    lot_sz: str = field(name="lotSz")
    ct_val: str = field(name="ctVal", default="")
    ct_mult: str = field(name="ctMult", default="")
    ct_val_ccy: Asset = field(name="ctValCcy", default=Asset(""))
    settle_ccy: Asset = field(name="settleCcy", default=Asset(""))
    min_sz: str = field(name="minSz", default="")
    state: str = field(default="live")


class OkxHttpTicker(Struct, frozen=True):
    """Ticker data from /api/v5/market/ticker.

    Provides mark price, index price, funding rate, and open interest
    for perpetual contracts.

    Docs: https://www.okx.com/docs-v5/en/#public-data-rest-api-get-ticker

    Example payload::

        {
          "instId": "BTC-USDT-SWAP",
          "last": "30000.5",
          "askPx": "30001.0",
          "bidPx": "30000.0",
          "open24h": "29000.0",
          "high24h": "31000.0",
          "low24h": "28000.0",
          "vol24h": "100000",
          "ts": "1597026383085",
          "markPx": "30000.0",
          "idxPx": "29995.25",
          "fundingRate": "0.0001",
          "nextFundingTime": "1597027200000",
          "openInterest": "100000.5"
        }
    """

    inst_id: Symbol = field(name="instId")
    mark_px: str = field(name="markPx", default="0")
    idx_px: str = field(name="idxPx", default="0")
    funding_rate: str = field(name="fundingRate", default="0")
    next_funding_time: str = field(name="nextFundingTime", default="0")
    open_interest: str = field(name="openInterest", default="")
    vol_24h: str = field(name="vol24h", default="")
    last: str = field(default="0")
    ts: str = field(default="0")


class OkxHttpOrderbookLevel(Struct, frozen=True, array_like=True):
    """Single orderbook level as array [price, size, deprecated, num_orders].

    OKX returns orderbook levels as arrays, not objects. The third field
    is deprecated (was liquidation orders) and should be ignored.
    """

    price: str
    size: str
    deprecated: str
    num_orders: str


class OkxHttpOrderbook(Struct, frozen=True):
    """Orderbook snapshot from /api/v5/market/books.

    Provides bid and ask levels with price, size, and order count.
    Each level is an array: [price, size, deprecated, num_orders].

    Docs: https://www.okx.com/docs-v5/en/#order-book-trading-market-data-get-order-book

    Example payload::

        {
          "asks": [
            ["30001.0", "1.5", "0", "3"],
            ["30002.0", "3.0", "0", "5"]
          ],
          "bids": [
            ["30000.0", "1.0", "0", "2"],
            ["29999.5", "2.0", "0", "4"]
          ],
          "ts": "1597026383085"
        }
    """

    asks: list[OkxHttpOrderbookLevel]
    bids: list[OkxHttpOrderbookLevel]
    ts: str


class OkxHttpTrade(Struct, frozen=True):
    """Public trade from /api/v5/market/trades.

    Represents a single executed trade in the market.

    Docs: https://www.okx.com/docs-v5/en/#order-book-trading-market-data-get-trades

    Example payload::

        {
          "instId": "BTC-USDT-SWAP",
          "tradeId": "123456789",
          "px": "30000.5",
          "sz": "1.0",
          "side": "buy",
          "ts": "1597026383085"
        }
    """

    inst_id: Symbol = field(name="instId")
    trade_id: str = field(name="tradeId")
    px: str
    sz: str
    side: str
    ts: str


# =============================================================================
# HTTP REST - Private Account Data
# =============================================================================


class OkxHttpBalanceDetail(Struct, frozen=True):
    """Currency balance detail nested in account response.

    Each currency held in the account has separate balance details
    including equity, frozen balance, and unrealized PnL.

    Example payload::

        {
          "ccy": "USDT",
          "eq": "10000.0",
          "frozenBal": "1000.0",
          "availBal": "9000.0",
          "upl": "500.0"
        }
    """

    ccy: str
    eq: str = field(default="0")
    frozen_bal: str = field(name="frozenBal", default="0")
    avail_bal: str = field(name="availBal", default="0")
    upl: str = field(default="0")


class OkxHttpAccount(Struct, frozen=True):
    """Account balance from /api/v5/account/balance.

    Provides total equity and per-currency balance details.
    The details array contains OkxHttpBalanceDetail for each currency.

    Docs: https://www.okx.com/docs-v5/en/#trading-account-rest-api-get-balance

    Example payload::

        {
          "uTime": "1597026383085",
          "totalEq": "100000.0",
          "details": [
            {
              "ccy": "USDT",
              "eq": "10000.0",
              "frozenBal": "1000.0",
              "availBal": "9000.0",
              "upl": "500.0"
            }
          ]
        }
    """

    u_time: str = field(name="uTime")
    total_eq: str = field(name="totalEq", default="0")
    details: list[OkxHttpBalanceDetail] = field(default_factory=list)


class OkxHttpPosition(Struct, frozen=True):
    """Position from /api/v5/account/positions.

    Provides position size and average entry price. Positive pos means long,
    negative means short.

    Docs: https://www.okx.com/docs-v5/en/#trading-account-rest-api-get-positions

    Example payload::

        {
          "instId": "BTC-USDT-SWAP",
          "instType": "SWAP",
          "mgnMode": "cross",
          "posId": "123456789",
          "posSide": "net",
          "pos": "1.0",
          "avgPx": "30000.0",
          "upl": "500.0",
          "lever": "10",
          "liqPx": "25000.0"
        }
    """

    inst_id: Symbol = field(name="instId")
    inst_type: str = field(name="instType", default="SWAP")
    mgn_mode: str = field(name="mgnMode", default="cross")
    pos_id: str = field(name="posId", default="")
    pos_side: str = field(name="posSide", default="net")
    pos: str = field(default="0")
    avg_px: str = field(name="avgPx", default="0")
    upl: str = field(default="0")
    lever: str = field(default="1")
    liq_px: str = field(name="liqPx", default="")


class OkxHttpOrder(Struct, frozen=True):
    """Pending order from /api/v5/trade/orders-pending.

    Provides order details including price, size, type, and fill status.

    Docs: https://www.okx.com/docs-v5/en/#order-book-trading-trade-get-order-list

    Example payload::

        {
          "instId": "BTC-USDT-SWAP",
          "ordId": "123456789",
          "clOrdId": "client123",
          "px": "30000.0",
          "sz": "1.0",
          "ordType": "limit",
          "side": "buy",
          "posSide": "net",
          "tdMode": "cross",
          "state": "live",
          "accFillSz": "0",
          "cTime": "1597026383085",
          "uTime": "1597026383085",
          "reduceOnly": "false"
        }
    """

    inst_id: Symbol = field(name="instId")
    ord_id: str = field(name="ordId")
    cl_ord_id: str = field(name="clOrdId", default="")
    px: str = field(default="0")
    sz: str = field(default="0")
    ord_type: str = field(name="ordType", default="limit")
    side: str = field(default="buy")
    pos_side: str = field(name="posSide", default="net")
    td_mode: str = field(name="tdMode", default="cross")
    state: str = field(default="live")
    acc_fill_sz: str = field(name="accFillSz", default="0")
    c_time: str = field(name="cTime", default="0")
    u_time: str = field(name="uTime", default="0")
    reduce_only: str = field(name="reduceOnly", default="false")


class OkxHttpFill(Struct, frozen=True):
    """Execution/fill from /api/v5/trade/fills.

    Provides fill details including price, size, fees, and maker/taker status.
    execType "M" = maker, "T" = taker.

    Docs: https://www.okx.com/docs-v5/en/#order-book-trading-trade-get-transaction-details-last-3-days

    Example payload::

        {
          "instId": "BTC-USDT-SWAP",
          "ordId": "123456789",
          "clOrdId": "client123",
          "tradeId": "987654321",
          "fillPx": "30000.0",
          "fillSz": "0.5",
          "side": "buy",
          "posSide": "net",
          "execType": "T",
          "fee": "-0.015",
          "feeCcy": "USDT",
          "ts": "1597026383085"
        }
    """

    inst_id: Symbol = field(name="instId")
    ord_id: str = field(name="ordId")
    cl_ord_id: str = field(name="clOrdId", default="")
    trade_id: str = field(name="tradeId", default="")
    fill_px: str = field(name="fillPx")
    fill_sz: str = field(name="fillSz")
    side: str
    pos_side: str = field(name="posSide", default="net")
    exec_type: str = field(name="execType", default="T")
    fee: str = field(default="0")
    fee_ccy: Asset = field(name="feeCcy", default=Asset(""))
    ts: str


class OkxHttpBatchCancelResult(Struct, frozen=True):
    """Result from batch cancel /api/v5/trade/cancel-batch-orders.

    Each cancelled order returns its ID and status code.

    Docs: https://www.okx.com/docs-v5/en/#order-book-trading-trade-post-cancel-multiple-orders

    Example payload::

        {
          "ordId": "123456789",
          "clOrdId": "client123",
          "sCode": "0",
          "sMsg": ""
        }
    """

    ord_id: str = field(name="ordId")
    cl_ord_id: str = field(name="clOrdId", default="")
    s_code: str = field(name="sCode")
    s_msg: str = field(name="sMsg", default="")
