
import json
import time
import hashlib
import hmac
import aiohttp
import asyncio

from frameworks.tools.logging.logger import Logger
from frameworks.exchange.binance.endpoints import BaseEndpoints
from frameworks.sharedstate.private import PrivateDataSharedState


class BinanceAPIErrors:


    def __init__(self) -> None:
        self.err_codes = {}
        self._fill_err_codes()

    
    def _fill_err_codes(self) -> None:
        """
        Tuple(bool, error msg)

        False: Do not attempt retry, break loop
        True: Raise exception and go through standard retry loop
        """

        # need to be replaced with binance errors!
        self.err_codes["10006"] = (False, "Rate limits exceeded!")
        self.err_codes["10016"] = (False, "Bybit server error...")
        self.err_codes["110001"] = (False, "Order doesnt exist anymore!")
        self.err_codes["110012"] = (False, "Insufficient available balance")



class BinancePrivatePostClient:


    def __init__(self, sharedstate: PrivateDataSharedState) -> None:
        self.pdss = sharedstate
        self.binance = self.pdss.binance["API"]
        self.base_endpoint = BaseEndpoints.MAINNET1
        self.recvWindow = "5000"

        self.logging = Logger()
    
    
    def _sign(self, payload: str) -> dict:
        self.timestamp = str(int(time.time()*1000))
        param_str = "".join([self.timestamp, self.binance["key"], self.recvWindow, payload])

        header = {
            "X-BAPI-TIMESTAMP": self.timestamp,
            "X-BAPI-API-KEY": self.binance["key"],
            "X-BAPI-RECV-WINDOW": self.recvWindow,
        }

        hash_signature = hmac.new(
            bytes(self.binance["secret"], "utf-8"), 
            param_str.encode("utf-8"), 
            hashlib.sha256
        )

        header["X-BAPI-SIGN"] = hash_signature.hexdigest()

        return header


    def _update_rate_limit(self, endpoint: str, response: json) -> None:
        remaining_limit = int(response["X-MBX-ORDER-COUNT-(intervalNum)(intervalLetter)"])
        time_till_reset = float(response["X-Bapi-Limit-Reset-Timestamp"])

        if endpoint not in self.binance:
            max_limit = int(response["X-MBX-ORDER-COUNT-(intervalNum)(intervalLetter)"])
            self.binance[endpoint] = [remaining_limit, max_limit, time_till_reset]

        else:
            self.binance[endpoint][0] = remaining_limit
            self.binance[endpoint][2] = time_till_reset


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
                    self.timestamp = str(int(time.time()*1000))
                    self.signed_header = self._sign(payload)

                else:
                    self.logging.critical(f"Exception: {e} | Endpoint: {endpoint}")
                    return None
