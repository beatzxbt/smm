from typing import Dict, List, Tuple, Optional, Iterator

from framework.base.internal_structs import OrderbookLevel

class Orderbook:
    """
    An orderbook class maintaining separate dictionaries for bid and
    ask orders with functionality to initialize, update, and access
    best bid/offer information.
    """

    def __init__(
            self, 
            size: int=500, 
            initial_bids: Optional[List[OrderbookLevel]]=None, 
            initial_asks: Optional[List[OrderbookLevel]]=None
        ) -> None:
        self._size = size

        self._asks: Dict[float, OrderbookLevel] = {}
        self._bids: Dict[float, OrderbookLevel] = {}
        
        self._sorted_ask_pxs: List[float] = []
        self._sorted_bid_pxs: List[float] = []

        self._is_populated = False
        
        if initial_bids is not None and initial_asks is not None:
            self.update(
                bids=initial_bids, 
                asks=initial_asks, 
                is_snapshot=True
            )
    
    def _ensure_populated(self) -> None:
        """Check if the orderbook is populated."""
        if not self._is_populated:
            raise ValueError("Orderbook is not populated.")
    
    def _ensure_snapshot_validity(self, bids: List[OrderbookLevel], asks: List[OrderbookLevel]) -> None:
        """Check if the snapshot is valid."""
        len_bids = len(bids)
        if len(bids) != self._size:
            raise ValueError(f"Invalid bids with snapshot; expected {self._size} bids but got {len_bids}.")
        
        len_asks = len(asks)
        if len(asks) != self._size:
            raise ValueError(f"Invalid asks with snapshot; expected {self._size} asks but got {len_asks}.")
        
    def _remove_ask(self, px: float) -> None:
        """Remove an ask level."""
        if px in self._asks:
            del self._asks[px]
            self._sorted_ask_pxs.remove(px)
    
    def _remove_bid(self, px: float) -> None:
        """Remove a bid level."""
        if px in self._bids:
            del self._bids[px]
            self._sorted_bid_pxs.remove(px)
    
    def update(self, bids: List[OrderbookLevel], asks: List[OrderbookLevel], is_snapshot: bool = False) -> None:
        """Update the orderbook.
        
        Args:
            bids: List of bid levels.
            asks: List of ask levels.
            is_snapshot: Whether this is a snapshot update.
        """
        if is_snapshot:
            self._ensure_snapshot_validity(bids, asks)

            self.reset()
    
            for ask in asks:
                self._asks[ask.px] = ask
                self._sorted_ask_pxs.append(ask.px)
            self._sorted_ask_pxs.sort()

            for bid in bids:
                self._bids[bid.px] = bid
                self._sorted_bid_pxs.append(bid.px)
            self._sorted_bid_pxs.sort(reverse=True)

            # As we allow for the orderbook to be not populated directly on initialization,
            # we allow it here as a snapshot serves the same purpose in a cheap way.
            self._is_populated = True

        else:
            for ask in asks:
                if ask.sz == 0.0:
                    self._remove_ask(ask.px)
                else:
                    if ask.px not in self._asks:
                        self._sorted_ask_pxs.append(ask.px)
                        self._sorted_ask_pxs.sort()
                    self._asks[ask.px] = ask

            for bid in bids:
                if bid.sz == 0.0:
                    self._remove_bid(bid.px)
                else:
                    if bid.px not in self._bids:
                        self._sorted_bid_pxs.append(bid.px)
                        self._sorted_bid_pxs.sort(reverse=True)
                    self._bids[bid.px] = bid

    def update_bbo(self, bid: OrderbookLevel, ask: OrderbookLevel) -> None:
        """Update the best bid and offer. BBO updates usually don't 
        supply sz=0 updates for signalling level deletion, and directly
        provide the new best bid/ask if available. Therefore, we ignore it
        and directly update the best bid/ask for now, fixing any issues
        arising with the orderbook by assuming this source of truth.
        
        Args: 
            bid: Best bid level.
            ask: Best ask level.
        """
        # Handle bid update
        if bid.sz == 0:
            # Remove current best bid if it exists
            if self._sorted_bid_pxs:
                best_bid_px = self._sorted_bid_pxs[0]
                if best_bid_px in self._bids:
                    del self._bids[best_bid_px]
                    self._sorted_bid_pxs.remove(best_bid_px)
        else:
            # Update or replace the best bid
            if self._sorted_bid_pxs and bid.px in self._bids:
                # Update existing best bid
                self._bids[bid.px] = bid
            else:
                # New best bid - remove old best if exists and add new one
                if self._sorted_bid_pxs:
                    old_best_px = self._sorted_bid_pxs[0]
                    if old_best_px != bid.px and old_best_px in self._bids:
                        del self._bids[old_best_px]
                        self._sorted_bid_pxs.remove(old_best_px)
                
                self._bids[bid.px] = bid
                if bid.px not in self._sorted_bid_pxs:
                    self._sorted_bid_pxs.append(bid.px)
                    self._sorted_bid_pxs.sort(reverse=True)
        
        # Handle ask update
        if ask.sz == 0:
            # Remove current best ask if it exists
            if self._sorted_ask_pxs:
                best_ask_px = self._sorted_ask_pxs[0]
                if best_ask_px in self._asks:
                    del self._asks[best_ask_px]
                    self._sorted_ask_pxs.remove(best_ask_px)
        else:
            # Update or replace the best ask
            if self._sorted_ask_pxs and ask.px in self._asks:
                # Update existing best ask
                self._asks[ask.px] = ask
            else:
                # New best ask - remove old best if exists and add new one
                if self._sorted_ask_pxs:
                    old_best_px = self._sorted_ask_pxs[0]
                    if old_best_px != ask.px and old_best_px in self._asks:
                        del self._asks[old_best_px]
                        self._sorted_ask_pxs.remove(old_best_px)
                
                self._asks[ask.px] = ask
                if ask.px not in self._sorted_ask_pxs:
                    self._sorted_ask_pxs.append(ask.px)
                    self._sorted_ask_pxs.sort()
    
    def get_bbo(self) -> Tuple[Optional[OrderbookLevel], Optional[OrderbookLevel]]:
        """Get best bid and offer.
        
        Returns:
            Tuple of (best_bid, best_ask). Either can be None if no levels exist.
        """
        self._ensure_populated()
        best_bid_px = self._sorted_bid_pxs[0]
        best_ask_px = self._sorted_ask_pxs[0]
        return self._bids[best_bid_px], self._asks[best_ask_px]
    
    def get_asks(self, depth: Optional[int] = None) -> List[OrderbookLevel]:
        """Get ask levels sorted by price (lowest first).
        
        Args:
            depth: Maximum number of levels to return. If None, returns all.
            
        Returns:
            List of ask levels sorted by price.
        """
        self._ensure_populated()
        pxs = self._sorted_ask_pxs[:depth] if depth else self._sorted_ask_pxs
        return [self._asks[px] for px in pxs]
    
    def iter_asks(self) -> Iterator[OrderbookLevel]:
        """Iterate over ask levels sorted by price (lowest first).
        
        Args:
            depth: Maximum number of levels to return. If None, returns all.
        """
        self._ensure_populated()
        for px in self._sorted_ask_pxs:
            yield self._asks[px]

    def get_bids(self, depth: Optional[int] = None) -> List[OrderbookLevel]:
        """Get bid levels sorted by price (highest first).
        
        Args:
            depth: Maximum number of levels to return. If None, returns all.
            
        Returns:
            List of bid levels sorted by price.
        """
        self._ensure_populated()
        pxs = self._sorted_bid_pxs[:depth] if depth else self._sorted_bid_pxs
        return [self._bids[px] for px in pxs]
    
    def iter_bids(self) -> Iterator[OrderbookLevel]:
        """Iterate over bid levels sorted by price (highest first).
        
        Args:
            depth: Maximum number of levels to return. If None, returns all.
        """
        self._ensure_populated()
        for px in self._sorted_bid_pxs: 
            yield self._bids[px]

    def get_bbo_spread(self) -> Optional[float]:
        """Get the bid-ask spread.
        
        Returns:
            The spread (ask - bid) or None if BBO is incomplete.
        """
        self._ensure_populated()
        best_bid, best_ask = self.get_bbo()
        return best_ask.px - best_bid.px
    
    def get_mid_px(self) -> Optional[float]:
        """Get the mid price between best bid and ask.
        
        Returns:
            The mid price or None if BBO is incomplete.
        """
        self._ensure_populated()
        best_bid, best_ask = self.get_bbo()
        return (best_bid.px + best_ask.px) / 2.0
    
    def get_wmid_px(self) -> Optional[float]:
        """Get the weighted mid price between best bid and ask.
        
        Returns:
            The weighted mid price or None if BBO is incomplete.
        """
        self._ensure_populated()
        best_bid, best_ask = self.get_bbo()
        return (best_bid.px * best_bid.sz + best_ask.px * best_ask.sz) / (best_bid.sz + best_ask.sz)
    
    def get_sz_impact(self, sz: float, is_buy: bool, is_base_currency: bool = True) -> float:
        """Get the direct price impact if a theoretical size were to be executed on the book.
        
        Args:
            sz: The size of the trade to simulate.
            is_buy: True for buy order (consuming asks), False for sell order (consuming bids).
            is_base_currency: Whether the trade is in the base currency.

        Returns:
            The price impact as the difference between execution price and mid price.
            Returns 0.0 if no impact or insufficient liquidity.
        """
        self._ensure_populated()
        if sz == 0.0:
            return 0.0
        
        mid_px = self.get_mid_px()
        if is_base_currency:
            sz *= mid_px
        
        remaining_sz = sz
        total_cost = 0.0
        
        if is_buy:
            # Consuming asks (buying)
            for px in self._sorted_ask_pxs:
                level = self._asks[px]
                consumed_sz = min(remaining_sz, level.sz)
                total_cost += consumed_sz * px
                remaining_sz -= consumed_sz
                
                if remaining_sz <= 0.0:
                    break
        else:
            # Consuming bids (selling)
            for px in self._sorted_bid_pxs:
                level = self._bids[px]
                consumed_sz = min(remaining_sz, level.sz)
                total_cost += consumed_sz * px
                remaining_sz -= consumed_sz
                
                if remaining_sz <= 0.0:
                    break
        
        if remaining_sz > 0.0:
            return float('inf')
        
        avg_execution_px = total_cost / sz
        return abs(avg_execution_px - mid_px)

    def is_crossed(self, orderbook: 'Orderbook') -> bool:
        """Check if the orderbook is crossed.
        
        Returns:
            True if the orderbook is crossed, False otherwise.
        """
        # Other's BBO call already checks for populatedness
        self._ensure_populated()
        
        my_best_bid, my_best_ask = self.get_bbo()
        other_best_bid, other_best_ask = orderbook.get_bbo()
        return my_best_bid.px > other_best_ask.px or my_best_ask.px < other_best_bid.px

    def reset(self) -> None:
        """Reset the orderbook to empty state."""
        self._asks.clear()
        self._bids.clear()
        self._sorted_ask_pxs.clear()
        self._sorted_bid_pxs.clear()