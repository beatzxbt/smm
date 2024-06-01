from abc import ABC
from typing import Dict


class Endpoint:
    """
    A class representing an API endpoint.

    Attributes
    ----------
    url : str
        The URL of the endpoint.

    method : str
        The HTTP method for the endpoint (GET, PUT, POST, DELETE).
    """

    def __init__(self, url: str, method: str) -> None:
        self.url = url
        self.method = method

    def __repr__(self):
        return f"Endpoint(url='{self.url}', method='{self.method}')"


class Endpoints(ABC):
    """
    An abstract base class for managing API endpoints.

    Attributes
    ----------
    _endpoints_ : dict
        A dictionary to store the endpoint objects.
    """

    def __init__(self) -> None:
        self._endpoints_ = {}

    def _add_endpoint_(self, name: str, url: str, method: str) -> None:
        """
        Add an endpoint to the endpoints dictionary.

        Parameters
        ----------
        name : str
            The name of the endpoint.

        url : str
            The URL of the endpoint.

        method : str
            The HTTP method for the endpoint (GET, PUT, POST, DELETE).

        Raises
        ------
        ValueError
            If the HTTP method is not one of GET, PUT, POST, DELETE.
        """
        if method not in ["GET", "PUT", "POST", "DELETE"]:
            raise ValueError(f"Invalid method for {url}: {method}")

        self._endpoints_[name] = Endpoint(url, method)

    def load_base(self, main: str, public_ws: str, private_ws: str) -> None:
        """
        Load base URLs for the API.

        Parameters
        ----------
        main : str
            The main URL for the API.

        public_ws : str
            The URL for the public WebSocket endpoint.

        private_ws : str
            The URL for the private WebSocket endpoint.
        """
        self._endpoints_["main"] = Endpoint(main, "")
        self._endpoints_["public_ws"] = Endpoint(public_ws, "")
        self._endpoints_["private_ws"] = Endpoint(private_ws, "")

    def load_required(
        self,
        createOrder: Dict[str, str],
        amendOrder: Dict[str, str],
        cancelOrder: Dict[str, str],
        cancelAllOrders: Dict[str, str],
        getOrderbook: Dict[str, str],
        getTrades: Dict[str, str],
        getTicker: Dict[str, str],
        getOhlcv: Dict[str, str],
        getOpenOrders: Dict[str, str],
        getPosition: Dict[str, str],
    ) -> None:
        """
        Load required endpoints into the endpoints dictionary.

        Parameters
        ----------
        createOrder : dict
            The endpoint data for creating an order.

        amendOrder : dict
            The endpoint data for amending an order.

        cancelOrder : dict
            The endpoint data for canceling an order.

        cancelAllOrders : dict
            The endpoint data for canceling all orders.

        getOrderbook : dict
            The endpoint data for getting the order book.

        getTrades : dict
            The endpoint data for getting trades.

        getTicker : dict
            The endpoint data for getting the ticker.

        getOhlcv : dict
            The endpoint data for getting Klines (OHLCV data).

        getOpenOrders : dict
            The endpoint data for getting open orders.

        getPosition : dict
            The endpoint data for getting positions.

        Raises
        ------
        Exception
            If any required endpoint is missing.
        """
        required_args = {
            "createOrder": createOrder,
            "amendOrder": amendOrder,
            "cancelOrder": cancelOrder,
            "cancelAllOrders": cancelAllOrders,
            "getOrderbook": getOrderbook,
            "getTrades": getTrades,
            "getTicker": getTicker,
            "getOhlcv": getOhlcv,
            "getOpenOrders": getOpenOrders,
            "getPosition": getPosition,
        }

        for name, data in required_args.items():
            self._add_endpoint_(name, data["url"], data["method"])

    def load_additional(self, **kwargs: Dict) -> None:
        """
        Load additional endpoints into the endpoints dictionary.

        Parameters
        ----------
        **kwargs : dict
            Additional endpoint data with endpoint name as the key and a dictionary
            containing 'url' and 'method' as the value.
        """
        for name, data in kwargs.items():
            self._add_endpoint_(name, data["url"], data["method"])

    def __getattr__(self, name: str) -> Endpoint:
        """
        Get an endpoint by name.

        Parameters
        ----------
        name : str
            The name of the endpoint.

        Returns
        -------
        Endpoint
            The endpoint object.

        Raises
        ------
        AttributeError
            If the endpoint name does not exist in the endpoints dictionary.
        """
        try:
            return self._endpoints_[name]
        except KeyError:
            raise AttributeError(f"'Endpoints' object has no attribute '{name}'")

    def __delattr__(self, name: str):
        """
        Delete an endpoint by name.

        Parameters
        ----------
        name : str
            The name of the endpoint.

        Raises
        ------
        AttributeError
            If the endpoint name does not exist in the endpoints dictionary.
        """
        try:
            del self._endpoints_[name]
        except KeyError:
            raise AttributeError(f"'Endpoints' object has no attribute '{name}'")

    def __repr__(self) -> str:
        """
        Return a string representation of the Endpoints object.

        Returns
        -------
        str
            A string representation of the Endpoints object.
        """
        return f"Endpoints({self._endpoints_})"
