from typing import Dict


class Side:
    BUY = 0.0
    SELL = 1.0


class OrderType:
    LIMIT = 0.0
    MARKET = 1.0
    STOP_LIMIT = 2.0
    TAKE_PROFIT_LIMIT = 3.0


class TimeInForce:
    GTC = 0.0
    FOK = 1.0
    POST_ONLY = 2.0


class PositionDirection:
    LONG = 0.0
    SHORT = 1.0


class StrNumConverter:
    """
    A base class for converting between numerical values and their string representations.

    This class provides methods to convert a numerical value to its string representation
    and vice versa. If the value or name is not found, it returns default unknown values.
    """

    DEFAULT_UNKNOWN_STR = "UNKNOWN"
    DEFAULT_UNKNOWN_NUM = -1.0

    def __init__(self, str_to_num: Dict[str, float]) -> None:
        self.str_to_num: Dict[str, float] = str_to_num
        self.num_to_str: Dict[float, str] = {v: k for k, v in self.str_to_num.items()}

    def to_str(self, value: float) -> str:
        """
        Converts a numerical value to its str representation.

        Parameters
        ----------
        value : float
            The numerical value to convert.

        Returns
        -------
        str
            The str representation of the numerical value.
            If the value is not found, returns "UNKNOWN".
        """
        return self.num_to_str.get(value, self.DEFAULT_UNKNOWN_STR)

    def to_num(self, name: str) -> float:
        """
        Converts a str name to its numerical representation.

        Parameters
        ----------
        name : str
            The str name to convert.

        Returns
        -------
        float
            The numerical representation of the str name.
            If the name is not found, returns -1.0.
        """
        return self.str_to_num.get(name, self.DEFAULT_UNKNOWN_NUM)


class SideConverter(StrNumConverter):
    """
    A converter class for trade sides, converting between string and numerical representations.

    Attributes
    ----------
    str_to_num : Dict
        A dictionary mapping string representations to numerical values.

    num_to_str : Dict
        A dictionary mapping numerical values to string representations.

    Parameters
    ----------
    BUY : str
        The string representation for the "buy" side.
    
    SELL : str
        The string representation for the "sell" side.
    """

    def __init__(self, BUY: str, SELL: str) -> None:
        super().__init__(str_to_int={f"{BUY}": Side.BUY, f"{SELL}": Side.SELL})


class OrderTypeConverter(StrNumConverter):
    """
    A converter class for order types, converting between string and numerical representations.

    Attributes
    ----------
    str_to_num : Dict
        A dictionary mapping string representations to numerical values.

    num_to_str : Dict
        A dictionary mapping numerical values to string representations.

    Parameters
    ----------
    LIMIT : str
        The string representation for the "limit" order type.

    MARKET : str
        The string representation for the "market" order type.

    STOP_LIMIT : str, optional
        The string representation for the "stop limit" order type. Default is None.

    TAKE_PROFIT_LIMIT : str, optional
        The string representation for the "take profit limit" order type. Default is None.
    """

    def __init__(
        self,
        LIMIT: str,
        MARKET: str,
        STOP_LIMIT: str = None,
        TAKE_PROFIT_LIMIT: str = None,
    ) -> None:
        super().__init__(
            str_to_int={
                f"{LIMIT}": OrderType.LIMIT,
                f"{MARKET}": OrderType.MARKET,
                f"{STOP_LIMIT}": OrderType.STOP_LIMIT,
                f"{TAKE_PROFIT_LIMIT}": OrderType.TAKE_PROFIT_LIMIT,
            }
        )


class TimeInForceConverter(StrNumConverter):
    """
    A converter class for time-in-force policies, converting between string and numerical representations.

    Attributes
    ----------
    str_to_num : Dict
        A dictionary mapping string representations to numerical values.

    num_to_str : Dict
        A dictionary mapping numerical values to string representations.

    Parameters
    ----------
    GTC : str
        The string representation for "good till canceled".

    FOK : str
        The string representation for "fill or kill".

    POST_ONLY : str
        The string representation for "post only".
    """

    def __init__(self, GTC: str, FOK: str, POST_ONLY: str) -> None:
        super().__init__(
            str_to_int={
                f"{GTC}": TimeInForce.GTC,
                f"{FOK}": TimeInForce.FOK,
                f"{POST_ONLY}": TimeInForce.POST_ONLY,
            }
        )


class PositionDirectionConverter(StrNumConverter):
    """
    A converter class for position directions, converting between string and numerical representations.

    Attributes
    ----------
    str_to_num : Dict
        A dictionary mapping string representations to numerical values.

    num_to_str : Dict
        A dictionary mapping numerical values to string representations.

    Parameters
    ----------
    LONG : str
        The string representation for the "long" position direction.

    SHORT : str
        The string representation for the "short" position direction.
    """

    def __init__(self, LONG: str, SHORT: str) -> None:
        super().__init__(
            str_to_int={
                f"{LONG}": PositionDirection.LONG,
                f"{SHORT}": PositionDirection.SHORT,
            }
        )
