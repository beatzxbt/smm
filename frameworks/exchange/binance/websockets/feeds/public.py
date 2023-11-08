
import orjson
import websockets

from frameworks.tools.logging.logger import Logger
from frameworks.exchange.binance.get.public import BinancePublicGet
from frameworks.exchange.binance.websockets.handlers.orderbook import BinanceBBAHandler
from frameworks.exchange.binance.websockets.handlers.trades import BinanceTradesHandler
from frameworks.exchange.binance.websockets.public import BinancePublicWs
from frameworks.sharedstate.market import MarketDataSharedState


class BinanceMarketStream:


    def __init__(self, sharedstate: MarketDataSharedState, symbol: str) -> None:
        self.mdss = sharedstate
        self.symbol = symbol
        self.binance = self.mdss.binance[self.symbol]

        self.logging = Logger()

        self.ws_url, self.ws_topics = BinancePublicWs().multi_stream_request(
            symbol=self.symbol,
            topics=["Orderbook", "BBA", "Trades", "Kline"] # Add liq stream
        )

        # Dictionary to map topics to their respective handlers
        self.stream_handler_map = {
            self.ws_topics[0]: self.binance[self.symbol]["book"].update,
            self.ws_topics[1]: BinanceBBAHandler(self.mdss).update,
            self.ws_topics[2]: BinanceTradesHandler(self.mdss).update,
        }


    async def _initialize(self):
        _orderbook = await BinancePublicGet(self.symbol).orderbook(500)
        self.binance["book"].initialize(_orderbook)

        _trades = await BinancePublicGet(self.symbol).trades(1000)
        BinanceTradesHandler(self.mdss).initialize(_trades)


    async def _stream(self):
        await self._initialize()
        self.logging.info("Binance market data initialized...")

        async for websocket in websockets.connect(self.ws_url):
            self.logging.info(f"Subscribed to BINANCE {self.ws_topics} websocket feeds...")

            try:
                while True:
                    recv = orjson.loads(await websocket.recv())

                    if "success" not in recv:
                        handler = self.stream_handler_map.get(recv["stream"])

                        if handler:
                            handler(recv)

            except websockets.ConnectionClosed:
                self.logging.critical(f"Disconnected from BYBIT {self.ws_topics} websocket feeds...reconnecting...")
                continue

            except Exception as e:
                self.logging.critical(e)
                raise e


    async def start_feed(self):
        await self._stream()
