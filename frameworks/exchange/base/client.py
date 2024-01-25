import asyncio
import aiohttp
import orjson
from typing import Dict, Union
from frameworks.tools.logger import ms as time_ms


class Client:
    def __init__(self) -> None:
        self.session = aiohttp.ClientSession()
        self.recvWindow = "5000"
        self.timestamp = str(time_ms())
        self.MAX_RETRIES = 3

    def update_timestamp(self) -> str:
        self.timestamp = str(time_ms())

    def _sign_(self, payload: str) -> Dict:
        raise NotImplementedError("Must be implimented in inherited class!")

    def _error_handler_(self, response: Dict) -> Union[Dict, None]:
        raise NotImplementedError("Must be implimented in inherited class!")

    async def send(self, method: str, endpoint: str, header: str, payload: Union[Dict, str], pre_signed: bool=False) -> Union[Dict, Exception]:
        for attempt in range(1, self.MAX_RETRIES + 1):
            try:
                request = await self.session.request(
                    method=method,
                    endpoint=endpoint,
                    headers=header,
                    data=self._sign_(orjson.dumps(payload)) if not pre_signed else payload,
                )

                return orjson.loads(await request.text())

            except Exception as e:
                if attempt < self.MAX_RETRIES:
                    await asyncio.sleep(attempt)
                else:
                    raise e
