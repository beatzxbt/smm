import json
import time
import hashlib
import hmac
import aiohttp

from src.sharedstate import SharedState
from src.exchanges.bybit.order.endpoints import BaseEndpoints


OPEN_ORDERS = "/v5/order/realtime"
CURRENT_POSITION = "/v5/position/list"


class BybitPrivateClient:


    def __init__(self, sharedstate: SharedState) -> None:
        self.ss = sharedstate
        self.base_endpoint = BaseEndpoints.MAINNET1
        self.api_key = self.ss.api_key
        self.api_secret = self.ss.api_secret
        self.recvWindow = str(5000)
        self.timestamp = str(int(time.time()*1000))

        self.session = aiohttp.ClientSession()
             
    
    def sign(self, params: str) -> json:
        
        headers = {
            'X-BAPI-API-KEY': self.api_key,
            'X-BAPI-SIGN-TYPE': '2',
            'X-BAPI-TIMESTAMP': self.timestamp,
            'X-BAPI-RECV-WINDOW': self.recvWindow
        }

        param_str= str(self.timestamp) + self.api_key + self.recvWindow + params
        hash = hmac.new(bytes(self.api_secret, "utf-8"), param_str.encode("utf-8"),hashlib.sha256)
        headers['X-BAPI-SIGN'] = hash.hexdigest()

        return headers


    async def open_orders(self):

        symbol = self.ss.bybit_symbol

        params = f"category=linear&symbol={symbol}&limit=50"
        endpoint = self.base_endpoint + OPEN_ORDERS + "?" + params

        async with self.session:

            try:
                # Submit request to the session \
                req = await self.session.request(
                    method="GET", 
                    url=endpoint, 
                    headers=self.sign(params)
                )

                response = json.loads(await req.text())

                return response

            except Exception as e:
                print(e)
                pass


    async def current_position(self):

        symbol = self.ss.bybit_symbol

        params = f"category=linear&symbol={symbol}"
        endpoint = self.base_endpoint + CURRENT_POSITION + "?" + params

        async with self.session:

            try:
                # Submit request to the session \
                req = await self.session.request(
                    method="GET", 
                    url=endpoint, 
                    headers=self.sign(params)
                )

                response = json.loads(await req.text())

                return response

            except Exception as e:
                print(e)
                pass
