from dydx_v4_client import NodeClient, Wallet
from dydx_v4_client.indexer.rest.indexer_client import IndexerClient
from dydx_v4_client.node.market import Market
from typing import Dict

from frameworks.exchange.base.exchange import Exchange
from frameworks.exchange.base.structures.order import Order
from frameworks.exchange.dydx_v4.endpoints import DydxEndpoints
from frameworks.exchange.dydx_v4.formats import DydxFormats
from frameworks.exchange.dydx_v4.client import DydxClient
from frameworks.exchange.dydx_v4.orderid import DydxOrderIdGenerator


class Dydx(Exchange):
    def __init__(self, api_key: str, api_secret: str) -> None:
        self.api_key = api_key
        self.api_secret = api_secret

        super().__init__(
            client=DydxClient(self.api_key, self.api_secret),
            formats=DydxFormats(),
            endpoints=DydxEndpoints(),
            orderIdGenerator=DydxOrderIdGenerator()
        )

    async def create_order(
        self,
        order
    ) -> Dict:
        return await self.client.node.place_order(
            wallet=self.client.wallet,
            order=self.client.market.order(
                order_id=order.clientOrderId,
                side=self.formats.convert_side.num_to_str(order.side),
                size=order.size,
                price=order.price,
                time_in_force=self.formats.convert_tif(order.timeInForce),
                reduce_only=False
            )
        )

    async def amend_order(
        self, order
    ) -> Dict:
        endpoint = self.endpoints.amendOrder
        headers = self.formats.amend_order(order)
        return await self.client.request(
            url=self.base_endpoint.url + endpoint.url,
            method=endpoint.method,
            headers=self.client.base_headers,
            data=self.client.sign_headers(endpoint.method, headers),
            signed=True,
        )

    async def cancel_order(self, order) -> Dict:
        endpoint = self.endpoints.cancelOrder
        headers = self.formats.cancel_order(order)
        return await self.client.request(
            url=self.base_endpoint.url + endpoint.url,
            method=endpoint.method,
            headers=self.client.base_headers,
            data=self.client.sign_headers(endpoint.method, headers),
            signed=True,
        )
    
    async def cancel_all_orders(self, symbol: str) -> Dict:
        endpoint = self.endpoints.cancelAllOrders
        headers = self.formats.cancel_all_orders(symbol)
        return await self.client.request(
            url=self.base_endpoint.url + endpoint.url,
            method=endpoint.method,
            headers=self.client.base_headers,
            data=self.client.sign_headers(endpoint.method, headers),
            signed=True,
        )

    async def get_orderbook(self, symbol: str) -> Dict:
        return await self.client.indexer.markets.get_perpetual_market_orderbook(
            market=symbol
        )

    async def get_trades(self, symbol: str) -> Dict:
        return await self.client.indexer.markets.get_perpetual_market_trades(
            market=symbol
        )

    async def get_ohlcv(self, symbol: str, interval: str = "1MIN") -> Dict:
        return await self.client.indexer.markets.get_perpetual_market_candles(
            market=symbol,
            resolution=interval
        )

    async def get_ticker(self, symbol: str) -> Dict:
        return await self.client.indexer.markets.get_perpetual_markets(
            market=symbol
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

    async def warmup(self) -> None:
        try:
            self.client.indexer = IndexerClient(host=self.endpoints["rest"].url)
            self.client.node = NodeClient()
            self.client.market = Market(
                market=(await self.client.indexer.markets.get_perpetual_markets(self.symbol))["markets"][self.symbol]
            )

            self.data["tick_size"] = float(self.client.market.market["tickSize"])
            self.data["lot_size"] = float(self.client.market.market["stepSize"])
            
            self.client.wallet = await Wallet.from_mnemonic(self.node, DYDX_TEST_MNEMONIC, self.api_key)

        except Exception as e:
            await self.logging.error(f"Dydx exchange warmup: {e}")

        finally:
            await self.logging.info(f"Dydx exchange warmup sequence complete.")
