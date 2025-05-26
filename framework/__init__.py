import os

from framework.base.exchange import BaseExchange
from framework.base.data import BaseMarketData, BasePrivateData

type API_KEY = str
type API_SECRET = str

def load_exchange(exchange: int) -> tuple[BaseExchange, BaseMarketData, BasePrivateData, API_KEY, API_SECRET]:
    match exchange:
        # case 0:
        #     from framework.binance.exchange import Binance
        #     from framework.binance.data import Binance
        #     return Binance()
        case 1:
            from framework.bybit.exchange import Bybit
            from framework.bybit.data import BybitMarketData, BybitPrivateData

            BYBIT_API_KEY = os.getenv("BYBIT_API_KEY")
            BYBIT_API_SECRET = os.getenv("BYBIT_API_SECRET")

            return Bybit, BybitMarketData, BybitPrivateData, BYBIT_API_KEY, BYBIT_API_SECRET
        
        case 2:
            from framework.okx.exchange import Okx
            from framework.okx.data import OkxMarketData, OkxPrivateData

            OKX_API_KEY = os.getenv("OKX_API_KEY")
            OKX_API_SECRET = os.getenv("OKX_API_SECRET")
            OKX_API_PASSPHRASE = os.getenv("OKX_API_PASSPHRASE")

            return Okx, OkxMarketData, OkxPrivateData, OKX_API_KEY, OKX_API_SECRET, OKX_API_PASSPHRASE
        # case 3:
        #     from framework.hyperliquid.exchange import Hyperliquid
        #     return Hyperliquid()
        # case 4:
        #     from framework.paradex.exchange import Paradex
        #     return Paradex()
        # case 5:
        #     from framework.x10.exchange import X10
        #     return X10()
        case _:
            raise ValueError(f"Invalid exchange id; expected 0-5 but got {exchange}")