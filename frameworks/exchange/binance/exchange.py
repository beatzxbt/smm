from typing import Dict, Optional

from frameworks.exchange.base.exchange import Exchange
from frameworks.exchange.binance.endpoints import BinanceEndpoints
from frameworks.exchange.binance.formats import BinanceFormats
from frameworks.exchange.binance.client import BinanceClient
from frameworks.exchange.binance.orderid import BinanceOrderIdGenerator


class Binance(Exchange):
    def __init__(self, api_key: str, api_secret: str) -> None:
        self.api_key = api_key
        self.api_secret = api_secret
        
        super().__init__(
            client=BinanceClient(self.api_key, self.api_secret),
            formats=BinanceFormats(),
            endpoints=BinanceEndpoints(),
            orderIdGenerator=BinanceOrderIdGenerator()
        )

    async def create_order(
        self,
        symbol: str,
        side: str,
        orderType: str,
        size: float,
        price: Optional[float] = None,
    ) -> Dict:
        endpoint = self.endpoints.createOrder
        data = self.formats.create_order(symbol, side, orderType, size, price)
        return await self.client.request(
            url=self.base_endpoint.url + endpoint.url,
            method=endpoint.method,
            data=data,
            signed=False,
        )

    async def amend_order(
        self, symbol: str, orderId: int, side: str, size: float, price: float
    ) -> Dict:
        endpoint = self.endpoints.amendOrder
        data = self.formats.amend_order(orderId, size, price)
        return await self.client.request(
            url=self.base_endpoint.url + endpoint.url,
            method=endpoint.method,
            data=data,
            signed=False,
        )

    async def cancel_order(self, symbol: str, orderId: str) -> Dict:
        endpoint = self.endpoints.cancelOrder
        data = self.formats.cancel_order(symbol, orderId)
        return await self.client.request(
            url=self.base_endpoint.url + endpoint.url,
            method=endpoint.method,
            data=data,
            signed=False,
        )

    async def cancel_all_orders(self, symbol: str) -> Dict:
        endpoint = self.endpoints.cancelAllOrders
        data = self.formats.cancel_all_orders(symbol)
        return await self.client.request(
            url=self.base_endpoint.url + endpoint.url,
            method=endpoint.method,
            data=data,
            signed=False,
        )

    async def get_orderbook(self, symbol: str) -> Dict:
        endpoint = self.endpoints.getOrderbook
        params = self.formats.get_orderbook(symbol)
        return await self.client.request(
            url=self.base_endpoint.url + endpoint.url,
            method=endpoint.method,
            params=params,
            signed=False,
        )

    async def get_trades(self, symbol: str) -> Dict:
        endpoint = self.endpoints.getTrades
        params = self.formats.get_trades(symbol)
        return await self.client.request(
            url=self.base_endpoint.url + endpoint.url,
            method=endpoint.method,
            params=params,
            signed=False,
        )

    async def get_ohlcv(self, symbol: str, interval: str = "1m") -> Dict:
        endpoint = self.endpoints.getOhlcv
        params = self.formats.get_ohlcv(symbol, interval)
        return await self.client.request(
            url=self.base_endpoint.url + endpoint.url,
            method=endpoint.method,
            params=params,
            signed=False,
        )

    async def get_ticker(self, symbol: str) -> Dict:
        endpoint = self.endpoints.getTicker
        params = self.formats.get_ticker(symbol)
        return await self.client.request(
            url=self.base_endpoint.url + endpoint.url,
            method=endpoint.method,
            params=params,
            signed=False,
        )

    async def get_open_orders(self, symbol: str) -> Dict:
        endpoint = self.endpoints.getOpenOrders
        params = self.formats.get_open_orders(symbol)
        return await self.client.request(
            url=self.base_endpoint.url + endpoint.url,
            method=endpoint.method,
            params=params,
            signed=False,
        )

    async def get_position(self, symbol: str) -> Dict:
        endpoint = self.endpoints.getPosition
        params = self.formats.get_position(symbol)
        return await self.client.request(
            url=self.base_endpoint.url + endpoint.url,
            method=endpoint.method,
            params=params,
            signed=False,
        )

    async def get_account_info(self) -> Dict:
        endpoint = self.endpoints.accountInfo
        params = self.formats.get_account_info()
        return await self.client.request(
            url=self.base_endpoint.url + endpoint.url,
            method=endpoint.method,
            params=params,
            signed=False,
        )

    async def get_exchange_info(self) -> Dict:
        endpoint = self.endpoints.exchangeInfo
        params = self.formats.get_exchange_info()
        return await self.client.request(
            url=self.base_endpoint.url + endpoint.url,
            method=endpoint.method,
            params=params,
            signed=False,
        )

    async def get_listen_key(self) -> Dict:
        endpoint = self.endpoints.listenKey
        params = self.formats.get_listen_key()
        return await self.client.request(
            url=self.base_endpoint.url + endpoint.url,
            method=endpoint.method,
            params=params,
            signed=False,
        )

    async def ping_listen_key(self) -> Dict:
        endpoint = self.endpoints.pingListenKey
        params = self.formats.ping_listen_key()
        return await self.client.request(
            url=self.base_endpoint.url + endpoint.url,
            method=endpoint.method,
            params=params,
            signed=False,
        )

    async def warmup(self) -> None:
        try:
            for symbol in (await self.get_exchange_info())["symbols"]:
                if self.symbol != symbol["symbol"]:
                    continue

                for filter in symbol["filters"]:
                    match filter["filterType"]:
                        case "PRICE_FILTER":
                            self.data["tick_size"] = float(filter["tickSize"])

                        case "LOT_SIZE":
                            self.data["lot_size"] = float(filter["stepSize"])

        except Exception as e:
            await self.logging.error(f"Exchange warmup: {e}")

        finally:
            await self.logging.info(f"Exchange warmup sequence complete.")
