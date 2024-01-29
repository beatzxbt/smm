import numpy as np
from typing import Tuple, Dict, Union

from frameworks.sharedstate import SharedState
from frameworks.tools.numba_funcs import nblinspace, nbround, nbclip, nbabs
from frameworks.tools.mids import mid, wmid, vamp, weighted_vamp
from smm.features.impact_ratio import ImpactRatio
from smm.settings import SmmParameters

class Features:
    """Configure your features here!"""

    def __init__(self, market: SharedState) -> None:
        self.market = market

        self.weights = {
            "wmid": 0.25,
            "vamp": 0.25,
            "wvamp": 0.25,
        }
    
        self.mid_cache = 0

    @property
    def __market__(self):
        return self.market[]

    def _update_mid_(self, bba) -> float:
        self.mid_cache = mid(bba)
        
    def _wmid_(self, bba) -> float:
        return wmid(bba)

    def _vamp_(self, orderbook) -> float:
        return vamp(orderbook.asks, orderbook.bids)

    def _wvamp_(self, orderbook) -> float:
        return weighted_vamp(orderbook.asks, orderbook.bids)
    
    def _momentum_(self) -> float:
        return None

    def update(self) -> float:
        skew = 0
        skew += self._wmid_() * self.weights["wmid"]
        skew += self._vamp_() * self.weights["vamp"]
        skew += self._wvamp_() * self.weights["wvamp"]
        skew += self._momentum_() * self.weights["momentum"]
        return skew