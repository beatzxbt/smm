import websockets
import orjson

from src.bybit.websockets.endpoints import WsStreamLinks
from src.bybit.websockets.private import PrivateWs
from src.utils.misc import Misc

from src.bybit.websockets.handlers.execution import BybitExecutionHandler
from src.bybit.websockets.handlers.position import BybitPositionHandler



class BybitPrivateData:


    def __init__(self, sharedstate) -> None:
        
        self.ss = sharedstate
        self.api_key = self.ss.api_key
        self.api_secret = self.ss.api_secret
        self.symbol = self.ss.bybit_symbol

        self.private_ws = PrivateWs(self.api_key, self.api_secret)


    async def privatefeed(self):
        
        req, topics = self.private_ws.multi_stream_request(['Position', 'Execution'])

        print(f"{Misc.current_datetime()}: Subscribed to BYBIT {topics} feeds...")
        
        async for websocket in websockets.connect(WsStreamLinks.combined_private_stream()):
            
            try:
                await websocket.send(self.private_ws.auth())
                await websocket.send(req)

                while True:
                    
                    recv = orjson.loads(await websocket.recv())

                    if 'success' in recv:
                        pass
                    
                    else:
                        data = recv['data']

                        if recv['topic'] == topics[0]:
                            BybitPositionHandler(self.ss, data).process()

                        if recv['topic'] == topics[1]:
                            BybitExecutionHandler(self.ss, data).process()
                        

            except websockets.ConnectionClosed:
                continue

            except Exception as e:
                print(e)
                raise


    async def start_feed(self):
        await self.privatefeed()