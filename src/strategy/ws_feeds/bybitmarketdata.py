import asyncio
import websockets
import orjson

from src.bybit.public.client import Client as PublicClient
from src.bybit.websockets.endpoints import WsStreamLinks
from src.bybit.websockets.public import PublicWs
from src.utils.misc import Misc

from src.bybit.websockets.handlers.orderbook import BybitBBAHandler
from src.bybit.websockets.handlers.kline import BybitKlineHandler, BybitKlineInit
from src.bybit.websockets.handlers.ticker import BybitTickerHandler
from src.bybit.websockets.handlers.trades import BybitTradesHandler



class BybitMarketData:


    def __init__(self, sharedstate) -> None:
        self.ss = sharedstate


    async def bybit_data_feed(self):
        
        init_kline_data = await PublicClient('Futures').klines(self.ss.bybit_symbol, 15)
        init_kline_ss = BybitKlineInit(self.ss, init_kline_data).process()

        streams = ['Orderbook', 'BBA', 'Trades', 'Ticker', 'Kline']
        req, topics = PublicWs(self.ss.bybit_symbol).multi_stream_request(streams, depth=500, interval=15)
        
        async for websocket in websockets.connect(WsStreamLinks.futures_public_stream()):
            
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