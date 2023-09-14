
import orjson
import websockets

from src.utils.misc import curr_dt
from src.exchanges.binance.get.client import BinancePublicGet
from src.exchanges.binance.websockets.handlers.orderbook import BinanceBBAHandler
from src.exchanges.binance.websockets.handlers.trades import BinanceTradesHandler
from src.exchanges.binance.websockets.public import BinancePublicWs
from src.sharedstate import SharedState


class BinanceMarketData:


    def __init__(self, sharedstate: SharedState) -> None:
        self.ss = sharedstate

        self.public_ws = BinancePublicWs(self.ss)

        self.ws_url, self.ws_topics = self.public_ws.multi_stream_request(
            topics=["Orderbook", "BBA", "Trades"]
        )

        # Dictionary to map topics to their respective handlers
        self.stream_handler_map = {
            self.ws_topics[0]: self.ss.binance_book.process,
            self.ws_topics[1]: BinanceBBAHandler(self.ss).process,
            self.ws_topics[2]: BinanceTradesHandler(self.ss).process,
        }


    async def initialize_data(self):
        init_ob = await BinancePublicGet(self.ss).orderbook_snapshot(500)
        self.ss.binance_book.process_snapshot(init_ob)

        init_trades = await BinancePublicGet(self.ss).trades_snapshot(1000)
        BinanceTradesHandler(self.ss)._init(init_trades)


    async def binance_data_feed(self):
        await self.initialize_data()

        async for websocket in websockets.connect(self.ws_url):
            print(f"{curr_dt()}: Subscribing to BINANCE {self.ws_topics} feeds...")

            try:
                while True:
                    recv = orjson.loads(await websocket.recv())

                    if "success" not in recv:
                        handler = self.stream_handler_map.get(recv["stream"])

                        if handler:
                            handler(recv)

            except websockets.ConnectionClosed:
                continue

            except Exception as e:
                print(e)
                raise


    async def start_feed(self):
        await self.binance_data_feed()