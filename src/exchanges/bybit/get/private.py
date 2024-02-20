import hashlib
import hmac
import aiohttp
import orjson
import asyncio
from typing import Dict, Union
from src.utils.misc import time_ms, datetime_now as dt_now
from src.exchanges.bybit.endpoints import BaseEndpoints, PrivateGetLinks
from src.sharedstate import SharedState


class BybitPrivateGetClient:
    max_retries = 3
    recv_window = "5000"
    _success_ = ["OK", "success", "SUCCESS", ""]
    _retry_ = [100016] # NOTE: Add more
    _skip_ = [10006, 110001, 110012] # NOTE: Add more

    def __init__(self, ss: SharedState) -> None:
        self.ss = ss
        self.key, self.secret = self.ss.api_key, self.ss.api_secret
        self.base_endpoint = BaseEndpoints.MAINNET1
        self.timestamp = time_ms()

        self.static_headers = {
            "X-BAPI-TIMESTAMP": self.timestamp,
            "X-BAPI-RECV-WINDOW": self.recv_window,
            "X-BAPI-API-KEY": self.key, 
            "X-BAPI-SIGN-TYPE": "2",
            "X-BAPI-SIGN": ""
        }

        self.static_partial_str = "".join([self.key, self.recv_window])

    def _update_timestamp_(self) -> None:
        self.timestamp = str(time_ms())

    def _sign_(self, payload: str) -> Dict:
        self._update_timestamp_()
        param_str = "".join([self.timestamp, self.static_partial_str, payload])
        hash_signature = hmac.new(
            bytes(self.secret, "utf-8"), 
            param_str.encode("utf-8"), 
            hashlib.sha256
        ).hexdigest()
        self.static_headers["X-BAPI-TIMESTAMP"] = self.timestamp
        self.static_headers["X-BAPI-SIGN"] = hash_signature
        return self.static_headers

    async def submit(self, session: aiohttp.ClientSession, endpoint: str, payload: str):
        signed_header = self._sign_(payload)
        full_endpoint = self.base_endpoint + endpoint
        max_retries = self.max_retries
    
        for attempt in range(max_retries):
            try:
                req = await session.request("GET", url=full_endpoint, headers=signed_header)
                response = orjson.loads(await req.text())
                code, msg = response["retCode"], response["retMsg"]

                if msg in self._success_:
                    return response
                
                else:
                    if code in self._retry_: 
                        raise Exception(f"Error: {code}/{msg} | Endpoint: {endpoint}")
                
                    else:            
                        print(f"{dt_now()}: Error: {code}/{msg} | Endpoint: {endpoint}")
                        break

            except Exception as e:
                if attempt < max_retries - 1:  
                    await asyncio.sleep(attempt)  
                    signed_header = self._sign_(payload)
                else:
                    raise e 


class BybitPrivateGet:
    def __init__(self, ss: SharedState) -> None:
        self.ss = ss
        self.symbol: str = self.ss.bybit_symbol
        self.endpoints = PrivateGetLinks
        self.client = BybitPrivateGetClient(self.ss)
        self.session = aiohttp.ClientSession()

    async def open_orders(self) -> Union[Dict, None]:
        payload = f"category=linear&symbol={self.symbol}&limit=50"
        endpoint = f"{self.endpoints.OPEN_ORDERS}?{payload}"
        return await self.client.submit(self.session, endpoint, payload)

    async def current_position(self) -> Union[Dict, None]:
        payload = f"category=linear&symbol={self.symbol}"
        endpoint = f"{self.endpoints.CURRENT_POSITION}?{payload}"
        return await self.client.submit(self.session, endpoint, payload)
 
    async def _close_(self) -> None:
        return await self.session.close()