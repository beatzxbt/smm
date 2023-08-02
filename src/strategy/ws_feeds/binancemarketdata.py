import websockets
import orjson

from src.binance.websockets.public import PublicWs
from src.utils.misc import Misc

from src.binance.websockets.handlers.orderbook import BinanceBBAHandler
from src.binance.websockets.handlers.trades import BinanceTradesHandler



class BinanceMarketData:


    def __init__(self, sharedstate) -> None:
        self.ss = sharedstate


    async def binance_data_feed(self):
        
        streams = ['Orderbook', 'BBA', 'Trades']
        url, topics = PublicWs(self.ss.binance_symbol).multi_stream_request(streams, depth=500)
        
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