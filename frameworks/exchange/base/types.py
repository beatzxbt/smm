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
