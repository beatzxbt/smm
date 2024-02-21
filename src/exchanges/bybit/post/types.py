from typing import Dict

class BybitFormats:
    """
    Provides methods to format order payloads according to Bybit's API requirements for various order operations.

    Attributes
    ----------
    category : str
        The category of the product, e.g., "linear" for linear contracts.
    symbol : str
        The trading symbol the orders will be created for.

    Methods
    -------
    create_limit(side: str, price: str, qty: str) -> Dict:
        Formats a limit order payload.
    create_market(side: str, qty: str) -> Dict:
        Formats a market order payload.
    create_amend(orderId: str, price: str, qty: str) -> Dict:
        Formats a payload for amending an existing order.
    create_cancel(orderId: str) -> Dict:
        Formats a payload for canceling a specific order.
    create_cancel_all() -> Dict:
        Formats a payload for canceling all orders for the symbol.
    """

    category = "linear"

    def __init__(self, symbol: str) -> None:
        """
        Initializes the BybitFormats class with the trading symbol.

        Parameters
        ----------
        symbol : str
            The trading symbol orders are associated with.
        """
        self.symbol = symbol
        self._base_ = {
            "category": self.category,
            "symbol": self.symbol,
        }

    def create_limit(self, side: str, price: str, qty: str) -> Dict:
        """
        Creates a dictionary payload for a limit order.

        Parameters
        ----------
        side : str
            The side of the order, either "Buy" or "Sell".
        price : str
            The price at which to place the order.
        qty : str
            The quantity of the order.

        Returns
        -------
        Dict
            A dictionary formatted for a limit order request.
        """
        return {
            **self._base_,
            "side": side,
            "orderType": "Limit",
            "price": price,
            "qty": qty,
            "timeInForce": "PostOnly",
        }

    def create_market(self, side: str, qty: str) -> Dict:
        """
        Creates a dictionary payload for a market order.

        Parameters
        ----------
        side : str
            The side of the order, either "Buy" or "Sell".
        qty : str
            The quantity of the order.

        Returns
        -------
        Dict
            A dictionary formatted for a market order request.
        """
        return {
            **self._base_,
            "side": side,
            "orderType": "Market",
            "qty": qty,
        }

    def create_amend(self, orderId: str, price: str, qty: str) -> Dict:
        """
        Creates a dictionary payload for amending an existing order.

        Parameters
        ----------
        orderId : str
            The ID of the order to amend.
        price : str
            The new price for the order.
        qty : str
            The new quantity for the order.

        Returns
        -------
        Dict
            A dictionary formatted for an amend order request.
        """
        return {
            **self._base_, 
            "orderId": orderId, 
            "price": price, 
            "qty": qty
        }
    
    def create_cancel(self, orderId: str) -> Dict:
        """
        Creates a dictionary payload for canceling a specific order.

        Parameters
        ----------
        orderId : str
            The ID of the order to cancel.

        Returns
        -------
        Dict
            A dictionary formatted for a cancel order request.
        """
        return {
            **self._base_, 
            "orderId": orderId
        }
    
    def create_cancel_all(self) -> Dict:
        """
        Creates a dictionary payload for canceling all orders for the symbol.

        Returns
        -------
        Dict
            A dictionary formatted for a cancel all orders request.
        """
        return self._base_