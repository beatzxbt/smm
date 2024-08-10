from typing import List, Dict, Any, Optional, Union


class Order:
    """
    A class to represent an order.

    Attributes
    ----------
    symbol : str
        The trading symbol of the order.

    side : float
        The side of the order (buy/sell).

    orderType : float
        The type of the order.

    timeInForce : float
        The time in force for the order.

    size : float
        The size of the order.

    price : Optional[float]
        The price of the order.

    orderId : Optional[str]
        The order ID.

    clientOrderId : Optional[str]
        The client order ID.
    """

    def __init__(
        self,
        symbol: str = None,
        side: float = None,
        orderType: float = None,
        timeInForce: float = None,
        size: float = None,
        price: Optional[float] = None,
        orderId: Optional[str] = None,
        clientOrderId: Optional[str] = None,
    ) -> None:
        self._symbol = symbol
        self._side = side
        self._orderType = orderType
        self._timeInForce = timeInForce
        self._size = size
        self._price = price
        self._orderId = orderId
        self._clientOrderId = clientOrderId

    @property
    def symbol(self) -> str:
        return self._symbol

    @property
    def side(self) -> float:
        return self._side

    @property
    def orderType(self) -> float:
        return self._orderType

    @property
    def timeInForce(self) -> float:
        return self._timeInForce

    @property
    def size(self) -> float:
        return self._size
    
    @property
    def price(self) -> Union[float, None]:
        return self._price

    @property
    def orderId(self) -> Union[str, None]:
        return self._orderId

    @property
    def clientOrderId(self) -> Union[str, None]:
        return self._clientOrderId

    def __bool__(self) -> bool:
        return any(
            [
                self._symbol,
                self._side,
                self._orderType,
                self._timeInForce,
                self._price,
                self._size,
                self._orderId,
                self._clientOrderId,
            ]
        )

    def __eq__(self, other: Union['Order', Any]) -> bool:
        if isinstance(other, Order):
            return (
                self.symbol == other.symbol
                and self.side == other.side
                and self.orderType == other.orderType
                and self.timeInForce == other.timeInForce
                and self.price == other.price
                and self.size == other.size
                and self.orderId == other.orderId
                and self.clientOrderId == other.clientOrderId
            )
        return False
    
    def __repr__(self) -> str:
        return (
            f"Order(symbol={self.symbol}, side={self.side}, orderType={self.orderType}, "
            f"timeInForce={self.timeInForce}, size={self.size}, price={self.price}, "
            f"orderId={self.orderId}, clientOrderId={self.clientOrderId})"
        )

    def to_dict(self) -> Dict[str, Union[str, float, None]]:
        """
        Converts the Order object to a dictionary.

        Returns
        -------
        Dict
            The dictionary representation of the Order object.
        """
        return {
            "symbol": self._symbol,
            "side": self._side,
            "orderType": self._orderType,
            "timeInForce": self._timeInForce,
            "size": self._size,
            "price": self._price,
            "orderId": self._orderId,
            "clientOrderId": self._clientOrderId,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Union[str, float, None]]) -> "Order":
        """
        Creates an Order object from a dictionary.

        Parameters
        ----------
        data : dict
            The dictionary containing the order data.

        Returns
        -------
        Order
            The Order object created from the dictionary.
        """
        return cls(
            symbol=data.get("symbol"),
            side=data.get("side"),
            orderType=data.get("orderType"),
            timeInForce=data.get("timeInForce"),
            size=data.get("size"),
            price=data.get("price"),
            orderId=data.get("orderId"),
            clientOrderId=data.get("clientOrderId"),
        )


class Orders:
    """
    A class to manage a collection of Order objects.

    Attributes
    ----------
    _orders_ : Dict[str, Order]
        A dictionary to store orders with orderId as the key.
    """

    def __init__(self) -> None:
        self._orders_: Dict[str, Order] = {}

    def reset(self) -> None:
        """
        Resets the collection, removing all orders.
        """
        self._orders_.clear()

    def recordable(self) -> List[Dict]:
        """
        Unwraps the internal structures into widely-used Python structures
        for easy recordability (databases, logging, debugging etc). 

        Returns
        -------
        List[Dict]
            A list of Order objects.
        """
        return [order.to_dict() for order in self._orders_.values()]
    
    def add_single(self, order: Order) -> None:
        """
        Adds a single order to the collection.

        OrderId is preferred as a key over ClientOrderId.

        Parameters
        ----------
        order : Order
            The order to add to the collection.
        """
        self._orders_.update({order.orderId: order})

    def add_many(self, orders: List[Order]) -> None:
        """
        Adds multiple orders to the collection.

        Parameters
        ----------
        orders : List[Order]
            A list of orders to add to the collection.
        """
        for order in orders:
            self.add_single(order)

    def remove_single(self, order: Order) -> None:
        """
        Removes a single order from the collection.

        Parameters
        ----------
        order : Order
            The order to remove from the collection.
        """
        self._orders_.pop(order.orderId)

    def __getitem__(self, idx: str) -> Order:
        return self._orders_.get(idx, Order())
    
    def __len__(self) -> int:
        return len(self._orders_)
    
    def __repr__(self) -> str:
        return f"Orders({self._orders_})"
    
