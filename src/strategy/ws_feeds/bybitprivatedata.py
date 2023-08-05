import websockets
import orjson
import asyncio

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


    async def authenticate_feed(self, websocket):

        # Send first auth attempt and wait for response \
        await websocket.send(self.private_ws.auth())
        auth_recv = orjson.loads(await websocket.recv())
        
        # If successful, continue... \
        if auth_recv['success'] is True:
            return 

        # If it failed, run a retry loop 
        for i in range(2):
            
            # Exponential backoff for retries \
            await asyncio.sleep(1 + i**2)

            try:
                # Reinitialize the class to reset the timer, then send \
                self.private_ws = PrivateWs(self.api_key, self.api_secret)
                await websocket.send(self.private_ws.auth())
                auth_recv = orjson.loads(await websocket.recv())    

                # If successful, continue... \
                if auth_recv['success'] is True:
                    return 

                # Trigger exception to re-run loop \
                else: 
                    raise Exception

            # Catch exception and move onto next iteration \
            except Exception as e:
                continue
        
        # Raise final exception to halt feed \
        print('Authentication for private feed failed...')
        raise Exception


    async def private_feed(self):
        
        req, topics = self.private_ws.multi_stream_request(['Position', 'Execution'])

        print(f"{Misc.current_datetime()}: Subscribed to BYBIT {topics} feeds...")
        
        async for websocket in websockets.connect(WsStreamLinks.combined_private_stream()):
            
            try:
                await self.authenticate_feed(websocket)
                await websocket.send(req)

                while True:
                    
                    recv = orjson.loads(await websocket.recv())

                    # Skip the streams subscription message \
                    if 'success' in recv:
                        continue

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
        await self.private_feed()