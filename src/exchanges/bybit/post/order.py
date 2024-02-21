import asyncio
import aiohttp
from typing import List, Dict, Tuple, Union
from src.exchanges.bybit.post.client import BybitPrivatePostClient
from src.exchanges.bybit.endpoints import PrivatePostLinks
from src.exchanges.bybit.post.types import BybitFormats
from src.sharedstate import SharedState

class Order:
    """
    Facilitates creating, amending, and canceling orders on Bybit through asynchronous HTTP requests.
    
    Attributes
    ----------
    ss : SharedState
        An instance of SharedState containing shared application data.
    key : str
        API key for authenticated requests.
    secret : str
        API secret for signing requests.
    formats : BybitFormats
        A helper object for formatting order payloads according to Bybit's API requirements.
    endpoints : PrivatePostLinks
        Container for Bybit's API endpoint URLs.
    client : BybitPrivatePostClient
        A client configured for executing signed POST requests to Bybit.
    session : aiohttp.ClientSession
        A session for making HTTP requests.

    Methods
    -------
    order_market(order: Tuple) -> Union[Dict, None]:
        Submits a market order.
    order_limit(order: Tuple) -> Union[Dict, None]:
        Submits a limit order.
    order_limit_batch(orders: List) -> Union[Dict, None]:
        Submits a batch of limit orders.
    amend(order: Tuple) -> Union[Dict, None]:
        Amends an existing order.
    amend_batch(orders: List) -> Union[Dict, None]:
        Amends a batch of existing orders.
    cancel(orderId: str) -> Union[Dict, None]:
        Cancels an existing order by its ID.
    cancel_batch(orderIds: List) -> Union[Dict, None]:
        Cancels a batch of orders by their IDs.
    cancel_all() -> Union[Dict, None]:
        Cancels all orders for the trading symbol.
    """

    category = "linear"

    def __init__(self, ss: SharedState) -> None:
        """
        Initializes the Order object with shared state and API credentials.
        """
        self.ss = ss
        self.key, self.secret = self.ss.api_key, self.ss.api_secret
        self.formats = BybitFormats(self.ss.bybit_symbol)
        self.endpoints = PrivatePostLinks
        self.client = BybitPrivatePostClient(self.ss)
        self.session = aiohttp.ClientSession()

    def _order_to_str_(self, order: List) -> List[str]:
        """
        Converts order elements to strings for API submission.

        Parameters
        ----------
        order : List
            The order details as a list.

        Returns
        -------
        List[str]
            The order details with all elements converted to strings.
        """
        return list(map(str, order))

    async def _submit_(self, endpoint: str, payload: Dict) -> Union[Dict, None]:
        """
        Submits an order to a specified endpoint with the given payload.

        Parameters
        ----------
        endpoint : str
            The API endpoint to submit the order to.
        payload : Dict
            The payload of the order.

        Returns
        -------
        Union[Dict, None]
            The response from the API if successful; otherwise, None.
        """
        async with self.session:
            return await self.client.submit(self.session, endpoint, payload)

    async def _sessionless_submit_(self, endpoint: str, payload: Dict) -> Union[Dict, None]:
        """
        Submits an order without managing the session lifecycle, assuming the session is already active.

        Parameters
        ----------
        endpoint : str
            The API endpoint to submit the order to.
        payload : Dict
            The payload of the order.

        Returns
        -------
        Union[Dict, None]
            The response from the API if successful; otherwise, None.
        """
        return await self.client.submit(self.session, endpoint, payload)

    async def order_market(self, order: Tuple[str, float]) -> Union[Dict, None]:
        """
        Asynchronously places a market order on Bybit.

        Parameters
        ----------
        order : Tuple[str, float]
            The order details, including side ('Buy' or 'Sell') and quantity.

        Returns
        -------
        Union[Dict, None]
            The response from Bybit's API if the order is successfully placed; otherwise, None.
        """
        endpoint = self.endpoints.CREATE_ORDER
        side, qty = self._order_to_str_(order)
        payload = self.formats.create_market(side, qty)
        return await self._submit_(endpoint, payload)

    async def order_limit(self, order: Tuple[str, float, float]) -> Union[Dict, None]:
        """
        Asynchronously places a limit order on Bybit.

        Parameters
        ----------
        order : Tuple[str, float, float]
            The order details, including side ('Buy' or 'Sell'), price, and quantity.

        Returns
        -------
        Union[Dict, None]
            The response from Bybit's API if the order is successfully placed; otherwise, None.
        """
        endpoint = self.endpoints.CREATE_ORDER
        side, price, qty = self._order_to_str_(order)
        payload = self.formats.create_limit(side, price, qty)
        return await self._submit_(endpoint, payload)

    async def order_limit_batch(self, orders: List[Tuple[str, float, float]]) -> Union[Dict, None]:
        """
        Asynchronously places a batch of limit orders on Bybit.

        Parameters
        ----------
        orders : List[Tuple[str, float, float]]
            A list of orders, each including side ('Buy' or 'Sell'), price, and quantity.

        Returns
        -------
        Union[Dict, None]
            The response from Bybit's API if the orders are successfully placed; otherwise, None.
        """
        batch_endpoint = self.endpoints.CREATE_BATCH
        tasks = []

        # Split the orders into chunks of 10 for batch processing
        for i in range(0, len(orders), 10):
            batch_orders = [self._order_to_str_(order) for order in orders[i:i+10]]
            batch_payload = {
                "category": self.category, 
                "request": [
                    self.formats.create_limit(*order)
                    for order in batch_orders
                ]
            }
            task = asyncio.create_task(self._sessionless_submit_(batch_endpoint, batch_payload))
            tasks.append(task)

        result = await asyncio.gather(*tasks)
        await self.close_session()
        return result
         
    async def amend(self, order: Tuple[str, float, float]) -> Union[Dict, None]:
        """
        Asynchronously amends an existing order on Bybit.

        Parameters
        ----------
        order : Tuple[str, float, float]
            The order details to be amended, including the order ID, new price, and new quantity.

        Returns
        -------
        Union[Dict, None]
            The response from Bybit's API if the order is successfully amended; otherwise, None.
        """
        endpoint = self.endpoints.AMEND_ORDER
        order_id, price, qty = self._order_to_str_(order)
        payload = self.formats.create_amend(order_id, price, qty)
        return await self._submit_(endpoint, payload)

    async def amend_batch(self, orders: List[Tuple[str, float, float]]) -> Union[Dict, None]:
        """
        Asynchronously amends a batch of existing orders on Bybit.

        Parameters
        ----------
        orders : List[Tuple[str, float, float]]
            A list of orders to be amended, each including the order ID, new price, and new quantity.

        Returns
        -------
        Union[Dict, None]
            The response from Bybit's API if the orders are successfully amended; otherwise, None.
        """
        batch_endpoint = self.endpoints.AMEND_BATCH
        tasks = []

        # Split the orders into chunks of 10 for batch processing
        for i in range(0, len(orders), 10):
            batch_orders = [self._order_to_str_(order) for order in orders[i:i+10]]
            batch_payload = {
                "category": self.category, 
                "request": [
                    self.formats.create_amend(*order)
                    for order in batch_orders
                ]
            }
            task = asyncio.create_task(self._sessionless_submit_(batch_endpoint, batch_payload))
            tasks.append(task)

        result = await asyncio.gather(*tasks)
        await self.close_session()
        return result

    async def cancel(self, order_id: str) -> Union[Dict, None]:
        """
        Asynchronously cancels an existing order on Bybit by order ID.

        Parameters
        ----------
        order_id : str
            The ID of the order to cancel.

        Returns
        -------
        Union[Dict, None]
            The response from Bybit's API if the order is successfully canceled; otherwise, None.
        """
        endpoint = self.endpoints.CANCEL_SINGLE
        payload = self.formats.create_cancel(order_id)
        return await self._submit_(endpoint, payload)

    async def cancel_batch(self, order_ids: List[str]) -> Union[Dict, None]:
        """
        Asynchronously cancels a batch of existing orders on Bybit by their order IDs.

        Parameters
        ----------
        order_ids : List[str]
            A list of order IDs to cancel.

        Returns
        -------
        Union[Dict, None]
            The response from Bybit's API if the orders are successfully canceled; otherwise, None.
        """
        batch_endpoint = self.endpoints.CANCEL_BATCH
        tasks = []

        # Split the order IDs into chunks of 10 for batch processing
        for i in range(0, len(order_ids), 10):
            batch_payload = {
                "category": self.category, 
                "request": [
                    self.formats.create_cancel(order_id)
                    for order_id in order_ids[i:i+10]
                ]
            }
            task = asyncio.create_task(self._sessionless_submit_(batch_endpoint, batch_payload))
            tasks.append(task)

        result = await asyncio.gather(*tasks)
        await self.close_session()
        return result

    async def cancel_all(self) -> Union[Dict, None]:
        """
        Asynchronously cancels all orders for the trading symbol on Bybit.

        Returns
        -------
        Union[Dict, None]
            The response from Bybit's API if all orders are successfully canceled; otherwise, None.
        """
        endpoint = self.endpoints.CANCEL_ALL
        payload = self.formats.create_cancel_all()
        return await self._submit_(endpoint, payload)
    
    async def close_session(self) -> None:
        """
        Asynchronously close the current session
        """
        await self.session.close()