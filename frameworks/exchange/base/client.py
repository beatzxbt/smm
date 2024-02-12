import ssl
import asyncio
import aiohttp
import orjson
from typing import Dict, Union, Optional
from frameworks.tools.logger import ms as time_ms


class Client:
    _ssl_context = ssl.create_default_context()
    _ssl_context.check_hostname = False
    _ssl_context.verify_mode = ssl.CERT_REQUIRED # NOTE: ssl.CERT_NONE (faster) if you're feeling bold 
    connector = aiohttp.TCPConnector(ssl=_ssl_context, limit=100, limit_per_host=50)

    def __init__(self) -> None:
        self.session = aiohttp.ClientSession(
            connector=self.connector, 
            json_serialize=orjson.dumps, 
            auto_decompress=True
        )
        self.recvWindow = "5000"
        self.timestamp = str(time_ms())
        self.MAX_RETRIES = 3

    def update_timestamp(self) -> str:
        self.timestamp = str(time_ms())

    def _sign_(self, payload: str) -> Dict:
        raise NotImplementedError("Must be implimented in inherited class!")

    def _error_handler_(self, recv: Dict) -> Union[Dict, None]:
        raise NotImplementedError("Must be implimented in inherited class!")

    def _latency_handler_(self, recv: Dict) -> Union[Dict, None]:
        raise NotImplementedError("Must be implimented in inherited class!")

    def _ratelimit_handler_(self, 
        method: Optional[str]=None, 
        endpoint: Optional[str]=None, 
        recv: Optional[Dict]=None
    ) -> None:
        raise NotImplementedError("Must be implimented in inherited class!")

    async def send(
        self,
        method: str,
        endpoint: str,
        header: str,
        payload: Union[Dict, str],
        pre_signed: bool=False,
    ) -> Union[Dict, Exception]:
        for attempt in range(1, self.MAX_RETRIES + 1):
            json = self._sign_(orjson.dumps(payload)) if not pre_signed else payload
            try:
                request = await self.session.request(
                    method=method,
                    endpoint=endpoint,
                    headers=header,
                    json=json,
                )
                text = orjson.loads(request.text())
                self._error_handler_(request)
                self._latency_handler_(text)
                self._ratelimit_handler_(endpoint, text)
                return request, text
                
            except Exception as e:
                if attempt < self.MAX_RETRIES:
                    await asyncio.sleep(attempt)
                else:
                    raise e
