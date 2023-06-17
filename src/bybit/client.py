import json
import aiohttp
import time
import hashlib
import hmac
import pandas as pd


base = 'https://api.bybit.com'


class HTTP_PublicRequests:


    def __init__(self) -> None:
        self.recvWindow = str(5000)
        self.timestamp = str(int(time.time()*1000))
        self.baseheader = {}
        self.payload = {}
                

    async def klines(self, symbol: str, interval: str):

        url = base + f"/v5/market/kline?category=linear&symbol={symbol}&interval={interval}"

        async with aiohttp.ClientSession() as session:
            _req = await session.request(method='GET', url=url, headers=self.baseheader, data=self.payload)
            klines = json.loads(await _req.text())['result']['list']
            df = pd.DataFrame(klines, columns=['Time', 'Open', 'High', 'Low', 'Close', 'Volume', 'Turnover'])
            return df[::-1]
        


class HTTP_PrivateRequests:


    def __init__(self, api_key: str, api_secret: str, recvWindow: int) -> None:
        self.api_key = api_key
        self.api_secret = api_secret
        self.recvWindow = str(recvWindow)
        self.timestamp = str(int(time.time()*1000))
        
        self.baseheader = {
            'X-BAPI-TIMESTAMP': self.timestamp,
            'X-BAPI-API-KEY': self.api_key,
            'X-BAPI-RECV-WINDOW': self.recvWindow,
        }
             
    
    async def send(self, method: str, endPoint: str, payload: str):
        payload = json.dumps(payload)
        param_str= self.timestamp + self.api_key + self.recvWindow + str(payload)
        hash = hmac.new(bytes(self.api_secret, "utf-8"), param_str.encode("utf-8"), hashlib.sha256)
        self.baseheader['X-BAPI-SIGN'] = hash.hexdigest()

        async with aiohttp.ClientSession() as session:
            
            try: 
                if method == 'GET':
                    _req = await session.request("GET", base+endPoint, headers=self.baseheader, data=payload)

                elif method == 'POST':
                    _req = await session.request("POST", base+endPoint, headers=self.baseheader, data=payload)
     
                else:
                    print("Invalid request method!, select either 'GET' or 'POST'")


                recv = json.dumps(await _req.text())

                if recv['RetMsg'] == "Too many visits!":
                    print('Rate limits hit, cooling off...')
                    return 'RATELIMITS'
                
                else:            
                    # Enter error handling here \
                    print(recv['RetMsg'])
                    
            except Exception as e:
                print(e)

            finally:
                _close = await session.close()