import websockets
import orjson
import asyncio

from src.utils.misc import Misc

from src.exchanges.bybit.websockets.endpoints import WsStreamLinks
from src.exchanges.bybit.websockets.private import PrivateWs
from src.exchanges.bybit.websockets.handlers.execution import BybitExecutionHandler
from src.exchanges.bybit.websockets.handlers.position import BybitPositionHandler
from src.exchanges.bybit.websockets.handlers.order import BybitOrderHandler

from src.exchanges.bybit.get.private import BybitPrivateClient


from src.sharedstate import SharedState


class BybitPrivateData:


    def __init__(self, sharedstate: SharedState) -> None:

        self.ss = sharedstate
        self.api_key = self.ss.api_key
        self.api_secret = self.ss.api_secret
        self.symbol = self.ss.bybit_symbol

        self.private_ws = PrivateWs(self.api_key, self.api_secret)


    async def open_orders_sync(self):
        """
        Will sync the open orders dict every 0.5s
        """

        while True:

            recv = await BybitPrivateClient(self.ss).open_orders()
            data = recv['result']['list']

            curr_orders = {}

            for open_order in data: 

                id = open_order['orderId']
                price = float(open_order['price'])
                qty = float(open_order['qty'])
                side = open_order['side']
                
                curr_orders[id] = {'price': price, 'qty': qty, 'side': side}

            self.ss.current_orders = curr_orders

            # Sleep for 0.5s \
            await asyncio.sleep(0.5)


    async def current_position_sync(self):
        """
        Will sync the open orders dict every 0.5s
        """

        while True:

            recv = await BybitPrivateClient(self.ss).current_position()
            data = recv['result']['list']

            BybitPositionHandler(self.ss, data).process()

            # Sleep for 0.5s \
            await asyncio.sleep(0.5)


    async def privatefeed(self):
        
        req, topics = self.private_ws.multi_stream_request(['Position', 'Execution', 'Order'])

        print(f"{Misc.current_datetime()}: Subscribed to BYBIT {topics} feeds...")
        
        async for websocket in websockets.connect(WsStreamLinks.COMBINED_PRIVATE_STREAM):
            
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
                        
                        if recv['topic'] == topics[2]:
                            BybitOrderHandler(self.ss, data).process()

            except websockets.ConnectionClosed:
                continue

            except Exception as e:
                print(e)
                raise


    async def start_feed(self):

        tasks = []

        tasks.append(asyncio.create_task(self.open_orders_sync()))
        tasks.append(asyncio.create_task(self.current_position_sync()))
        tasks.append(asyncio.create_task(self.privatefeed()))

        await asyncio.gather(*tasks)