class StrNumConverter:
    """
    A base class for converting between numerical values and their string representations.

    This class provides methods to convert a numerical value to its string representation
    and vice versa. If the value or name is not found, it returns default unknown values.
    """

    DEFAULT_UNKNOWN_STR = "UNKNOWN"
    DEFAULT_UNKNOWN_NUM = -1.0

    num_to_str = {}
    str_to_num = {}

    @classmethod
    def to_str(cls, value: float) -> str:
        """
        Converts a numerical value to its string representation.

        Parameters
        ----------
        value : float
            The numerical value to convert.

        Returns
        -------
        str
            The string representation of the numerical value.
            If the value is not found, returns "UNKNOWN".
        """
        return cls.num_to_str.get(value, cls.DEFAULT_UNKNOWN_STR)

    @classmethod
    def to_num(cls, name: str) -> float:
        """
        Converts a string name to its numerical representation.

        Parameters
        ----------
        name : str
            The string name to convert.

        Returns
        -------
        float
            The numerical representation of the string name.
            If the name is not found, returns -1.0.
        """
        return cls.str_to_num.get(name, cls.DEFAULT_UNKNOWN_NUM)


class SideConverter(StrNumConverter):
    """
    A converter class for trade sides, converting between string and numerical representations.

    Parameters
    ----------
    BUY : str
        The string representation for the "buy" side.

    SELL : str
        The string representation for the "sell" side.

    Attributes
    ----------
    str_to_num : dict
        A dictionary mapping string representations to numerical values.

    num_to_str : dict
        A dictionary mapping numerical values to string representations.
    """

    def __init__(self, BUY: str, SELL: str) -> None:
        self.str_to_num = {f"{BUY}": 0, f"{SELL}": 1}
        self.num_to_str = {v: k for k, v in self.str_to_num.items()}


class OrderTypeConverter(StrNumConverter):
    """
    A converter class for order types, converting between string and numerical representations.

    Parameters
    ----------
    LIMIT : str
        The string representation for the "limit" order type.

    MARKET : str
        The string representation for the "market" order type.

    STOP_LIMIT : str, optional
        The string representation for the "stop limit" order type.

    TAKE_PROFIT_LIMIT : str, optional
        The string representation for the "take profit limit" order type.

    Attributes
    ----------
    str_to_num : dict
        A dictionary mapping string representations to numerical values.

    num_to_str : dict
        A dictionary mapping numerical values to string representations.
    """

    def __init__(self, LIMIT: str, MARKET: str, STOP_LIMIT: str=None, TAKE_PROFIT_LIMIT: str=None) -> None:
        self.str_to_num = {f"{LIMIT}": 0, f"{MARKET}": 1, f"{STOP_LIMIT}": 2, f"{TAKE_PROFIT_LIMIT}": 3}
        self.num_to_str = {v: k for k, v in self.str_to_num.items()}


class TimeInForceConverter(StrNumConverter):
    """
    A converter class for time-in-force policies, converting between string and numerical representations.

    Parameters
    ----------
    GTC : str
        The string representation for "good till canceled".

    FOK : str
        The string representation for "fill or kill".

    POST_ONLY : str
        The string representation for "post only".

    Attributes
    ----------
    str_to_num : dict
        A dictionary mapping string representations to numerical values.
        
    num_to_str : dict
        A dictionary mapping numerical values to string representations.
    """

    def __init__(self, GTC: str, FOK: str, POST_ONLY: str) -> None:
        self.str_to_num = {f"{GTC}": 0, f"{FOK}": 1, f"{POST_ONLY}": 2}
        self.num_to_str = {v: k for k, v in self.str_to_num.items()}