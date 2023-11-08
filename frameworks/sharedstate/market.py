import numpy as np
from numpy_ringbuffer import RingBuffer

class MarketDataSharedState:

    def __init__(self, params) -> None:
        self.binance_symbols = [] 
        self.bybit_symbols = [] 
        self.hyperliquid_symbols = [] 

        if self.binance_symbols:
            from frameworks.exchange.binance.websockets.handlers.orderbook import OrderBookBinance
            self.binance = {f"{symbol}": self._base_data_outline(OrderBookBinance()) for symbol in self.binance_symbols}

        if self.bybit_symbols:
            from frameworks.exchange.bybit.websockets.handlers.orderbook import OrderBookBybit
            self.bybit = {f"{symbol}": self._base_data_outline(OrderBookBybit()) for symbol in self.bybit_symbols}

        # if self.hyperliquid_symbols:
        #     self.hyperliquid = {f"{symbol}": self._base_data_outline() for symbol in self.hyperliquid_symbols}
        #     self.hyperliquid["book"] = OrderBookHyperliquid() 
    

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
