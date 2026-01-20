"""Bybit-specific data structures for trading WebSocket responses."""

from msgspec import Struct


class BybitWsCreateOrderResult(Struct, rename="camel"):
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


class BybitWsOrderResponse[T](Struct, rename="camel"):
    id: str
    status: int
    result: T

    @property
    def is_successful(self) -> bool:
        return self.status == 0 or self.status == 200
