from typing import Dict, Union

class Position:
    def __init__(
        self,
        symbol: str = None,
        side: float = None,
        price: float = None,
        size: float = None,
        uPnl: float = None,
    ) -> None:
        self._symbol = symbol
        self._side = side
        self._price = price
        self._size = size
        self._uPnl = uPnl

    @property
    def symbol(self) -> str:
        return self._symbol

    @property
    def side(self) -> float:
        return self._side

    @property
    def price(self) -> float:
        return self._price

    @property
    def size(self) -> float:
        return self._size

    @property
    def uPnl(self) -> float:
        return self._uPnl

    @property
    def is_empty(self) -> bool:
        return isinstance(self._size, float) and self._size == 0.0

    @property
    def in_profit(self) -> bool:
        return isinstance(self._uPnl, float) and self._uPnl > 0.0

    def __bool__(self) -> bool:
        return any(
            attr is not None
            for attr in [self._symbol, self._side, self._price, self._size, self._uPnl]
        )

    def __repr__(self) -> str:
        return (
            f"Position(symbol={self.symbol}, side={self.side}, price={self.price}, "
            f"size={self.size}, uPnl={self.uPnl})"
        )

    def reset(self) -> None:
        """
        Reset all attributes of the Position object.
        """
        self._symbol = None
        self._side = None
        self._price = None
        self._size = None
        self._uPnl = None

    def recordable(self) -> Dict[str, Union[str, float]]:
        """
        Unwraps the internal structures into widely-used Python structures
        for easy recordability (databases, logging, debugging etc). 

        Returns
        -------
        Dict
            A dict containing the current state of the orderbook.
        """
        return {
            "symbol": self.symbol,
            "side": self.side,
            "price": self.price,
            "size": self.size,
            "uPnl": self.uPnl,
        }

    def update(
        self,
        symbol: str = None,
        side: float = None,
        price: float = None,
        size: float = None,
        uPnl: float = None,
    ) -> None:
        """
        Updates the attributes of the Position object with the provided values.

        Parameters
        ----------
        symbol : str, optional
            The symbol to update.

        side : float, optional
            The side to update.

        price : float, optional
            The price to update.

        size : float, optional
            The size to update.

        uPnl : float, optional
            The unrealized PnL to update.

        """
        if symbol is not None:
            self._symbol = symbol

        if side is not None:
            self._side = side

        if price is not None:
            self._price = price

        if size is not None:
            self._size = size

        if uPnl is not None:
            self._uPnl = uPnl
