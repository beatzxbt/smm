import websockets
import orjson

from src.utils.misc import Misc
from src.exchanges.bybit.get.public import BybitPublicClient

from src.exchanges.bybit.websockets.endpoints import WsStreamLinks
from src.exchanges.bybit.websockets.public import PublicWs
from src.exchanges.bybit.websockets.handlers.orderbook import BybitBBAHandler
from src.exchanges.bybit.websockets.handlers.kline import BybitKlineHandler, BybitKlineInit
from src.exchanges.bybit.websockets.handlers.ticker import BybitTickerHandler
from src.exchanges.bybit.websockets.handlers.trades import BybitTradesHandler, BybitTradesInit

from src.sharedstate import SharedState


class BybitMarketData:


    def __init__(self, sharedstate: SharedState) -> None:
        self.ss = sharedstate


    async def initialize_data(self):
        
        # Initialize the klines data with a snapshot of 200 candles of M1 \
        init_kline_data = await BybitPublicClient(self.ss).klines(1)
        BybitKlineInit(self.ss, init_kline_data).process()

        # Initialize the trades feed to full capacity \ 
        init_trades = await BybitPublicClient(self.ss).trades(1000)
        BybitTradesInit(self.ss, init_trades).process()


    async def bybit_data_feed(self):
        
        await self.initialize_data()

        streams = ['Orderbook', 'BBA', 'Trades', 'Ticker', 'Kline']
        req, topics = PublicWs(self.ss).multi_stream_request(streams, depth=500, interval=1)
        
        async for websocket in websockets.connect(WsStreamLinks.FUTURES_PUBLIC_STREAM):
            
            print(f"{Misc.current_datetime()}: Subscribed to BYBIT {topics} feed...")

            try:
                # Subscribe to the stream \
                await websocket.send(req)

                while True:

                    recv = orjson.loads(await websocket.recv())
                    
                    if 'success' in recv:
                        pass
                    
                    else:
                        data = recv['data']

                        # Orderbook update \
                        if recv['topic'] == topics[0]:
                            self.ss.bybit_book.process_data(recv)

                        # Realtime BBA update \
                        if recv['topic'] == topics[1]:
                            BybitBBAHandler(self.ss, data).process()

                        # Realtime trades update \
                        if recv['topic'] == topics[2]:
                            BybitTradesHandler(self.ss, data).process()

                        # Ticker update \
                        if recv['topic'] == topics[3]:
                            BybitTickerHandler(self.ss, data).process()

                        # Klines update \
                        if recv['topic'] == topics[4]:
                            BybitKlineHandler(self.ss, data).process()


            except websockets.ConnectionClosed:
                continue

            except Exception as e:
                print(e)
                raise


    async def start_feed(self):
        await self.bybit_data_feed()