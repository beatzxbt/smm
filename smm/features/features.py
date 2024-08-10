import numpy as np

from frameworks.exchange.base.structures.orderbook import Orderbook
from frameworks.exchange.base.structures.trades import Trades
from smm.sharedstate import SmmSharedState

from smm.features.trades_diff import trades_diffs
from smm.features.trades_imbalance import trades_imbalance
from smm.features.orderbook_imbalance import orderbook_imbalance


class FeatureEngine:
    def __init__(self, ss: SmmSharedState) -> None:
        self.data = ss.data

        self.fair_price_weights = {
            "wmid": 0.10,
            "tight_vamp": 0.10,
            "mid_vamp": 0.15,
            "deep_vamp": 0.15,
            "book_imb": 0.25,
            "trades_imb": 0.25,
        }

        self.volatility_weights = {"trades_diffs": 1.0}

    @property
    def orderbook(self) -> Orderbook:
        return self.data["orderbook"]
    
    @property
    def trades(self) -> Trades:
        return self.data["trades"]
    
    def wmid_imbalance(self) -> float:
        """
        Calculate the weighted mid-price imbalance.

        Returns
        -------
        float
            The logarithm of the ratio between the weighted mid-price and the mid-price.
        """
        return np.log(self.orderbook.get_wmid() / self.orderbook.get_mid())

    def vamp_imbalance(self, depth: float) -> float:
        """
        Calculate the volume adjusted mid-price imbalance.

        Parameters
        ----------
        depth : float
            The depth in dollars used to calculate the volume adjusted mid-price.

        Returns
        -------
        float
            The logarithm of the ratio between the volume adjusted mid-price and the mid-price.
        """
        dollars_to_size = depth / self.orderbook.get_mid()
        return np.log(self.orderbook.get_vamp(dollars_to_size) / self.orderbook.get_mid())

    def orderbook_imbalance(self) -> float:
        """
        Calculate the order book imbalance. A more in-depth description of
        this feature can be found in it's docstring.

        Returns
        -------
        float
            The order book imbalance based on predefined depths.

        """
        return orderbook_imbalance(
            bids=self.orderbook.bids,
            asks=self.orderbook.asks,
            depths=np.array([10.0, 25.0, 50.0, 100.0, 250.0]),
        )

    def trades_imbalance(self) -> float:
        """
        Calculate the trades imbalance. A more in-depth description of
        this feature can be found in it's docstring.

        Returns
        -------
        float
            The trades imbalance over a predefined window.
        """
        return trades_imbalance(trades=self.trades.unwrap(), window=100)

    def trades_differences(self) -> float:
        """
        Calculate the trades differences. A more in-depth description of
        this feature can be found in it's docstring.

        Returns
        -------
        float
            The trades differences over a predefined lookback period.
        """
        return trades_diffs(trades=self.trades.unwrap(), lookback=100)

    def generate_skew(self) -> float:
        """
        Generate the skew feature. Adds custom weighted values for the price
        predictive features into a single value.

        Returns
        -------
        float
            The calculated skew based on various imbalance measures.
        """
        skew = 0.0
        skew += self.wmid_imbalance() * self.fair_price_weights["wmid"]
        skew += self.vamp_imbalance(depth=25000.0) * self.fair_price_weights["tight_vamp"]
        skew += self.vamp_imbalance(depth=75000.0) * self.fair_price_weights["mid_vamp"]
        skew += self.vamp_imbalance(depth=200000.0) * self.fair_price_weights["deep_vamp"]
        skew += self.orderbook_imbalance() * self.fair_price_weights["book_imb"]
        skew += self.trades_imbalance() * self.fair_price_weights["trades_imb"]
        return skew

    def generate_vol(self) -> float:
        """
        Generate the volatility feature. Adds custom weighted values for the vol
        predictive features into a single value.

        Returns
        -------
        float
            The calculated volatility based on trades differences.
        """
        vol = 0.0
        vol += self.trades_differences() * self.volatility_weights["trades_diffs"]
        return vol
