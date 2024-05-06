import numpy as np
from abc import ABC
from numpy.typing import NDArray
from typing import Tuple

from smm.sharedstate import SmmSharedState


class QuoteGenerator(ABC):
    def __init__(self, ss: SmmSharedState) -> None:
        self.ss = ss
        self.params = self.ss.parameters
        self.tick_size = self.ss.misc["tick_size"]
        self.lot_size = self.ss.misc["lot_size"]

    @property
    def mid(self) -> float:
        return self.ss.orderbook.get_mid()
    
    @property
    def wmid_price(self) -> float:
        return self.ss.orderbook.get_wmid()
    
    @property
    def live_best_bid(self) -> NDArray:
        return self.ss.orderbook.bids[0]
    
    @property
    def live_best_ask(self) -> NDArray:
        return self.ss.orderbook.asks[0]
    
    @property
    def inventory_delta(self) -> float:
        return self.ss.current_position["size"] / self.ss.parameters["max_position"]
    
    def bps_to_decimal(self, bps: float) -> float:
        return bps / 10000
    
    def bps_offset_to_decimal(self, bps: float) -> float:
        return self.mid + (self.mid * self.bps_to_decimal(bps))
    
    def offset_to_decimal(self, offset: float) -> float:
        return self.mid + (self.mid * offset)
        
    def generate_single_quote(self, side: float, orderType: float, price: float, size: float) -> Tuple[float, float, float, float]:
        return (side, orderType, price, size)