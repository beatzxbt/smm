from collections.abc import Iterator
from typing import Self

from framework.base.stream.structs import OrderbookLevel


class Orderbook:
    """An orderbook class maintaining separate dictionaries for bid and
    ask orders with functionality to initialize, update, and access
    best bid/offer information.
    """

    updates_consumed: int = 0

    def __init__(
        self,
        size: int = 500,
        initial_bids: list[OrderbookLevel] | None = None,
        initial_asks: list[OrderbookLevel] | None = None,
    ) -> None:
        self._size = size

        self._asks: dict[float, OrderbookLevel] = {}
        self._bids: dict[float, OrderbookLevel] = {}

        self._sorted_ask_prices: list[float] = []
        self._sorted_bid_prices: list[float] = []

        self._is_populated = False

        if initial_bids is not None and initial_asks is not None:
            self.update(bids=initial_bids, asks=initial_asks, is_snapshot=True)

    def _ensure_populated(self) -> None:
        """Check if the orderbook is populated."""
        if not self._is_populated:
            raise ValueError("Orderbook is not populated.")

    def _ensure_snapshot_validity(
        self, bids: list[OrderbookLevel], asks: list[OrderbookLevel]
    ) -> None:
        """Check if the snapshot is valid."""
        len_bids = len(bids)
        if len(bids) < self._size:
            raise ValueError(
                f"Invalid bids with snapshot; expected >={self._size} bids but got {len_bids}."
            )

        len_asks = len(asks)
        if len(asks) < self._size:
            raise ValueError(
                f"Invalid asks with snapshot; expected >={self._size} asks but got {len_asks}."
            )

    def _remove_ask(self, px: float) -> None:
        """Remove an ask level."""
        if px in self._asks:
            del self._asks[px]
            self._sorted_ask_prices.remove(px)

    def _remove_bid(self, px: float) -> None:
        """Remove a bid level."""
        if px in self._bids:
            del self._bids[px]
            self._sorted_bid_prices.remove(px)

    def update(
        self,
        bids: list[OrderbookLevel],
        asks: list[OrderbookLevel],
        is_snapshot: bool = False,
    ) -> None:
        """Update the orderbook. Bids and asks coming from internal ws/http message structs are guaranteed to be sorted."""
        if is_snapshot:
            self._ensure_snapshot_validity(bids, asks)

            self.reset()

            for ask in asks:
                self._asks[ask.price] = ask
                self._sorted_ask_prices.append(ask.price)
            self._sorted_ask_prices.sort()

            for bid in bids:
                self._bids[bid.price] = bid
                self._sorted_bid_prices.append(bid.price)
            self._sorted_bid_prices.sort(reverse=True)

            self._is_populated = True

        else:
            for ask in asks:
                if ask.size == 0.0:
                    self._remove_ask(ask.price)
                else:
                    if ask.price not in self._asks:
                        self._sorted_ask_prices.append(ask.price)
                    self._asks[ask.price] = ask
            self._sorted_ask_prices.sort()

            for bid in bids:
                if bid.size == 0.0:
                    self._remove_bid(bid.price)
                else:
                    if bid.price not in self._bids:
                        self._sorted_bid_prices.append(bid.price)
                    self._bids[bid.price] = bid
            self._sorted_bid_prices.sort(reverse=True)

    def update_bbo(self, bid: OrderbookLevel, ask: OrderbookLevel) -> None:
        """Update the best bid and offer.

        BBO updates usually don't supply sz=0 updates for signalling level
        deletion, and directly provide the new best bid/ask if available.

        Therefore, we ignore it and directly update the best bid/ask for now,
        fixing any issues arising with the orderbook by assuming this source of truth.
        """
        bid_price, bid_size = bid.price, bid.size
        ask_price, ask_size = ask.price, ask.size

        if bid_size == 0.0:
            if (best_bid_price := self._sorted_bid_prices[0]) in self._bids:
                del self._bids[best_bid_price]
                self._sorted_bid_prices.pop(0)
        else:
            if bid_price in self._bids:
                self._bids[bid_price] = bid
            else:
                old_best_price = self._sorted_bid_prices[0]
                if old_best_price != bid_price:
                    del self._bids[old_best_price]
                    self._sorted_bid_prices.pop(0)

                self._bids[bid_price] = bid
                if bid_price not in self._sorted_bid_prices:
                    self._sorted_bid_prices.append(bid_price)
                    self._sorted_bid_prices.sort(reverse=True)

        if ask_size == 0.0:
            if (best_ask_price := self._sorted_ask_prices[0]) in self._asks:
                del self._asks[best_ask_price]
                self._sorted_ask_prices.pop(0)
        else:
            if ask_price in self._asks:
                self._asks[ask_price] = ask
            else:
                old_best_price = self._sorted_ask_prices[0]
                if old_best_price != ask_price and old_best_price in self._asks:
                    del self._asks[old_best_price]
                    self._sorted_ask_prices.pop(0)

                self._asks[ask_price] = ask
                if ask_price not in self._sorted_ask_prices:
                    self._sorted_ask_prices.append(ask_price)
                    self._sorted_ask_prices.sort()

    def does_bbo_px_change(self, bid_px: float, ask_px: float) -> bool:
        """Check if the best bid/ask price will change."""
        self._ensure_populated()
        best_bid_px = self._sorted_bid_prices[0]
        best_ask_px = self._sorted_ask_prices[0]
        return best_bid_px != bid_px or best_ask_px != ask_px

    def get_bbo(self, copy: bool = False) -> tuple[OrderbookLevel, OrderbookLevel]:
        """Get best bid and offer as a tuple."""
        self._ensure_populated()
        best_bid_px = self._sorted_bid_prices[0]
        best_ask_px = self._sorted_ask_prices[0]
        if copy:
            return self._bids[best_bid_px].copy(), self._asks[best_ask_px].copy()
        return self._bids[best_bid_px], self._asks[best_ask_px]

    def get_asks(
        self, depth: int | None = None, copy: bool = False
    ) -> list[OrderbookLevel]:
        """Get ask levels sorted by price (lowest first)."""
        self._ensure_populated()
        depth = depth if depth is not None else len(self._sorted_ask_prices)
        prices = self._sorted_ask_prices[:depth]
        if copy:
            return [self._asks[price].copy() for price in prices]
        return [self._asks[price] for price in prices]

    def get_bids(
        self, depth: int | None = None, copy: bool = False
    ) -> list[OrderbookLevel]:
        """Get bid levels sorted by price (highest first)."""
        self._ensure_populated()
        depth = depth if depth is not None else len(self._sorted_bid_prices)
        prices = self._sorted_bid_prices[:depth]
        if copy:
            return [self._bids[price].copy() for price in prices]
        return [self._bids[price] for price in prices]

    def iter_asks(self, depth: int | None = None) -> Iterator[OrderbookLevel]:
        """Iterate over ask levels sorted by price (lowest -> highest)."""
        self._ensure_populated()
        depth = depth if depth is not None else len(self._sorted_ask_prices)
        for price in self._sorted_ask_prices[:depth]:
            yield self._asks[price]

    def iter_bids(self, depth: int | None = None) -> Iterator[OrderbookLevel]:
        """Iterate over bid levels sorted by price (highest -> lowest)."""
        self._ensure_populated()
        depth = depth if depth is not None else len(self._sorted_bid_prices)
        for price in self._sorted_bid_prices[:depth]:
            yield self._bids[price]

    def get_bbo_spread(self) -> float:
        """Get the bid-ask spread."""
        self._ensure_populated()
        best_bid, best_ask = self.get_bbo(copy=False)
        return best_ask.price - best_bid.price

    def get_mid_price(self) -> float:
        """Get the mid price between best bid and ask."""
        self._ensure_populated()
        best_bid, best_ask = self.get_bbo(copy=False)
        return (best_bid.price + best_ask.price) / 2.0

    def get_wmid_price(self) -> float:
        """Get the weighted mid price between best bid and ask."""
        self._ensure_populated()
        best_bid, best_ask = self.get_bbo(copy=False)
        return (best_bid.price * best_bid.size + best_ask.price * best_ask.size) / (
            best_bid.size + best_ask.size
        )

    def get_volume_weighted_mid_price(
        self, size: float, is_base_currency: bool = True
    ) -> float:
        """Get the mid price between the price to buy and sell 'size' on the book."""
        self._ensure_populated()
        if size == 0.0:
            return self.get_mid_price()

        mid_price = self.get_mid_price()
        if is_base_currency:
            size *= mid_price

        cum_bid_size = 0.0
        buy_price = None
        for price in self._sorted_ask_prices:
            level = self._asks[price]
            if cum_bid_size + level.size >= size:
                buy_price = price
                break
            cum_bid_size += level.size
        if buy_price is None:
            return float("inf")

        cum_ask_size = 0.0
        sell_price = None
        for price in self._sorted_bid_prices:
            level = self._bids[price]
            if cum_ask_size + level.size >= size:
                sell_price = price
                break
            cum_ask_size += level.size
        if sell_price is None:
            return float("inf")

        return (buy_price + sell_price) / 2.0

    def get_price_impact(
        self, size: float, is_buy: bool, is_base_currency: bool = True
    ) -> float:
        """Get the direct price impact if a theoretical size were to be executed on the book."""
        self._ensure_populated()
        if size == 0.0:
            return 0.0

        mid_price = self.get_mid_price()
        if is_base_currency:
            size *= mid_price

        remaining_size = size
        total_cost = 0.0

        if is_buy:
            for price in self._sorted_ask_prices:
                level = self._asks[price]
                consumed_size = min(remaining_size, level.size)
                total_cost += consumed_size * price
                remaining_size -= consumed_size

                if remaining_size <= 0.0:
                    break
        else:
            for price in self._sorted_bid_prices:
                level = self._bids[price]
                consumed_size = min(remaining_size, level.size)
                total_cost += consumed_size * price
                remaining_size -= consumed_size

                if remaining_size <= 0.0:
                    break

        if remaining_size > 0.0:
            return float("inf")

        avg_execution_price = total_cost / size
        return abs(avg_execution_price - mid_price)

    def is_crossed(self, orderbook: Self) -> bool:
        """Check if the other orderbook's BBO crosses with this orderbook's BBO."""
        self._ensure_populated()
        my_best_bid, my_best_ask = self.get_bbo(copy=False)
        other_best_bid, other_best_ask = orderbook.get_bbo(copy=False)
        return (
            my_best_bid.price > other_best_ask.price
            or my_best_ask.price < other_best_bid.price
        )

    def reset(self) -> None:
        """Reset the orderbook to empty state."""
        self._asks.clear()
        self._bids.clear()
        self._sorted_ask_prices.clear()
        self._sorted_bid_prices.clear()
