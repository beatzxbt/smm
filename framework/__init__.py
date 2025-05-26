import os
from typing import Any

from framework.base.exchange import BaseExchange
from framework.base.data import BaseMarketData, BasePrivateData

type API_KEY = str
type API_SECRET = str
type KWARGS = dict[str, Any]

def load_exchange(exchange: int) -> tuple[BaseExchange, BaseMarketData, BasePrivateData, API_KEY, API_SECRET, KWARGS]:
    match exchange:
        case 0:
            from framework.binance.exchange import BinanceExchange
            from framework.binance.data import BinanceMarketData, BinancePrivateData

            BINANCE_API_KEY = os.getenv("BINANCE_API_KEY")
            BINANCE_API_SECRET = os.getenv("BINANCE_API_SECRET")

            return BinanceExchange, BinanceMarketData, BinancePrivateData, BINANCE_API_KEY, BINANCE_API_SECRET, {}
        case 1:
            from framework.bybit.exchange import BybitExchange
            from framework.bybit.data import BybitMarketData, BybitPrivateData

            BYBIT_API_KEY = os.getenv("BYBIT_API_KEY")
            BYBIT_API_SECRET = os.getenv("BYBIT_API_SECRET")

            return BybitExchange, BybitMarketData, BybitPrivateData, BYBIT_API_KEY, BYBIT_API_SECRET, {}
        
        case 2:
            from framework.okx.exchange import OkxExchange
            from framework.okx.data import OkxMarketData, OkxPrivateData

            OKX_API_KEY = os.getenv("OKX_API_KEY")
            OKX_API_SECRET = os.getenv("OKX_API_SECRET")
            OKX_API_PASSPHRASE = os.getenv("OKX_API_PASSPHRASE")

            return OkxExchange, OkxMarketData, OkxPrivateData, OKX_API_KEY, OKX_API_SECRET, {"passphrase": OKX_API_PASSPHRASE}
        case 3:
            from framework.hyperliquid.exchange import HyperliquidExchange
            from framework.hyperliquid.data import HyperliquidMarketData, HyperliquidPrivateData

            HYPERLIQUID_API_KEY = os.getenv("HYPERLIQUID_API_KEY")
            HYPERLIQUID_API_SECRET = os.getenv("HYPERLIQUID_API_SECRET")

            return HyperliquidExchange, HyperliquidMarketData, HyperliquidPrivateData, HYPERLIQUID_API_KEY, HYPERLIQUID_API_SECRET, {}
        case 4:
            from framework.paradex.exchange import ParadexExchange
            from framework.paradex.data import ParadexMarketData, ParadexPrivateData

            PARADEX_API_KEY = os.getenv("PARADEX_API_KEY")
            PARADEX_API_SECRET = os.getenv("PARADEX_API_SECRET")

            return ParadexExchange, ParadexMarketData, ParadexPrivateData, PARADEX_API_KEY, PARADEX_API_SECRET, {}
        case 5:
            from framework.extended.exchange import ExtendedExchange
            from framework.extended.data import ExtendedMarketData, ExtendedPrivateData

            EXTENDED_API_KEY = os.getenv("EXTENDED_API_KEY")
            EXTENDED_API_SECRET = os.getenv("EXTENDED_API_SECRET")

            return ExtendedExchange, ExtendedMarketData, ExtendedPrivateData, EXTENDED_API_KEY, EXTENDED_API_SECRET, {}
        case 6:
            from framework.dydx.exchange import DydxV4Exchange
            from framework.dydx.data import DydxV4MarketData, DydxV4PrivateData

            DYDX_API_KEY = os.getenv("DYDX_API_KEY")
            DYDX_API_SECRET = os.getenv("DYDX_API_SECRET")

            return DydxV4Exchange, DydxV4MarketData, DydxV4PrivateData, DYDX_API_KEY, DYDX_API_SECRET, {}
        case _:
            raise ValueError(f"Invalid exchange id; expected 0-6 but got {exchange}")