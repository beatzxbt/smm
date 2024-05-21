import asyncio
from typing import Dict, Union, Optional, Any

from frameworks.exchange.base.exchange import Exchange
from frameworks.exchange.binance.endpoints import BinanceEndpoints
from frameworks.exchange.binance.formats import BinanceFormats
from frameworks.exchange.binance.client import BinanceClient


class Binance(Exchange):
    def __init__(self, api_key: str, api_secret: str) -> None:
        self.api_key = api_key
        self.api_secret = api_secret
        self.client = BinanceClient(self.api_key, self.api_secret)
        self.formats = BinanceFormats()
        self.endpoints = BinanceEndpoints
        self.base_endpoint = self.endpoints["main1"]
        super().__init__(self.client)

    async def create_order(
        self,
        symbol,
        side,
        orderType,
        size,
        price,
    ):
        endpoint, method = self.endpoints["createOrder"]
        payload = self.formats.create_order(symbol, side, orderType, size, price)
        return await self.client.request(
            url=self.base_endpoint+endpoint,
            method=method,
            payload=payload, 
            signed=False
        )

    async def amend_order(
        self, 
        symbol: str,
        orderId: str,
        side: int,
        size: float,
        price: float,
    ):
        endpoint, method = self.endpoints["amendOrder"]
        payload = self.formats.amend_order(symbol, orderId, side, price, size)
        return await self.client.request(
            url=self.base_endpoint + endpoint,
            method=method,
            payload=payload, 
            signed=False
        )

    async def cancel_order(self, symbol: str, orderId: str):
        endpoint, method = self.endpoints["cancelOrder"]
        payload = self.formats.cancel_order(symbol, orderId)
        return await self.client.request(
            url=self.base_endpoint + endpoint,
            method=method,
            payload=payload, 
            signed=False
        )

    async def cancel_all_orders(self, symbol: str):
        endpoint, method = self.endpoints["cancelAllOrders"]
        payload = self.formats.cancel_all_orders(symbol)
        return await self.client.request(
            url=self.base_endpoint + endpoint,
            method=method,
            payload=payload, 
            signed=False
        )

    async def get_orderbook(self, symbol: str) -> Dict:
        endpoint, method = self.endpoints["orderbook"]
        params = self.formats.get_orderbook(symbol, limit=1000)
        return await self.client.request(
            url=self.base_endpoint + endpoint,
            method=method,
            params=params
        )

    async def get_trades(self, symbol: str) -> Dict:
        endpoint, method = self.endpoints["trades"]
        params = self.formats.get_trades(symbol, limit=1000)
        return await self.client.request(
            url=self.base_endpoint + endpoint,
            method=method,
            params=params
        )

    async def get_ohlcv(self, symbol: str, interval: str = "1m") -> Dict:
        endpoint, method = self.endpoints["ohlcv"]
        params = self.formats.get_ohlcv(symbol, interval, limit=1000)
        return await self.client.request(
            url=self.base_endpoint + endpoint,
            method=method,
            params=params
        )

    async def get_ticker(self, symbol: str) -> Dict:
        endpoint, method = self.endpoints["markPrice"]
        params = self.formats.get_ticker(symbol)
        return await self.client.request(
            url=self.base_endpoint + endpoint,
            method=method,
            params=params
        )

    async def get_open_orders(self, symbol: str) -> Dict:
        endpoint, method = self.endpoints["allOpenOrders"]
        params = self.formats.get_open_orders(symbol)
        return await self.client.request(
            url=self.base_endpoint + endpoint,
            method=method, 
            headers={},
            params=params,
            payload=payload, 
            signed=False
        )

    async def get_position(self, symbol: str) -> Dict:
        endpoint, method = self.endpoints["positionInfo"]
        payload = self.formats.get_position(symbol)
        return await self.client.request(
            url=self.base_endpoint + endpoint,
            method=method,
            payload=payload, 
            signed=False
        )

    async def exchange_info(self):
        endpoint, method = self.endpoints["exchangeInfo"]
        payload = self.formats.get_exchange_info()
        return await self.client.request(
            url=self.base_endpoint + endpoint,
            method=method,
            payload=payload 
        )

    async def get_listen_key(self):
        endpoint, method = self.endpoints["listenKey"]
        payload = self.formats.get_listen_key()
        return await self.client.request(
            url=self.base_endpoint + endpoint,
            method=method,
            payload=payload, 
            signed=False
        )

    async def ping_listen_key(self):
        endpoint, method = self.endpoints["pingListenKey"]
        payload = self.formats.ping_listen_key()
        return await self.client.request(
            url=self.base_endpoint + endpoint,
            method=method,
            payload=payload, 
            signed=False
        )

    async def warmup(self) -> None:
        try:
            for symbol in (await self.exchange_info())["symbols"]:
                if self.symbol != symbol["symbol"]:
                    continue

                for filter in symbol["filters"]:
                    if filter["filterType"] == "PRICE_FILTER":
                        self.data["tick_size"] = float(filter["tickSize"])
                    elif filter["filterType"] == "LOT_SIZE":
                        self.data["lot_size"] = float(filter["stepSize"])

        except Exception as e:
            self.logging.error(f"Binance exchange warmup: {e}")

        finally:
            self.logging.success(f"Binance warmup sequence complete.")

    async def shutdown(self) -> None:
        try:
            tasks = []

            for _ in range(3):
                tasks.append(asyncio.create_task(self.cancel_all_orders(self.symbol))) 
            
            for _ in range(1):
                tasks.append(asyncio.create_task(self.create_order(
                    symbol=self.symbol,
                    side=0.0 if self.data["position"]["size"] < 0.0 else 1.0,
                    orderType=1.0,
                    size=self.data["position"]["size"],
                    price=0.0   # NOTE: Ignored for taker orders
                ))) 
            
            await asyncio.gather(*tasks)

        except Exception as e:
            await self.logging.error(f"Binance shutdown: {e}")

        finally:
            await self.logging.info(f"Binance shutdown sequence complete.")
