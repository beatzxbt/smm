
import json
import time
import hashlib
import hmac
import aiohttp
import asyncio

from src.exchanges.bybit.endpoints import BaseEndpoints
from src.utils.misc import curr_dt


class BybitPrivatePostClient:


    def __init__(self, api_key: str, api_secret: str) -> None:
        self.base_endpoint = BaseEndpoints.MAINNET1
        self.api_key = api_key
        self.api_secret = api_secret
        self.recvWindow = "5000"
    
    
    def _sign(self, payload) -> dict:
        self.timestamp = str(int(time.time()*1000))
        param_str = "".join([self.timestamp, self.api_key, self.recvWindow, str(payload)])

        header = {
            "X-BAPI-TIMESTAMP": self.timestamp,
            "X-BAPI-API-KEY": self.api_key,
            "X-BAPI-RECV-WINDOW": self.recvWindow,
        }

        hash_signature = hmac.new(
            bytes(self.api_secret, "utf-8"), 
            param_str.encode("utf-8"), 
            hashlib.sha256
        )

        header["X-BAPI-SIGN"] = hash_signature.hexdigest()

        return header


    async def submit(self, session: aiohttp.ClientSession, endpoint: str, payload: dict):
        payload_str = json.dumps(payload)
        self.signed_header = self._sign(payload_str)
        full_endpoint = self.base_endpoint + endpoint

        max_retries = 3  
        
        for attempt in range(max_retries):

            try:
                # Submit request to the session
                req = await session.request("POST", full_endpoint, headers=self.signed_header, data=payload_str)
                response = json.loads(await req.text())

                # If submission is successful, return orderId and latency
                if response["retMsg"] == "OK" or response["retMsg"] == "success":

                    ret = {
                        "return" : response["result"],
                        "latency": int(response["time"]) - int(self.timestamp)
                    }

                    return ret

                # Error handling
                else:
                    code = response["retCode"]
                    msg = response["retMsg"]

                    # If rate limits hit, close session
                    if msg == "too many visit":
                        print(f"{curr_dt()}: Rate limits exceeded!")
                        break

                    # If order doesnt exist anymore
                    elif code == "110001":       
                        print(f"{curr_dt()}: {msg} | Endpoint: {endpoint}")
                        break
                    
                    # Enter other error handling here
                    else:            
                        print(f"{curr_dt()}: {msg} | Endpoint: {endpoint}")
                        break


            except Exception as e:
                
                # Resign the payload and retry the request after sleeping for 1s
                if attempt < max_retries - 1:  

                    await asyncio.sleep(attempt)  

                    self.timestamp = str(int(time.time()*1000))
                    self.signed_header = self._sign(payload)

                # Re-raise the last exception if all retries failed
                else:
                    raise e 
