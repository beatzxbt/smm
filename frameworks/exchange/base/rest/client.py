import json
import time
import hashlib
import hmac
import aiohttp
import asyncio
from typing import Dict, List, Tuple, Optional, Union, _T
from frameworks.sharedstate import SharedState
from frameworks.exchange.base.rest.ratelimits import RateLimitManager


class Client:

    def __init__(self, ss: SharedState, rl: RateLimitManager) -> None:
        self.ss = ss
        self.rl = rl
        self.logging = self.ss.logging
        self.session = aiohttp.ClientSession()
        self.recvWindow = "5000"
        self.timestamp = str(int(time.time()*1000))

    @property
    def _api_(self) -> Dict:
        """Pointer to exchange's API info"""
        return self.ss.private[self.exchange]["API"]

    def _update_timestamp_(self) -> str:
        self.timestamp = str(int(time.time()*1000))

    def _sign_(self, payload: str) -> Dict:
        self._update_timestamp_()
        param_str = "".join([self.timestamp, self._api_["key"], self.recvWindow, payload])

        header = {
            "X-BAPI-TIMESTAMP": self.timestamp,
            "X-BAPI-API-KEY": self._api_["key"],
            "X-BAPI-RECV-WINDOW": self.recvWindow,
        }

        hash_signature = hmac.new(
            bytes(self._api_["secret"], "utf-8"), 
            param_str.encode("utf-8"), 
            hashlib.sha256
        )

        header["X-BAPI-SIGN"] = hash_signature.hexdigest()

        return header

    async def _post_(self, endpoint: str, payload: dict):
        payload_str = json.dumps(payload)
        self.signed_header = self._sign_(payload_str)
        full_endpoint = self.base_endpoint + endpoint

        max_retries = 3  
        
        for attempt in range(max_retries):
            try:
                req = await self.session.request("POST", full_endpoint, headers=self.signed_header, data=payload_str)
                response = json.loads(await req.text())
                self.rl.update(endpoint, response)

                if response["retMsg"] == "OK" or response["retMsg"] == "success":
                    latency = int(response["time"]) - int(self.timestamp)

                    if latency >= 1000:
                        self.logging.warning(f"High latency detected: {latency}ms | Endpoint: {endpoint}")

                    ret = {
                        "return" : response["result"],
                        "latency": latency
                    }

                    return ret

                # Error handling
                else:
                    code = response["retCode"]

                    if code in self.errors.err_codes.keys():
                        err_response, msg = self.errors.err_codes[code]
    
                        if err_response:
                            self.logging.error(f"{msg} | Endpoint: {endpoint}")
                            return None

                        # Retry the request
                        else:
                            raise Exception
                            
                    # Enter other error handling here
                    else:            
                        self.logging.error(f"{msg} | Endpoint: {endpoint}")
                        return None


            except Exception as e:
                # Resign the payload and retry the request after sleeping for 1s
                if attempt < max_retries - 1:  
                    await asyncio.sleep(attempt)  
                    self.signed_header = self._sign_(payload)

                else:
                    self.logging.critical(f"Exception: {e} | Endpoint: {endpoint}")
                    return None

        
