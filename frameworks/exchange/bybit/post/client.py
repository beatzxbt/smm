
import json
import time
import hashlib
import hmac
import aiohttp
import asyncio

from frameworks.exchange.bybit.endpoints import BaseEndpoints
from frameworks.tools.misc import current_datetime as now
from frameworks.sharedstate.private import PrivateDataSharedState


class BybitAPIErrors:


    def __init__(self) -> None:
        self.err_codes = {}
        self._fill_err_codes()

    
    def _fill_err_codes(self) -> None:
        """
        Tuple(bool, error msg)

        False: Do not attempt retry, break loop
        True: Raise exception and go through standard retry loop
        """

        self.err_codes["10006"] = (False, "Rate limits exceeded!")
        self.err_codes["10016"] = (False, "Bybit server error...")
        self.err_codes["110001"] = (False, "Order doesnt exist anymore!")
        self.err_codes["110012"] = (False, "Insufficient available balance")



class BybitPrivatePostClient:


    def __init__(self, sharedstate: PrivateDataSharedState) -> None:
        self.pdss = sharedstate
        self.bybit = self.pdss.bybit["API"]
        self.base_endpoint = BaseEndpoints.MAINNET1
        self.recvWindow = "5000"
    
    
    def _sign(self, payload: str) -> dict:
        self.timestamp = str(int(time.time()*1000))
        param_str = "".join([self.timestamp, self.bybit["key"], self.recvWindow, payload])

        header = {
            "X-BAPI-TIMESTAMP": self.timestamp,
            "X-BAPI-API-KEY": self.bybit["key"],
            "X-BAPI-RECV-WINDOW": self.recvWindow,
        }

        hash_signature = hmac.new(
            bytes(self.bybit["secret"], "utf-8"), 
            param_str.encode("utf-8"), 
            hashlib.sha256
        )

        header["X-BAPI-SIGN"] = hash_signature.hexdigest()

        return header


    def _update_rate_limit(self, endpoint: str, response: json) -> None:
        remaining_limit = int(response["X-Bapi-Limit-Status"])
        time_till_reset = float(response["X-Bapi-Limit-Reset-Timestamp"])

        if endpoint not in self.bybit:
            max_limit = int(response["X-Bapi-Limit"])
            self.bybit[endpoint] = [remaining_limit, max_limit, time_till_reset]

        else:
            self.bybit[endpoint][0] = remaining_limit
            self.bybit[endpoint][2] = time_till_reset


    async def submit(self, session: aiohttp.ClientSession, endpoint: str, payload: dict):
        payload_str = json.dumps(payload)
        self.signed_header = self._sign(payload_str)
        full_endpoint = self.base_endpoint + endpoint

        max_retries = 3  
        
        for attempt in range(max_retries):

            try:
                req = await session.request("POST", full_endpoint, headers=self.signed_header, data=payload_str)
                response = json.loads(await req.text())
                self._update_rate_limit(endpoint, response)

                if response["retMsg"] == "OK" or response["retMsg"] == "success":
                    ret = {
                        "return" : response["result"],
                        "latency": int(response["time"]) - int(self.timestamp)
                    }

                    return ret

                # Error handling
                else:
                    code = response["retCode"]

                    if code in self.errors.err_codes.keys():
                        err_response, msg = self.errors.err_codes[code]
    
                        if err_response:
                            print(f"{now()}: {msg} | Endpoint: {endpoint}, Payload: {payload}")
                            return None

                        else:
                            raise Exception
                            
                    # Enter other error handling here
                    else:            
                        print(f"{now()}: {response['retMsg']} | Endpoint: {endpoint}, Payload: {payload}")
                        return None


            except Exception:
                # Resign the payload and retry the request after sleeping for 1s
                if attempt < max_retries - 1:  
                    await asyncio.sleep(attempt)  
                    self.timestamp = str(int(time.time()*1000))
                    self.signed_header = self._sign(payload)

                else:
                    print(f"{now()}: {msg} | Endpoint: {endpoint}, Payload: {payload}")
                    return None
