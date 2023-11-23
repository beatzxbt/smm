import numpy as np
from numpy_ringbuffer import RingBuffer

class MarketDataSharedState:

    def __init__(self, params) -> None:
        self.binance_symbols, self.bybit_symbols, self.hyperlyquid_symbols = [], [], []

        exchange_handlers = {
            "BINANCE": "frameworks.exchange.binance.websockets.handlers.orderbook.OrderBookBinance",
            "BYBIT": "frameworks.exchange.bybit.websockets.handlers.orderbook.OrderBookBybit",
            "HYPERLIQUID": "frameworks.exchange.hyperliquid.websockets.handlers.orderbook.OrderBookHyperLiquid",
        }

        for exchange, ticker in params.symbols:
            getattr(self, f"{exchange.lower()}_symbols").append(ticker)

        self.binance = self._create_exchange_dict(exchange_handlers["BINANCE"], self.binance_symbols)
        self.bybit = self._create_exchange_dict(exchange_handlers["BYBIT"], self.bybit_symbols)
        self.hyperliquid = self._create_exchange_dict(exchange_handlers["HYPERLIQUID"], self.hyperlyquid_symbols)  

    def _create_exchange_dict(self, handler_path, symbols):
            handler_class = self._dynamic_import(handler_path)
            return {symbol: self._base_data_outline(handler_class()) for symbol in symbols}

    def _base_data_outline(self, orderbook):
        """
        Base dict for all exchange market data

        Values with 'None' will be populated in '__init__'
        """

        return {
            "trades": RingBuffer(capacity=1000, dtype=(float, 4)),
            "klines": RingBuffer(capacity=1000, dtype=(float, 7)),
            "bba": np.ones((2, 2)), # [Bid[P, Q], Ask[P, Q]]
            "liquidations": RingBuffer(capacity=1000, dtype=(float, 5)),
            "book": orderbook, 

            "mark_price": 0,
            "index_price": 0,
            "last_price": 0,
            "mid_price": 0,
            "wmid_price": 0,
            "funding_rate": 0,
            "volume_24h": 0,

            "tick_size": 0,
            "lot_size": 0
        }
    
    @staticmethod
    def _dynamic_import(class_path):
        module_path, class_name = class_path.rsplit('.', 1)
        module = __import__(module_path, fromlist=[class_name])
        return getattr(module, class_name)



class MarketDataWebsocketStream:
    """
    This class spawns the relevant market data streams on chosen 
    exchanges
    """

    def __init__(self, mdss: MarketDataSharedState, symbols: list[str, str]) -> None:
        self.mdss = mdss
        self.symbols = symbols
    
    async def run(self):
        tasks = []

        for exchange, symbol in self.symbols:

            if "BINANCE" == exchange:
                from frameworks.exchange.binance.websockets.feeds.public import BinanceMarketStream
                tasks.append(await BinanceMarketStream(self.mdss, symbol).start_feed())
                continue

            if "BYBIT" == exchange:
                from frameworks.exchange.bybit.websockets.feeds.public import BybitMarketStream
                tasks.append(await BybitMarketStream(self.mdss, symbol).start_feed())
                continue

            # if "HYPERLIQUID" == exchange:
            #     tasks.append(HyperLiquidMarketStream(self.mdss, symbol).start_feed())
            #     continue
