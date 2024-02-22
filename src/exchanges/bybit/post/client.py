import hashlib
import hmac
import aiohttp
import orjson
import asyncio
from typing import Dict
from src.utils.misc import time_ms, datetime_now as dt_now
from src.exchanges.bybit.endpoints import BaseEndpoints
from src.sharedstate import SharedState

class BybitPrivatePostClient:
    """
    Manages the execution of private POST requests to Bybit's API, handling authentication,
    request signing, and retry logic for failed requests due to rate limiting or other errors.

    Attributes
    ----------
    ss : SharedState
        An instance of SharedState containing shared application data.
    max_retries : int
        The maximum number of retries for a request before giving up.
    recv_window : str
        The time in milliseconds the server allows for a request to be processed.
    _success_ : List[str]
        A list of messages indicating a successful request.
    _retry_ : List[int]
        A list of error codes that should trigger a retry of the request.
    _skip_ : List[int]
        A list of error codes that should not trigger a retry and instead skip the request.

    Methods
    -------
    _update_timestamp_() -> None:
        Updates the timestamp for request signing.
    _sign_(payload: str) -> Dict:
        Signs the request payload for authentication.
    submit(session: aiohttp.ClientSession, endpoint: str, payload: dict) -> asyncio.Future:
        Asynchronously submits a POST request to the specified Bybit API endpoint.
    """

    max_retries = 3
    recv_window = "5000"
    _success_ = ["OK", "success", "SUCCESS", ""]
    _retry_ = [100016] # NOTE: Add more
    _skip_ = [10006, 110001, 110012] # NOTE: Add more

    def __init__(self, ss: SharedState) -> None:
        """
        Initializes the BybitPrivatePostClient with shared state and API credentials.

        Parameters
        ----------
        ss : SharedState
            An instance of SharedState containing shared application data.
        """
        self.ss = ss
        self.key, self.secret = self.ss.api_key, self.ss.api_secret
        self.base_endpoint = BaseEndpoints.MAINNET1
        self.timestamp = time_ms()

        self.static_headers = {
            "X-BAPI-TIMESTAMP": self.timestamp,
            "X-BAPI-RECV-WINDOW": self.recv_window,
            "X-BAPI-API-KEY": self.key, 
            "X-BAPI-SIGN": ""
        }

        self.static_partial_str = "".join([self.key, self.recv_window])

    def _update_timestamp_(self) -> None:
        """
        Updates the timestamp attribute to the current time in milliseconds.
        """
        self.timestamp = str(time_ms())

    def _sign_(self, payload: str) -> Dict:
        """
        Generates a signature for the given payload and updates request headers.

        Parameters
        ----------
        payload : str
            The request payload to be signed.

        Returns
        -------
        Dict
            The updated headers containing the signature.
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

    async def submit(self, session: aiohttp.ClientSession, endpoint: str, payload: dict) -> Dict:
        """
        Asynchronously submits a signed POST request to Bybit.

        Parameters
        ----------
        session : aiohttp.ClientSession
            The session used to send the request.
        endpoint : str
            The API endpoint to which the request is sent.
        payload : dict
            The payload of the request.

        Returns
        -------
        Dict
            The JSON response from the API if successful.

        Raises
        ------
        Exception
            If the request fails after the maximum number of retries.
        """
        str_payload = orjson.dumps(payload).decode()
        signed_header = self._sign_(str_payload)
        full_endpoint = self.base_endpoint + endpoint
        max_retries = self.max_retries
        
        for attempt in range(max_retries):
            try:
                req = await session.request("POST", full_endpoint, headers=signed_header, data=str_payload)
                response = orjson.loads(await req.text())
                code, msg = response["retCode"], response["retMsg"]

                if msg in self._success_:
                    return {
                        "result": response["result"],
                        "latency": int(response["time"]) - int(self.timestamp)
                    }
                elif code in self._retry_: 
                    raise Exception(f"Error: {code}/{msg} | Endpoint: {endpoint}")
                else:            
                    print(f"{dt_now()}: Error: {code}/{msg} | Endpoint: {endpoint}")
                    break
            except Exception as e:
                if attempt < max_retries - 1:
                    await asyncio.sleep(attempt + 1)  # Incremental back-off
                    signed_header = self._sign_(str_payload)
                else:
                    raise e