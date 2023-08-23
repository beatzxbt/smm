import json
import time
import hashlib
import hmac
import asyncio

from src.exchanges.bybit.order.endpoints import BaseEndpoints


class Client:


    def __init__(self, api_key: str, api_secret: str) -> None:
        self.base_endpoint = BaseEndpoints.MAINNET1
        self.api_key = api_key
        self.api_secret = api_secret
        self.recvWindow = str(5000)
        self.timestamp = str(int(time.time()*1000))
             
    
    def sign(self, payload: json) -> json:
        
        param_str = self.timestamp + self.api_key + self.recvWindow + str(payload)

        header = {
            'X-BAPI-TIMESTAMP': self.timestamp,
            'X-BAPI-API-KEY': self.api_key,
            'X-BAPI-RECV-WINDOW': self.recvWindow,
        }
        
        hash = hmac.new(bytes(self.api_secret, "utf-8"), param_str.encode("utf-8"), hashlib.sha256)
        header['X-BAPI-SIGN'] = hash.hexdigest()

        return header


    async def submit(self, session, endpoint: str, payload: dict):

        payload = json.dumps(payload)
        signed_header = self.sign(payload)
        endpoint = self.base_endpoint + endpoint

        max_retries = 3  
        
        for attempt in range(max_retries):

            try:
                # Submit request to the session \
                req = await session.request("POST", endpoint, headers=signed_header, data=payload)

                # Error handling & latency measurement \
                response = json.loads(await req.text())

                # If submission is successful, return orderId and latency \
                if response['retMsg'] == "OK" or response['retMsg'] == "success":

                    ret = {
                        "return" : response['result'],
                        "latency": int(response['time']) - int(self.timestamp)
                    }

                    return ret

                # Error handling \
                else:
                    code = response['retCode']
                    msg = response['retMsg']

                    # If rate limits hit, close session \
                    if msg == "too many visit":
                        print('Rate limits hit, cooling off...')
                        break

                    # If order doesnt exist anymore \
                    elif code == "110001":       
                        print(f"Msg: {msg}, Payload: {payload}")
                        break
                
                    else:            
                        # Enter other error handling here \
                        print(f"Msg: {msg}, Payload: {payload}")
                        break


            except Exception as e:

                print(f'Error at {endpoint}: {e}')
                
                # Resign the payload and retry the request after sleeping for 1s \
                if attempt < max_retries - 1:  

                    await asyncio.sleep(attempt)  

                    self.timestamp = str(int(time.time()*1000))
                    signed_header = self.sign(payload)

                else:
                    raise e # Re-raise the last exception if all retries failed \
