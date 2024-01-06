
import orjson
import websockets

from frameworks.tools.logger import Logger
from frameworks.exchange.hyperliquid.get.public import HyperLiquidPublicGet
from frameworks.exchange.hyperliquid.endpoints import WsStreamLinks
from frameworks.exchange.hyperliquid.websockets.handlers.kline import HyperLiquidKlineHandler
from frameworks.exchange.hyperliquid.websockets.handlers.orderbook import HyperLiquidBBAHandler
from frameworks.exchange.hyperliquid.websockets.handlers.ticker import HyperLiquidTickerHandler
from frameworks.exchange.hyperliquid.websockets.handlers.trades import HyperLiquidTradesHandler
from frameworks.exchange.hyperliquid.websockets.public import HyperLiquidPublicWsInit
from frameworks.sharedstate.market import MarketDataSharedState


class HyperLiquidMarketStream:


    def __init__(self, sharedstate: MarketDataSharedState, symbol: str) -> None:
        self.mdss = sharedstate
        self.symbol = symbol
        self.hlq = self.mdss.hyperliquid[self.symbol]

        self.logging = Logger()

        self.public_ws = HyperLiquidPublicWsInit(self.symbol)

        self.ws_req, self.ws_topics = self.public_ws.multi_stream_request(
            topics=["Orderbook", "BBA", "Trades", "Ticker", "Kline"],
            interval=1
        )

        # Dictionary to map topics to their respective handlers
        self.topic_handler_map = {
            self.ws_topics[0]: self.mdss.hlq[self.symbol]["book"].update,
            self.ws_topics[1]: HyperLiquidBBAHandler(self.mdss, self.symbol).update,
            self.ws_topics[2]: HyperLiquidTradesHandler(self.mdss, self.symbol).update,
            self.ws_topics[3]: HyperLiquidTickerHandler(self.mdss, self.symbol).update,
            self.ws_topics[4]: HyperLiquidKlineHandler(self.mdss, self.symbol).update,
        }


    async def _initialize(self):
        _klines = await HyperLiquidPublicGet(self.symbol).klines(1, 500)
        HyperLiquidKlineHandler(self.mdss, self.symbol).initialize(_klines["result"]["list"])

        _trades = await HyperLiquidPublicGet(self.symbol).trades(1000)
        HyperLiquidTradesHandler(self.mdss, self.symbol).initialize(_trades["result"]["list"])


    async def _stream(self):
        await self._initialize()
        self.logging.info("HyperLiquid market data initialized...")

        async for websocket in websockets.connect(WsStreamLinks.COMBINED_FUTURES_STREAM):
            self.logging.info(f"Subscribed to HYPERLIQUID {self.ws_topics} websocket feeds...")

            try:
                await websocket.send(self.ws_req)

                while True:
                    recv = orjson.loads(await websocket.recv())

                    if "success" in recv:
                        continue

                    handler = self.topic_handler_map.get(recv["topic"])

                    if handler:
                        handler(recv)

            except websockets.ConnectionClosed:
                self.logging.critical(f"Disconnected from HYPERLIQUID {self.ws_topics} websocket feeds...reconnecting...")
                continue

            except Exception as e:
                self.logging.critical(e)
                raise e


    async def start_feed(self):
        await self._stream()
