from dydx_v4_client import NodeClient, Wallet
from dydx_v4_client.indexer.rest.indexer_client import IndexerClient
from dydx_v4_client.node.market import Market
from typing import List, Dict, Optional

from frameworks.exchange.base.exchange import Exchange
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
        symbol: str,
        side: float,
        orderType: float,
        size: float,
        price: Optional[float]=None,
        clientOrderId: Optional[str]=None
    ) -> Dict:
        return await self.client.node.place_order(
            wallet=self.client.wallet,
            order=self.client.market.order(
                order_id=clientOrderId,
                side=self.formats.convert_side.num_to_str(side),
                size=size,
                price=price,
                time_in_force=self.formats.convert_tif(),
                reduce_only=False
            )
        )
    
    async def batch_create_orders(
        self,
        symbol: str,
        sides: List[int],
        orderTypes: List[int],
        sizes: List[float],
        prices: Optional[List[float]]=None,
        clientOrderIds: Optional[List[str]]=None
    ) -> Dict:
        endpoint = self.endpoints.batchCreateOrders
        headers = self.formats.batch_create_orders(symbol, sides, orderTypes, sizes, prices, clientOrderIds)
        return await self.client.request(
            url=self.base_endpoint.url + endpoint.url,
            method=endpoint.method,
            headers=headers,
            data=headers,
            signed=False,
        )

    async def amend_order(
        self, symbol: str, orderId: str, clientOrderId: str, side: float, size: float, price: float
    ) -> Dict:
        endpoint = self.endpoints.amendOrder
        headers = self.formats.amend_order(symbol, orderId, clientOrderId, side, size, price)
        return await self.client.request(
            url=self.base_endpoint.url + endpoint.url,
            method=endpoint.method,
            headers=headers,
            data=headers,
            signed=False,
        )
    
    async def batch_amend_orders(
        self,
        symbol: str,
        sides: List[int],
        orderTypes: List[int],
        sizes: List[float],
        prices: Optional[List[float]]=None,
        orderIds: Optional[List[str]]=None,
        clientOrderIds: Optional[List[str]]=None
    ) -> Dict:
        endpoint = self.endpoints.batchAmendOrders
        headers = self.formats.batch_amend_orders(symbol, sides, orderTypes, sizes, prices, orderIds, clientOrderIds)
        return await self.client.request(
            url=self.base_endpoint.url + endpoint.url,
            method=endpoint.method,
            headers=headers,
            data=headers,
            signed=False,
        )

    async def cancel_order(self, symbol: str, orderId: str, clientOrderId: str) -> Dict:
        endpoint = self.endpoints.cancelOrder
        headers = self.formats.cancel_order(symbol, orderId, clientOrderId)
        return await self.client.request(
            url=self.base_endpoint.url + endpoint.url,
            method=endpoint.method,
            headers=headers,
            data=headers,
            signed=False,
        )
    
    async def batch_cancel_orders(
        self,
        symbol: str, 
        orderIds: List[Optional[str]],
        clientOrderIds: List[Optional[str]]
    ) -> Dict:
        endpoint = self.endpoints.batchCancelOrders
        headers = self.formats.batch_cancel_orders(symbol, orderIds, clientOrderIds)
        return await self.client.request(
            url=self.base_endpoint.url + endpoint.url,
            method=endpoint.method,
            headers=headers,
            data=headers,
            signed=False,
        )
    
    async def cancel_all_orders(self, symbol: str) -> Dict:
        endpoint = self.endpoints.cancelAllOrders
        headers = self.formats.cancel_all_orders(symbol)
        return await self.client.request(
            url=self.base_endpoint.url + endpoint.url,
            method=endpoint.method,
            headers=headers,
            data=headers,
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

    async def get_ohlcv(self, symbol: str, interval: int = 1) -> Dict:
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
            headers=params,
            params=params,
            signed=False,
        )

    async def get_position(self, symbol: str) -> Dict:
        endpoint = self.endpoints.getPosition
        params = self.formats.get_position(symbol)
        return await self.client.request(
            url=self.base_endpoint.url + endpoint.url,
            method=endpoint.method,
            headers=params,
            params=params,
            signed=False,
        )

    async def get_instrument_info(self, symbol: str) -> Dict:
        endpoint = self.endpoints.getInstrumentInfo
        params = self.formats.get_instrument_info(symbol)
        return await self.client.request(
            url=self.base_endpoint.url + endpoint.url,
            method=endpoint.method,
            params=params,
        )
    
    async def set_leverage(self, symbol: str, leverage: int) -> Dict:
        endpoint = self.endpoints.setLeverage
        headers = self.formats.set_leverage(symbol, leverage)
        return await self.client.request(
            url=self.base_endpoint.url + endpoint.url,
            method=endpoint.method,
            headers=headers,
            data=headers,
            signed=False,
        )

    async def warmup(self) -> None:
        try:
            self.client.node = NodeClient()
            self.client.indexer = IndexerClient()
            self.client.market = Market(
                market=(await self.client.indexer.markets.get_perpetual_markets(market=self.symbol))["markets"][self.symbol]
            )
            self.client.wallet = await Wallet.from_mnemonic(self.node, DYDX_TEST_MNEMONIC, self.api_key)

            for instrument in instrument_data["result"]["list"]:
                if instrument["symbol"] != self.symbol:
                    continue

                self.data["tick_size"] = float(instrument["priceFilter"]["tickSize"])
                self.data["lot_size"] = float(instrument["lotSizeFilter"]["qtyStep"])
                
                return None

        except Exception as e:
            await self.logging.error(f"Dydx exchange warmup: {e}")

        finally:
            await self.logging.info(f"Dydx exchange warmup sequence complete.")
