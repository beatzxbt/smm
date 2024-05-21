class BaseStrNumConverter:
    DEFAULT_UNKNOWN_STR = "UNKNOWN"
    DEFAULT_UNKNOWN_NUM = -1.0

    num_to_str = {}
    str_to_num = {}
    
    @classmethod
    def to_str(cls, value: float) -> str:
        return cls.num_to_str.get(value, cls.DEFAULT_UNKNOWN_STR)

    @classmethod
    def to_num(cls, name: str) -> float:
        return cls.str_to_num.get(name, cls.DEFAULT_UNKNOWN_NUM)