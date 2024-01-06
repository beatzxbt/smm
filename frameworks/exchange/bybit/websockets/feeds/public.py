
import orjson
import websockets

from frameworks.tools.logger import Logger
from frameworks.exchange.bybit.get.public import BybitPublicGet
from frameworks.exchange.bybit.endpoints import WsStreamLinks
from frameworks.exchange.bybit.websockets.handlers.kline import BybitKlineHandler
from frameworks.exchange.bybit.websockets.handlers.orderbook import BybitBBAHandler
from frameworks.exchange.bybit.websockets.handlers.ticker import BybitTickerHandler
from frameworks.exchange.bybit.websockets.handlers.trades import BybitTradesHandler
from frameworks.exchange.bybit.websockets.public import BybitPublicWsInit
from frameworks.sharedstate.market import MarketDataSharedState


class BybitMarketStream:


    def __init__(self, sharedstate: MarketDataSharedState, symbol: str) -> None:
        self.mdss = sharedstate
        self.symbol = symbol
        self.bybit = self.mdss.bybit[self.symbol]

        self.logging = Logger()

        self.public_ws = BybitPublicWsInit(self.symbol)

        self.ws_req, self.ws_topics = self.public_ws.multi_stream_request(
            topics=["Orderbook", "BBA", "Trades", "Ticker", "Kline"],
            interval=1
        )

        # Dictionary to map topics to their respective handlers
        self.topic_handler_map = {
            self.ws_topics[0]: self.mdss.bybit[self.symbol]["book"].update,
            self.ws_topics[1]: BybitBBAHandler(self.mdss, self.symbol).update,
            self.ws_topics[2]: BybitTradesHandler(self.mdss, self.symbol).update,
            self.ws_topics[3]: BybitTickerHandler(self.mdss, self.symbol).update,
            self.ws_topics[4]: BybitKlineHandler(self.mdss, self.symbol).update,
        }


    async def _initialize(self):
        _klines = await BybitPublicGet(self.symbol).klines(1, 500)
        BybitKlineHandler(self.mdss, self.symbol).initialize(_klines["result"]["list"])

        _trades = await BybitPublicGet(self.symbol).trades(1000)
        BybitTradesHandler(self.mdss, self.symbol).initialize(_trades["result"]["list"])

        

    async def _stream(self):
        await self._initialize()
        self.logging.info("Bybit market data initialized...")

        async for websocket in websockets.connect(WsStreamLinks.FUTURES_PUBLIC_STREAM):
            self.logging.info(f"Subscribed to BYBIT {self.ws_topics} websocket feeds...")

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
                self.logging.critical(f"Disconnected from BYBIT {self.ws_topics} websocket feeds...reconnecting...")
                continue

            except Exception as e:
                self.logging.critical(e)
                raise e


    async def start_feed(self):
        await self._stream()
