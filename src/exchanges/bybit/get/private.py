import hashlib
import hmac
import aiohttp
import orjson
import asyncio
from typing import Dict, Union
from src.utils.misc import time_ms, datetime_now as dt_now
from src.exchanges.bybit.endpoints import BaseEndpoints, PrivateGetLinks
from src.sharedstate import SharedState


class BybitPrivateGetClient:
    """
    Handles the private GET requests to Bybit's API with signature authentication.

    Attributes
    ----------
    ss : SharedState
        An instance of SharedState containing shared application data.
    max_retries : int
        Maximum number of retries for a request before giving up.
    recv_window : str
        The time in milliseconds the request is valid after the timestamp.
    _success_ : List[str]
        List of messages indicating a successful request.
    _retry_ : List[int]
        List of error codes that should trigger a retry.
    _skip_ : List[int]
        List of error codes to skip or ignore without retrying.

    Methods
    -------
    submit(session: aiohttp.ClientSession, endpoint: str, payload: str) -> Union[Dict, None]:
        Submits a signed GET request to a specific Bybit API endpoint and returns the response.
    """

    max_retries = 3
    recv_window = "5000"
    _success_ = ["OK", "success", "SUCCESS", ""]
    _retry_ = [100016]  # NOTE: Add more as necessary
    _skip_ = [10006, 110001, 110012]  # NOTE: Add more as necessary

    def __init__(self, ss: SharedState) -> None:
        """
        Initializes the BybitPrivateGetClient with API credentials and base endpoint.

        Parameters
        ----------
        ss : SharedState
            An instance of SharedState containing shared application data.
        """
        self.ss = ss
        self.key, self.secret = self.ss.api_key, self.ss.api_secret
        self.base_endpoint = BaseEndpoints.MAINNET1
        self.timestamp = time_ms()

        # Predefined headers for requests, except the signature which is calculated per request
        self.static_headers = {
            "X-BAPI-TIMESTAMP": self.timestamp,
            "X-BAPI-RECV-WINDOW": self.recv_window,
            "X-BAPI-API-KEY": self.key,
            "X-BAPI-SIGN-TYPE": "2",
            "X-BAPI-SIGN": ""
        }

        self.static_partial_str = "".join([self.key, self.recv_window])

    def _update_timestamp_(self) -> None:
        """
        Updates the timestamp for signing requests, ensuring it's current.
        """
        self.timestamp = str(time_ms())

    def _sign_(self, payload: str) -> Dict:
        """
        Signs the request payload with the API secret key.

        Parameters
        ----------
        payload : str
            The request payload to be signed.

        Returns
        -------
        Dict
            The headers including the updated timestamp and signature.
        """
        self._update_timestamp_()
        param_str = "".join([self.timestamp, self.static_partial_str, payload])
        hash_signature = hmac.new(
            bytes(self.secret, "utf-8"),
            param_str.encode("utf-8"),
            hashlib.sha256
        ).hexdigest()
        self.static_headers["X-BAPI-TIMESTAMP"] = self.timestamp
        self.static_headers["X-BAPI-SIGN"] = hash_signature
        return self.static_headers

    async def submit(self, session: aiohttp.ClientSession, endpoint: str, payload: str) -> Union[Dict, None]:
        """
        Asynchronously submits a signed GET request to the specified endpoint.

        Parameters
        ----------
        session : aiohttp.ClientSession
            The session used to send the request.
        endpoint : str
            The API endpoint to which the request is sent.
        payload : str
            The request payload used for signing.

        Returns
        -------
        Union[Dict, None]
            The JSON response from the API or None if an error occurs.
        """
        signed_header = self._sign_(payload)
        full_endpoint = self.base_endpoint + endpoint
        max_retries = self.max_retries
    
        for attempt in range(max_retries):
            try:
                req = await session.request("GET", url=full_endpoint, headers=signed_header)
                response = orjson.loads(await req.text())
                code, msg = response["retCode"], response["retMsg"]

                if msg in self._success_:
                    return response
                
                else:
                    if code in self._retry_: 
                        raise Exception(f"Error: {code}/{msg} | Endpoint: {endpoint}")
                
                    else:            
                        print(f"{dt_now()}: Error: {code}/{msg} | Endpoint: {endpoint}")
                        break

            except Exception as e:
                if attempt < max_retries - 1:  
                    await asyncio.sleep(attempt)  
                    signed_header = self._sign_(payload)
                else:
                    raise e 


import aiohttp
from typing import Dict, Union
from src.sharedstate import SharedState
from src.exchanges.bybit.endpoints import PrivateGetLinks

class BybitPrivateGet:
    """
    Handles the retrieval of private data from Bybit's API, such as open orders and current positions.

    Attributes
    ----------
    ss : SharedState
        An instance of SharedState containing shared application data.
    symbol : str
        The trading symbol to query data for, obtained from the shared state.
    endpoints : PrivateGetLinks
        Container for API endpoint URLs specific to Bybit's private data retrieval.
    client : BybitPrivateGetClient
        A client configured to interact with Bybit's private API endpoints.
    session : aiohttp.ClientSession
        An active session for making HTTP requests asynchronously.

    Methods
    -------
    open_orders() -> Union[Dict, None]:
        Fetches the current open orders for the specified trading symbol.
    current_position() -> Union[Dict, None]:
        Retrieves the current position for the specified trading symbol.
    _close_() -> None:
        Closes the active aiohttp session gracefully.
    """

    def __init__(self, ss: SharedState) -> None:
        """
        Initializes the BybitPrivateGet class with shared state, API endpoints, and a session for HTTP requests.

        Parameters
        ----------
        ss : SharedState
            An instance of SharedState containing shared application data.
        """
        self.ss = ss
        self.symbol = self.ss.bybit_symbol
        self.endpoints = PrivateGetLinks
        self.client = BybitPrivateGetClient(self.ss)
        self.session = aiohttp.ClientSession()

    async def open_orders(self) -> Union[Dict, None]:
        """
        Asynchronously retrieves the list of open orders for the trading symbol from Bybit.

        Returns
        -------
        Union[Dict, None]
            A dictionary containing the open orders if successful, otherwise None.
        """
        payload = f"category=linear&symbol={self.symbol}&limit=50"
        endpoint = f"{self.endpoints.OPEN_ORDERS}?{payload}"
        return await self.client.submit(self.session, endpoint, payload)

    async def current_position(self) -> Union[Dict, None]:
        """
        Asynchronously fetches the current position for the trading symbol from Bybit.

        Returns
        -------
        Union[Dict, None]
            A dictionary containing the current position if successful, otherwise None.
        """
        payload = f"category=linear&symbol={self.symbol}"
        endpoint = f"{self.endpoints.CURRENT_POSITION}?{payload}"
        return await self.client.submit(self.session, endpoint, payload)
 
    async def _close_(self) -> None:
        """
        Closes the aiohttp session associated with this instance.

        This method should be called to release resources before the instance is discarded.
        """
        await self.session.close()