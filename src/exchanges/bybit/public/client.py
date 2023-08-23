import json
import time
import aiohttp
import asyncio

from src.bybit.public.endpoints import BaseEndpoints, MarketEndpoints



class Client:


    def __init__(self, category: str) -> None:
        self.base_endpoint = BaseEndpoints.mainnet1()
        self.recvWindow = str(5000)
        self.timestamp = str(int(time.time()*1000))
        self.baseheader = {}
        self.payload = {}
        self.session = aiohttp.ClientSession()

        if category == 'Futures':
            self.category = 'linear'

        if category == 'Spot':
            self.category = 'spot'
             

    async def klines(self, symbol: str, interval: int):

        endpoint = self.base_endpoint + MarketEndpoints(self.category, symbol).klines(interval)

        max_retries = 3  
        
        async with self.session:

            for attempt in range(max_retries):

                try:
                    # Submit request to the session \
                    req = await self.session.request(
                        method="GET", 
                        url=endpoint, 
                        headers=self.baseheader, 
                        data=self.payload
                    )

                    # Error handling & latency measurement \
                    response = json.loads(await req.text())

                    return response

                except Exception as e:
                    print(e)
                    
                    # Resign the payload and retry the request after sleeping for 1s \
                    if attempt < max_retries - 1:  
                        await asyncio.sleep(1)  

                    else:
                        raise  # Re-raise the last exception if all retries failed \