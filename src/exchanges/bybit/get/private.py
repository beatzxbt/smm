
import json
import time
import hashlib
import hmac
import aiohttp
import asyncio

from src.utils.misc import curr_dt
from src.exchanges.bybit.endpoints import BaseEndpoints, PrivateGetLinks

from src.sharedstate import SharedState


class BybitPrivateGetClient:


    def __init__(self, sharedstate: SharedState) -> None:
        self.ss = sharedstate
        self.api_key = self.ss.api_key
        self.api_secret = self.ss.api_secret
        self.base_endpoint = BaseEndpoints.MAINNET1
        self.recvWindow = "5000"

        # Compute headers only once
        self.static_headers = {
            "X-BAPI-API-KEY": self.api_key, 
            "X-BAPI-SIGN-TYPE": "2",
            "X-BAPI-RECV-WINDOW": self.recvWindow
        }


    def _sign(self, payload) -> dict:
        self.timestamp = str(int(time.time()*1000))
        param_str = "".join([self.timestamp, self.api_key, self.recvWindow, payload])

        hash_signature = hmac.new(
            bytes(self.api_secret, "utf-8"), 
            param_str.encode("utf-8"), 
            hashlib.sha256
        )

        headers = self.static_headers.copy()
        headers["X-BAPI-TIMESTAMP"] = self.timestamp
        headers["X-BAPI-SIGN"] = hash_signature.hexdigest()

        return headers


    async def submit(self, session: aiohttp.ClientSession, endpoint: str, payload: str):
        self.signed_header = self._sign(payload)
        full_endpoint = self.base_endpoint + endpoint

        max_retries = 3  
        
        for attempt in range(max_retries):

            try:
                # Submit request to the session
                req = await session.request("GET", url=full_endpoint, headers=self.signed_header)
                response = json.loads(await req.text())

                # If submission is successful, return orderId and latency
                if response["retMsg"] == "OK" or response["retMsg"] == "success":
                    return response

                # Error handling
                else:
                    msg = response["retMsg"]

                    # If rate limits hit, close session
                    if msg == "too many visit":
                        print(f"{curr_dt()}: Rate limits exceeded!")
                        break
                    
                    # Enter other error handling here
                    else:            
                        print(f"{curr_dt()}: {msg} | Endpoint: {endpoint}")
                        break


            except Exception as e:
                
                # Resign the payload and retry the request after sleeping
                if attempt < max_retries - 1:  

                    await asyncio.sleep(attempt)  

                    self.timestamp = str(int(time.time()*1000))
                    self.signed_header = self._sign(payload)

                # Re-raise the last exception if all retries failed
                else:
                    raise e 



class BybitPrivateGet:


    def __init__(self, sharedstate: SharedState) -> None:
        self.ss = sharedstate
        self.symbol = self.ss.bybit_symbol
        self.endpoints = PrivateGetLinks
        self.client = BybitPrivateGetClient(self.ss)
        self.session = aiohttp.ClientSession()


    async def open_orders(self):
        payload = f"category=linear&symbol={self.symbol}&limit=50"
        endpoint = f"{self.endpoints.OPEN_ORDERS}?{payload}"

        return await self.client.submit(self.session, endpoint, payload)

    
    async def current_position(self):
        payload = f"category=linear&symbol={self.symbol}"
        endpoint = f"{self.endpoints.CURRENT_POSITION}?{payload}"

        return await self.client.submit(self.session, endpoint, payload)


    async def _close(self):
        return await self.session.close()