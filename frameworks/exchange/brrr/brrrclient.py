from typing import Dict
from frameworks.exchange.base.rest.exchange import Exchange


class BrrrClient:
    def __init__(self, exchange: str, market: Dict, private: Dict) -> Exchange:
        self.exchange = exchange
        self.market, self.private = market, private
        return self._find_client_()

    def _find_client_(self):
        if self.exchange == "binance":
            from frameworks.exchange.brrr.binance.exchange import Binance

            return Binance(self.market, self.private)

        elif self.exchange == "bybit":
            from frameworks.exchange.brrr.bybit.exchange import Bybit

            return Bybit(self.market, self.private)

        # elif self.exchange == "okx":
        #     from frameworks.exchange.brrrclient.okx.exchange import Okx
        #     return Okx(self.market, self.private)

        # elif self.exchange == "hyperliquid":
        #     from frameworks.exchange.brrrclient.hyperliquid.exchange import Hyperliquid
        #     return Hyperliquid(self.market, self.private)

        # elif self.exchange == "kucoin":
        #     from frameworks.exchange.brrrclient.kucoin.exchange import Kucoin
        #     return Kucoin(self.market, self.private)

        else:
            raise ValueError(f"Unsupported custom exchange: {self.exchange}")
