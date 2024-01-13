import asyncio
import aiohttp
import orjson
from time import time_ns
from typing import Dict, Union
from frameworks.exchange.base.rest.ratelimits import RateLimitManager


class Client:

    def __init__(self, rl: RateLimitManager) -> None:
        self.rl = rl
        self.logging = self.ss.logging
        self.session = aiohttp.ClientSession()
        self.recvWindow = "5000"
        self.timestamp = str(time_ns()//1_000_000)

        self.MAX_RETRIES = 3

    def _update_timestamp_(self) -> str:
        self.timestamp = str(time_ns()//1_000_000)

    def _sign_(self, payload: str) -> Dict:
        raise NotImplementedError("Must be implimented in parent class")

    def _error_handler_(self, response: Dict) -> Union[dict, None]:
        raise NotImplementedError("Must be implimented in parent class")

    async def post(self, endpoint: str, header: str, payload: Dict):
        payload_to_str = orjson.dumps(payload)
        
        for attempt in range(1, self.MAX_RETRIES+1):
            try:
                request = await self.session.request(
                    method="POST", 
                    endpoint=endpoint, 
                    headers=header, 
                    data=payload_to_str
                )

                response = orjson.loads(await request.text())
                self.rl.update(endpoint, response)

            except Exception as e:
                # Resign the payload and retry the request after sleeping for 1s
                if attempt < self.MAX_RETRIES:  
                    await asyncio.sleep(attempt)  
                    self.signed_header = self._sign_(payload)

                else:
                    raise e

        
