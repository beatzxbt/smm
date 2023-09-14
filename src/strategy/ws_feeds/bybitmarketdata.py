
import orjson
import websockets

from src.utils.misc import curr_dt
from src.exchanges.bybit.get.public import BybitPublicClient
from src.exchanges.bybit.endpoints import WsStreamLinks
from src.exchanges.bybit.websockets.handlers.kline import BybitKlineHandler
from src.exchanges.bybit.websockets.handlers.orderbook import BybitBBAHandler
from src.exchanges.bybit.websockets.handlers.ticker import BybitTickerHandler
from src.exchanges.bybit.websockets.handlers.trades import BybitTradesHandler
from src.exchanges.bybit.websockets.public import BybitPublicWs
from src.sharedstate import SharedState


class BybitMarketData:


    def __init__(self, sharedstate: SharedState) -> None:
        self.ss = sharedstate

        self.public_ws = BybitPublicWs(self.ss)

        self.ws_req, self.ws_topics = self.public_ws.multi_stream_request(
            topics=["Orderbook", "BBA", "Trades", "Ticker", "Kline"], 
            depth=500, 
            interval=1
        )

        # Dictionary to map topics to their respective handlers
        self.topic_handler_map = {
            self.ws_topics[0]: self.ss.bybit_book.process,
            self.ws_topics[1]: BybitBBAHandler(self.ss).process,
            self.ws_topics[2]: BybitTradesHandler(self.ss).process,
            self.ws_topics[3]: BybitTickerHandler(self.ss).process,
            self.ws_topics[4]: BybitKlineHandler(self.ss).process,
        }


    async def initialize_data(self):
        init_klines = await BybitPublicClient(self.ss).klines(1, 500)
        BybitKlineHandler(self.ss)._init(init_klines["result"]["list"])

        init_trades = await BybitPublicClient(self.ss).trades(1000)
        BybitTradesHandler(self.ss)._init(init_trades["result"]["list"])


    async def bybit_data_feed(self):
        await self.initialize_data()

        async for websocket in websockets.connect(WsStreamLinks.FUTURES_PUBLIC_STREAM):
            print(f"{curr_dt()}: Subscribing to BYBIT {self.ws_topics} feeds...")

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
                continue

            except Exception as e:
                print(e)
                raise


    async def start_feed(self):
        await self.bybit_data_feed()