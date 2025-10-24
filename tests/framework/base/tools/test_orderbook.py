import pytest

from framework.base.stream.structs import OrderbookLevel
from framework.base.tools.orderbook import Orderbook


def levels(prices: list[float], sizes: list[float]) -> list[OrderbookLevel]:
    return [
        OrderbookLevel(price=p, size=s) for p, s in zip(prices, sizes, strict=False)
    ]


def test_orderbook_snapshot_and_accessors():
    ob = Orderbook(size=3)
    bids = levels([100.0, 99.5, 99.0], [1.0, 2.0, 3.0])
    asks = levels([100.5, 101.0, 101.5], [1.5, 2.5, 3.5])
    ob.update(bids=bids, asks=asks, is_snapshot=True)

    best_bid, best_ask = ob.get_bbo()
    assert best_bid.price == 100.0
    assert best_ask.price == 100.5
    assert ob.get_bbo_spread() == 0.5
    assert ob.get_mid_price() == 100.25

    top2_bids = ob.get_bids(depth=2)
    assert [level.price for level in top2_bids] == [100.0, 99.5]
    top2_asks = ob.get_asks(depth=2)
    assert [level.price for level in top2_asks] == [100.5, 101.0]


def test_orderbook_incremental_updates_and_bbo_change_detection():
    ob = Orderbook(size=3)
    bids = levels([100.0, 99.5, 99.0], [1.0, 2.0, 3.0])
    asks = levels([100.5, 101.0, 101.5], [1.5, 2.5, 3.5])
    ob.update(bids=bids, asks=asks, is_snapshot=True)

    # delete best bid, insert new better bid
    updates_b = [
        OrderbookLevel(price=100.0, size=0.0),
        OrderbookLevel(price=100.25, size=1.0),
    ]
    updates_a = []
    ob.update(bids=updates_b, asks=updates_a, is_snapshot=False)

    best_bid, best_ask = ob.get_bbo()
    assert best_bid.price == 100.25
    assert best_ask.price == 100.5
    assert ob.does_bbo_px_change(100.25, 100.5) is False
    assert ob.does_bbo_px_change(100.0, 100.5) is True


def test_orderbook_bbo_update_method():
    ob = Orderbook(size=3)
    bids = levels([100.0, 99.5, 99.0], [1.0, 2.0, 3.0])
    asks = levels([100.5, 101.0, 101.5], [1.5, 2.5, 3.5])
    ob.update(bids=bids, asks=asks, is_snapshot=True)

    # Replace best bid/ask directly
    ob.update_bbo(
        bid=OrderbookLevel(price=100.75, size=1.0),
        ask=OrderbookLevel(price=100.9, size=1.2),
    )
    best_bid, best_ask = ob.get_bbo()
    assert best_bid.price == 100.75
    assert best_ask.price == 100.9


def test_orderbook_volume_weighted_mid_and_price_impact():
    ob = Orderbook(size=3)
    bids = levels([100.0, 99.5, 99.0], [1.0, 2.0, 3.0])
    asks = levels([100.5, 101.0, 101.5], [1.5, 2.5, 3.5])
    ob.update(bids=bids, asks=asks, is_snapshot=True)

    vwmid = ob.get_volume_weighted_mid_price(size=1.0, is_base_currency=True)
    assert isinstance(vwmid, float)

    impact_buy = ob.get_price_impact(size=1.0, is_buy=True, is_base_currency=True)
    impact_sell = ob.get_price_impact(size=1.0, is_buy=False, is_base_currency=True)
    assert impact_buy >= 0.0
    assert impact_sell >= 0.0


def test_orderbook_crossed_and_reset():
    ob1 = Orderbook(size=3)
    ob2 = Orderbook(size=3)

    bids = levels([100.0, 99.5, 99.0], [1.0, 2.0, 3.0])
    asks = levels([100.5, 101.0, 101.5], [1.5, 2.5, 3.5])
    ob1.update(bids=bids, asks=asks, is_snapshot=True)
    ob2.update(
        bids=levels([100.6, 100.1, 99.6], [1.0, 2.0, 3.0]),
        asks=levels([100.7, 101.2, 101.7], [1.5, 2.5, 3.5]),
        is_snapshot=True,
    )

    assert ob1.is_crossed(ob2) is False

    ob2.update_bbo(
        bid=OrderbookLevel(price=101.0, size=1.0),
        ask=OrderbookLevel(price=100.4, size=1.0),
    )
    assert ob1.is_crossed(ob2) is True

    ob1.reset()
    with pytest.raises(ValueError):
        ob1.get_bbo()
