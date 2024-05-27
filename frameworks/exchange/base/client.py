import asyncio
import aiosonic
import orjson
from abc import ABC, abstractmethod
from typing import Tuple, Dict, Union, Any, Literal

from frameworks.tools.logging import Logger, time_ms


class Client(ABC):
    """
    Client is an abstract base class for interfacing with various APIs.

    This class provides a template for API clients, handling common functionality 
    such as session management, payload signing, error handling, and request sending 
    with retry logic.
    """

    max_retries = 3

    # [https://github.com/ccxt/ccxt/blob/9ab59963f780c4ded7cd76ffa9e58b7f3fdd6e79/python/ccxt/base/exchange.py#L229]
    http_exceptions = {
        422: "ExchangeError",
        418: "DDoSProtection",
        429: "RateLimitExceeded",
        404: "ExchangeNotAvailable",
        409: "ExchangeNotAvailable",
        410: "ExchangeNotAvailable",
        451: "ExchangeNotAvailable",
        500: "ExchangeNotAvailable",
        501: "ExchangeNotAvailable",
        502: "ExchangeNotAvailable",
        520: "ExchangeNotAvailable",
        521: "ExchangeNotAvailable",
        522: "ExchangeNotAvailable",
        525: "ExchangeNotAvailable",
        526: "ExchangeNotAvailable",
        400: "ExchangeNotAvailable",
        403: "ExchangeNotAvailable",
        405: "ExchangeNotAvailable",
        503: "ExchangeNotAvailable",
        530: "ExchangeNotAvailable",
        408: "RequestTimeout",
        504: "RequestTimeout",
        401: "AuthenticationError",
        407: "AuthenticationError",
        511: "AuthenticationError",
    }

    def __init__(self, api_key: str, api_secret: str) -> None:
        """
        Initializes the Client class with API key and secret.

        Parameters
        ----------
        api_key : str
            The API key for authentication.

        api_secret : str
            The API secret for authentication.
        """
        self.api_key, self.api_secret = api_key, api_secret
        self.session = aiosonic.HTTPClient()
        self.timestamp = str(time_ms())

        self.default_headers = {
            "Accept": "application/json"
        }

    def load_required_refs(self, logging: Logger) -> None:
        """
        Loads required references such as logging.

        Parameters
        ----------
        logging : Logger
            The Logger instance for logging events and messages.
        """
        self.logging = logging

    def update_timestamp(self) -> int:
        """
        Updates and returns the current timestamp.

        This method updates the internal timestamp to the current time in milliseconds.

        Returns
        -------
        int
            The updated timestamp.
        """
        self.timestamp = time_ms()
        return self.timestamp
    
    async def response_code_checker(self, code: int) -> bool:
        """
        Check the status code and raise exceptions for errors.

        This method checks if the given HTTP status code is a known error code.
        It raises an exception with the reason for known error codes and for unknown status codes.

        Parameters
        ----------
        code : int
            The HTTP status code to check.

        Returns
        -------
        bool
            True if the status code is between 200 and 299 (inclusive).

        Raises
        ------
        Exception
            If the status code is known, the exception message includes the reason.
            If the status code is unknown, the exception message indicates it is unknown.
        """
        match code:
            case code if 200 <= code <= 299:
                return True
            
            case code if code in self.http_exceptions:
                reason = self.http_exceptions[code]
                raise Exception(f"Known status code :: {code} | {reason}")
            
            case _:
                raise Exception(f"Unknown status code :: {code}")
        
    @abstractmethod
    def sign_headers(self, method: str, header: Dict) -> Dict[str, Any]:
        """
        Sign & encrypt the header inline the appropriate exchange's needs.

        Parameters
        ----------
        method : str
            The header to be signed.

        header : Dict
            The header to be signed.

        Returns
        -------
        Dict[str, Any]
            The updated dictionary with the required signed/encrypted data.
        """
        pass
    
    @abstractmethod
    def error_handler(self, recv: Dict[str, Any]) -> Tuple[bool, str]:
        """
        Handle errors received from the API response.

        This method interprets the error codes returned by the API and provides a standardized
        way to determine the appropriate action to take. It uses pattern matching or a similar 
        mechanism to map error codes to human-readable messages and retry logic.

        Parameters
        ----------
        recv : Dict[str, Any]
            The response dictionary received from the API, expected to contain an error code.

        Returns
        -------
        Tuple[bool, str]
            A tuple indicating whether to retry (True or False) and the error message.
        """
        pass
    
    async def request(
        self,
        url: str,
        method: Literal["GET", "PUT", "POST", "DELETE"],
        headers: Union[Dict[str, str], str]=None,
        params: Dict[str, str]=None,
        data: Dict[str, Any]=None,
        signed: bool=False
    ) -> Union[Dict, Exception]:
        """
        Sends an API request with retry logic.

        This method sends an HTTP request to the specified URL using the given method.
        It handles optional headers, parameters, and payloads, and includes support for
        payload signing. The method includes retry logic with exponential backoff in case 
        of errors.

        Parameters
        ----------
        url : str
            The API URL to send the request to.
        
        method : Literal["GET", "PUT", "POST", "DELETE"]
            The HTTP method to use for the request (e.g., 'GET', 'PUT', 'POST', 'DELETE').
        
        headers : Union[Dict[str, Any], str], optional
            The headers to include in the request. Default is None.
        
        params : Dict[str, Any], optional
            The query parameters to include in the request. Default is None.
        
        data : Dict[str, Any], optional
            The data to include in the request. Default is None.
        
        signed : bool, optional
            Whether the header is pre-signed or not. Default is False.

        Returns
        -------
        Dict
            The API response as a dictionary if successful.

        Raises
        ------
        Raises an exception if all retries fail.
        """
        for attempt in range(1, self.max_retries + 1):
            try:
                if headers and not signed:
                    headers = self.sign_headers(method, headers)
                
                # print(f"\n{method} :: {url}\n{headers}\n{orjson.dumps(data).decode() if data else ''} ")

                response = await self.session.request(
                    url=url,
                    method=method,
                    headers=headers if headers else None,
                    params=params if params else None,
                    data=orjson.dumps(data).decode() if data else None
                )

                # Successful usually within: 200 <= Code <= 299
                if await self.response_code_checker(response.status_code):
                    response_json = orjson.loads(await response.content())

                    if isinstance(response_json, Dict):
                        retry, msg = self.error_handler(response_json)

                        if retry and msg:
                            await self.logging.warning(f"Retry attempt {attempt} due to: {msg}")
                            await asyncio.sleep(attempt/10)  # Exponential backoff
                            continue

                        elif msg:
                            await self.logging.warning(f"Failed to send request: {msg}")

                    return response_json
                    
            except orjson.JSONDecodeError as e:
                await self.logging.error(f"JSON decode error: {e}")
                if attempt >= self.max_retries:
                    raise e

            except Exception as e:
                await self.logging.error(f"Client error: {e}")
                if attempt >= self.max_retries:
                    raise e
                
                await asyncio.sleep(attempt)

    async def shutdown(self) -> None:
        """
        Close the client's HTTP session, if existing.

        Returns
        -------
        None
        """
        if self.session:
            await self.logging.warning("Shutting down client...")
            await self.session.connector.cleanup()
            await self.session.__aexit__(None, None, None)
            del self.session