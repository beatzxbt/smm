import json
import time
import hashlib
import hmac
import asyncio

from src.bybit.order.endpoints import BaseEndpoints, OrderEndpoints



class Client:


    def __init__(self, api_key: str, api_secret: str) -> None:
        self.base_endpoint = BaseEndpoints.mainnet1()
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


    async def order(self, session, payload: dict):

        payload = json.dumps(payload)
        signed_header = self.sign(payload)
        endpoint = self.base_endpoint + OrderEndpoints.create_order()

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
                        "orderId" : response['result']['orderId'],
                        "latency": int(response['time']) - int(self.timestamp)
                    }

                    return ret

                # Error handling \
                else:
                    # If rate limits hit, close session \
                    if response['retMsg'] == "too many visit":

                        print('Rate limits hit, cooling off...')

                        await asyncio.sleep(1)

                        self.timestamp = str(int(time.time()*1000))
                        signed_header = self.sign(payload)
                        
                        continue
                
                    else:            
                        # Enter other error handling here \
                        print(response['retMsg'])


            except Exception as e:

                print(f'Error at {endpoint}: {e}')
                
                # Resign the payload and retry the request after sleeping for 1s \
                if attempt < max_retries - 1:  

                    await asyncio.sleep(1)  

                    self.timestamp = str(int(time.time()*1000))
                    signed_header = self.sign(payload)

                else:
                    raise  # Re-raise the last exception if all retries failed \


    async def batch_order(self, session, payload: dict):

        payload = json.dumps(payload)
        signed_header = self.sign(payload)
        endpoint = self.base_endpoint + OrderEndpoints.create_batch()

        max_retries = 3  
        
        for attempt in range(max_retries):

            try:
                # Submit request to the session \
                req = await session.request("POST", endpoint, headers=signed_header, data=payload)

                # Error handling & latency measurement \
                response = json.loads(await req.text())

                # If submission is successful, return orderId and latency \
                if response['retMsg'] == "OK" or response['retMsg'] == "success":

                    n = []

                    for order in response['result']['list']:
                        n.append(order['orderId'])

                    ret = {
                        "orderId" : n,
                        "latency": int(response['time']) - int(self.timestamp)
                    }

                    return ret

                # Error handling \
                else:
                    # If rate limits hit, close session \
                    if response['retMsg'] == "too many visit":

                        print('Rate limits hit, cooling off...')

                        await asyncio.sleep(1)

                        self.timestamp = str(int(time.time()*1000))
                        signed_header = self.sign(payload)
                        
                        continue
                
                    else:            
                        # Enter other error handling here \
                        print(response['retMsg'])


            except Exception as e:

                print(f'Error at {endpoint}: {e}')
                
                # Resign the payload and retry the request after sleeping for 1s \
                if attempt < max_retries - 1:  

                    await asyncio.sleep(1)  

                    self.timestamp = str(int(time.time()*1000))
                    signed_header = self.sign(payload)

                else:
                    raise  # Re-raise the last exception if all retries failed \
    
    
    async def amend(self, session, payload: dict):

        payload = json.dumps(payload)
        signed_header = self.sign(payload)
        endpoint = self.base_endpoint + OrderEndpoints.amend_order()

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
                        "orderId" : response['result']['orderId'],
                        "latency": int(response['time']) - int(self.timestamp)
                    }

                    return ret

                # Error handling \
                else:
                    # If rate limits hit, close session \
                    if response['retMsg'] == "too many visit":

                        print('Rate limits hit, cooling off...')

                        await asyncio.sleep(1)

                        self.timestamp = str(int(time.time()*1000))
                        signed_header = self.sign(payload)
                        
                        continue
                    
                    # If order doesnt exist anymore \
                    elif response['retCode'] == "110001":            
                        print(response['retMsg'])
                        break


            except Exception as e:

                print(f'Error at {endpoint}: {e}')
                
                # Resign the payload and retry the request after sleeping for 1s \
                if attempt < max_retries - 1:  

                    await asyncio.sleep(1)  

                    self.timestamp = str(int(time.time()*1000))
                    signed_header = self.sign(payload)

                else:
                    raise  # Re-raise the last exception if all retries failed \


    async def cancel(self, session, payload: dict):

        payload = json.dumps(payload)
        signed_header = self.sign(payload)
        endpoint = self.base_endpoint + OrderEndpoints.cancel_single()

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
                        "orderId" : response['result']['orderId'],
                        "latency": int(response['time']) - int(self.timestamp)
                    }

                    return ret

                # Error handling \
                else:
                    # If rate limits hit, close session \
                    if response['retMsg'] == "too many visit":

                        print('Rate limits hit, cooling off...')

                        await asyncio.sleep(1)

                        self.timestamp = str(int(time.time()*1000))
                        signed_header = self.sign(payload)
                        
                        continue
                
                    # If order doesnt exist anymore \
                    elif response['retCode'] == "110001":            
                        print(response['retMsg'])
                        break


            except Exception as e:

                print(f'Error at {endpoint}: {e}')
                
                # Resign the payload and retry the request after sleeping for 1s \
                if attempt < max_retries - 1:  

                    await asyncio.sleep(1)  

                    self.timestamp = str(int(time.time()*1000))
                    signed_header = self.sign(payload)

                else:
                    raise  # Re-raise the last exception if all retries failed \


    async def cancel_all(self, session, payload: dict):

        payload = json.dumps(payload)
        signed_header = self.sign(payload)
        endpoint = self.base_endpoint + OrderEndpoints.cancel_all()

        max_retries = 3  
        
        for attempt in range(max_retries):

            try:
                # Submit request to the session \
                req = await session.request("POST", endpoint, headers=signed_header, data=payload)

                # Error handling & latency measurement \
                response = json.loads(await req.text())

                # If submission is successful, return orderId and latency \
                if response['retMsg'] == "OK" or response['retMsg'] == "success":
                    
                    n = []

                    for order in response['result']['list']:
                        n.append(order['orderId'])

                    ret = {
                        "orderId" : n,
                        "latency": int(response['time']) - int(self.timestamp)
                    }

                    return ret

                # Error handling \
                else:
                    # If rate limits hit, close session \
                    if response['retMsg'] == "too many visit":
                        
                        print('Rate limits hit, cooling off...')

                        await asyncio.sleep(1)

                        self.timestamp = str(int(time.time()*1000))
                        signed_header = self.sign(payload)
                        
                        continue
                
                    # If order doesnt exist anymore \
                    elif response['retCode'] == "110001":            
                        print(response['retMsg'])
                        break


            except Exception as e:

                print(f'Error at {endpoint}: {e}')
                
                # Resign the payload and retry the request after sleeping for 1s \
                if attempt < max_retries - 1:  

                    await asyncio.sleep(1)  

                    self.timestamp = str(int(time.time()*1000))
                    signed_header = self.sign(payload)

                else:
                    raise  # Re-raise the last exception if all retries failed \

    