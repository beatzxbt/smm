import websockets
import orjson

from src.exchanges.binance.websockets.public import PublicWs
from src.utils.misc import Misc

from src.exchanges.binance.websockets.handlers.orderbook import BinanceBBAHandler
from src.exchanges.binance.websockets.handlers.trades import BinanceTradesHandler
from src.exchanges.binance.public.client import PublicClient


class BinanceMarketData:


    def __init__(self, sharedstate) -> None:
        self.ss = sharedstate


    async def binance_data_feed(self):
        
        # Initialize the local orderbook with data \ 
        init_ob = await PublicClient(self.ss).orderbook_snapshot(500)
        self.ss.binance_book.process_snapshot(init_ob)

        streams = ['Orderbook', 'BBA', 'Trades']
        url, topics = PublicWs(self.ss).multi_stream_request(streams)
        
        async for websocket in websockets.connect(url):
            
            print(f"{Misc.current_datetime()}: Subscribed to BINANCE {topics} feeds...")

            try:
                while True:

                    recv = orjson.loads(await websocket.recv())
                    
                    if 'success' in recv:
                        pass
                    
                    else:
                        # Orderbook update \
                        if recv['stream'] == topics[0]:
                            self.ss.binance_book.process_data(recv)

                        # Realtime BBA update \
                        if recv['stream'] == topics[1]:
                            BinanceBBAHandler(self.ss, recv).process()

                        # Realtime trades update \
                        if recv['stream'] == topics[2]:
                            BinanceTradesHandler(self.ss, recv).process()
                        

            except websockets.ConnectionClosed:
                continue

            except Exception as e:
                print(e)
                raise


    async def start_feed(self):
        await self.binance_data_feed()