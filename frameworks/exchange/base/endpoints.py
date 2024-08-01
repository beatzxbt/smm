from abc import ABC
from typing import Dict, Literal


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

    def __init__(
        self, url: str, method: Literal["GET", "PUT", "POST", "DELETE", "NONE"]
    ) -> None:
        # NONE is a placeholder for base url's, which dont use a method.
        if method not in ["GET", "PUT", "POST", "DELETE", "NONE"]:
            raise ValueError(f"Invalid method for {url}: {method}")

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
        self._endpoints_: Dict[str, Endpoint] = {}

    def _add_endpoint_(self, name: str, endpoint: Endpoint) -> None:
        """
        Add an endpoint to the endpoints dictionary.

        Parameters
        ----------
        name : str
            The name of the endpoint.

        endpoint : Endpoint
            The respective endpoint object.
        """
        self._endpoints_[name] = endpoint

    def load_base(
        self, rest: Endpoint, public_ws: Endpoint, private_ws: Endpoint
    ) -> None:
        """
        Load base URLs for the API.

        Parameters
        ----------
        rest : Endpoint
            The main URL for the API.

        public_ws : Endpoint
            The URL for the public WebSocket endpoint.

        private_ws : Endpoint
            The URL for the private WebSocket endpoint.
        """
        self._endpoints_.update(
            {"rest": rest, "publicWs": public_ws, "privateWs": private_ws}
        )

    def load_required(
        self,
        createOrder: Endpoint,
        amendOrder: Endpoint,
        cancelOrder: Endpoint,
        cancelAllOrders: Endpoint,
        getOrderbook: Endpoint,
        getTrades: Endpoint,
        getTicker: Endpoint,
        getOhlcv: Endpoint,
        getOpenOrders: Endpoint,
        getPosition: Endpoint,
    ) -> None:
        """
        Load required endpoints into the endpoints dictionary.

        Parameters
        ----------
        createOrder : Endpoint
            The endpoint for creating an order.

        amendOrder : Endpoint
            The endpoint for amending an order.

        cancelOrder : Endpoint
            The endpoint for canceling an order.

        cancelAllOrders : Endpoint
            The endpoint for canceling all orders.

        getOrderbook : Endpoint
            The endpoint for getting the order book.

        getTrades : Endpoint
            The endpoint for getting trades.

        getTicker : Endpoint
            The endpoint for getting the ticker.

        getOhlcv : Endpoint
            The endpoint for getting Klines (OHLCV data).

        getOpenOrders : Endpoint
            The endpoint for getting open orders.

        getPosition : Endpoint
            The endpoint for getting positions.

        Raises
        ------
        Exception
            If any required endpoint is missing.
        """
        self._endpoints_.update(
            {
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
        )

    def load_additional(self, **kwargs: Dict[str, Endpoint]) -> None:
        """
        Load additional endpoints into the endpoints dictionary.

        Parameters
        ----------
        **kwargs : Dict[str, Endpoint]
            Additional endpoint with endpoint name as the key and a
            corresponding Endpoint object as the value.
        """
        self._endpoints_.update(kwargs)

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
