from typing import Optional

from msgspec import Struct

from framework.base.common import Instrument, Venue
from framework.base.stream.models import (
    Execution,
)


class BinanceWsCreateOrderResult(Struct, rename="camel"):
    """Represents the 'result' field from the create order action websocket response."""

    order_id: int
    symbol: str
    status: str
    client_order_id: str
    price: str
    avg_price: str
    orig_qty: str
    executed_qty: str
    cum_qty: str
    cum_quote: str
    time_in_force: str
    type: str
    reduce_only: bool
    close_position: bool
    side: str
    positionSide: str
    stop_price: str
    working_type: str
    priceProtect: bool
    orig_type: str
    price_match: str
    self_trade_prevention_mode: str
    good_till_date: int
    update_time: int


class BinanceWsAmendOrderResult(Struct, rename="camel"):
    """Represents the 'result' field from the amend order action websocket response."""

    order_id: int
    symbol: str
    status: str
    client_order_id: str
    price: str
    avg_price: str
    orig_qty: str
    executed_qty: str
    cum_qty: str
    cum_quote: str
    time_in_force: str
    type: str
    reduce_only: bool
    close_position: bool
    side: str
    position_side: str
    stop_price: str
    working_type: str
    price_protect: bool
    orig_type: str
    price_match: str
    self_trade_prevention_mode: str
    good_till_date: int
    update_time: int


class BinanceWsCancelOrderResult(Struct, rename="camel"):
    """Represents the 'result' field from the cancel order action websocket response."""

    order_id: int
    client_order_id: str
    cum_qty: str
    cum_quote: str
    executed_qty: str
    orig_qty: str
    orig_type: str
    price: str
    reduce_only: bool
    side: str
    position_side: str
    status: str
    stop_price: str
    close_position: bool
    symbol: str
    time_in_force: str
    type: str
    activate_price: str
    price_rate: str
    update_time: int
    working_type: str
    price_protect: bool
    price_match: str
    self_trade_prevention_mode: str
    good_till_date: int


class BinanceWsOrderResponse[T](Struct, rename="camel"):
    """Represents the response from the order action websocket response."""

    id: str
    status: int
    result: T

    @property
    def is_successful(self) -> bool:
        return self.status == 200 or self.status == 0


class BinanceHttpCancelAllOrdersResponse(Struct):
    """Represents the response from the cancel all orders action."""

    code: int
    msg: str

    @property
    def is_successful(self) -> bool:
        return self.code == 200 or self.code == 0


class BinanceHttpOrderbookResponse(Struct, rename="camel"):
    """https://developers.binance.com/docs/derivatives/usds-margined-futures/market-data/rest-api/Order-Book."""

    last_update_id: int
    E: int  # Event time
    T: int  # Transaction time
    bids: list[list[str]]
    asks: list[list[str]]


class BinanceHttpTicker24hrResponse(Struct, rename="camel"):
    """https://developers.binance.com/docs/derivatives/usds-margined-futures/market-data/rest-api/24hr-Ticker-Price-Change-Statistics."""

    symbol: str
    price_change: str
    price_change_percent: str
    weighted_avg_price: str
    last_price: str
    last_qty: str
    open_price: str
    high_price: str
    low_price: str
    volume: str
    quote_volume: str
    open_time: int
    close_time: int
    first_id: int
    last_id: int
    count: int


class BinanceHttpMarkPriceResponse(Struct, rename="camel"):
    """https://developers.binance.com/docs/derivatives/usds-margined-futures/market-data/rest-api/Mark-Price."""

    symbol: str
    mark_price: str
    index_price: str
    estimated_settle_price: str
    last_funding_rate: str
    next_funding_time: int
    interest_rate: str
    time: int


class BinanceHttpOpenInterestResponse(Struct, rename="camel"):
    """https://developers.binance.com/docs/derivatives/usds-margined-futures/market-data/rest-api/Open-Interest."""

    open_interest: str
    symbol: str
    time: int


class BinanceHttpTradeResponse(Struct, rename="camel"):
    """https://developers.binance.com/docs/derivatives/usds-margined-futures/market-data/rest-api/Recent-Trades-List."""

    id: int
    price: str
    qty: str
    quote_qty: str
    time: int
    is_buyer_maker: bool


class SymbolInformationFilters(Struct, rename="camel"):
    """https://developers.binance.com/docs/derivatives/usds-margined-futures/market-data/rest-api/Exchange-Information."""

    filter_type: str

    # Only available on filter_type=PRICE_FILTER
    min_price: Optional[str]
    max_price: Optional[str]
    tick_size: Optional[str]

    # Only available on filter_type=LOT_SIZE/MARKET_LOT_SIZE
    min_qty: Optional[str]
    max_qty: Optional[str]
    step_size: Optional[str]


class SymbolInformation(Struct, rename="camel"):
    """https://developers.binance.com/docs/derivatives/usds-margined-futures/market-data/rest-api/Exchange-Information."""

    status: str
    base_asset: str
    quote_asset: str
    underlying_type: str
    filters: list[SymbolInformationFilters]


class BinanceHttpExchangeInformationResponse(Struct):
    """https://developers.binance.com/docs/derivatives/usds-margined-futures/market-data/rest-api/Exchange-Information."""

    symbols: list[SymbolInformation]


class BinanceHttpOrdersResponse(Struct, rename="camel"):
    """https://developers.binance.com/docs/derivatives/usds-margined-futures/trade/rest-api/Current-Open-Orders"""

    avg_price: str
    client_order_id: str
    cum_quote: str
    executed_qty: str
    order_id: int
    orig_qty: str
    orig_type: str
    price: str
    reduce_only: bool
    side: str
    position_side: str
    status: str
    stop_price: str
    close_position: bool
    symbol: str
    time: int
    time_in_force: str
    type: str
    update_time: int
    working_type: str
    price_protect: bool
    price_match: str
    self_trade_prevention_mode: str
    good_till_date: int


class BinanceHttpPositionResponse(Struct, rename="camel"):
    """Represents a trading position from Binance HTTP API."""

    symbol: str
    position_side: str
    position_amt: str
    entry_price: str
    break_even_price: str
    mark_price: str
    un_realized_profit: str
    liquidation_price: str
    isolated_margin: str
    notional: str
    margin_asset: str
    isolated_wallet: str
    initial_margin: str
    maint_margin: str
    position_initial_margin: str
    open_order_initial_margin: str
    adl: int
    update_time: int


class ExecutionResponse(Struct):
    """Represents an execution (fill) of an order."""

    venue: Venue
    instrument: Instrument

    executions: list[Execution]


class AccountResponse(Struct):
    """Represents account information."""

    venue: Venue
    instrument: Instrument

    balance: float
    initial_margin: float
    maintenance_margin: float
    unrealized_pnl: float


class HttpOrder(Struct, rename="camel"):
    """https://developers.binance.com/docs/derivatives/usds-margined-futures/trade/rest-api/Current-Open-Orders."""

    symbol: str
    order_id: int
    client_order_id: str
    price: str
    orig_qty: str
    executed_qty: str
    cumulative_quote_qty: str
    status: str
    time_in_force: str
    type: str
    side: str
    stop_price: str
    time: int
    update_time: int
    reduce_only: bool
    close_position: bool


class HttpPosition(Struct, rename="camel"):
    """https://developers.binance.com/docs/derivatives/usds-margined-futures/account/rest-api/Position-Information-V2."""

    symbol: str
    position_amt: str
    entry_price: str
    mark_price: str
    unreal_pnl: str
    liquidation_price: str
    leverage: str
    max_notional_value: str
    margin_type: str
    isolated_margin: str
    is_auto_add_margin: bool
    position_side: str
    notional: str
    isolated_wallet: str
    update_time: int


class HttpUserTrade(Struct, rename="camel"):
    """https://developers.binance.com/docs/derivatives/usds-margined-futures/trade/rest-api/Account-Trade-List."""

    symbol: str
    id: int
    order_id: int
    side: str
    qty: str
    price: str
    quote_qty: str
    commission: str
    commission_asset: str
    time: int
    is_buyer: bool
    is_maker: bool
    is_isolated: bool


class HttpAccount(Struct, rename="camel"):
    """https://developers.binance.com/docs/derivatives/usds-margined-futures/account/rest-api/Account-Information-V2."""

    fee_tier: int
    can_trade: bool
    can_deposit: bool
    can_withdraw: bool
    update_time: int
    total_initial_margin: str
    total_maint_margin: str
    total_wallet_balance: str
    total_unrealized_pnl: str
    total_margin_balance: str
    total_position_initial_margin: str
    total_open_order_initial_margin: str
    total_cross_wallet_balance: str
    total_cross_un_pnl: str
    available_balance: str
    max_withdraw_amount: str
