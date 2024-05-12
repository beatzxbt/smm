import asyncio
import aiohttp
import orjson
from typing import Dict, Union
from frameworks.tools.logging import time_ms
from abc import ABC, abstractmethod

class Client(ABC):
    max_retries = 3

    def __init__(self, key: str, secret: str) -> None:
        self.key, self.secret = key, secret
        self.session = aiohttp.ClientSession()
        self.timestamp = str(time_ms())

    def update_timestamp(self) -> None:
        self.timestamp = str(time_ms())
    
    @abstractmethod
    def sign_payload(self, payload: Union[str, Dict]) -> Dict:
        pass
    
    @abstractmethod
    def error_handler(self, recv: Dict) -> Union[Dict, None]:
        pass
    
    async def send(
        self,
        method: str,
        endpoint: str,
        header: str,
        payload: Dict,
        to_sign: bool=False,
    ) -> Union[Dict, Exception]:
        for attempt in range(1, self.max_retries+1):
            json = self.sign_payload(payload) if not to_sign else payload
            try:
                request = await self.session.request(
                    method=method,
                    url=endpoint,
                    headers=header,
                    json=json,
                )
                text = orjson.loads(request.text())
                self.error_handler(request)
                return request, text
                
            except Exception as e:
                if attempt < self.max_retries:
                    await asyncio.sleep(attempt)
                else:
                    raise e