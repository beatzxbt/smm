from enum import Enum

class BaseOrderTypes:
    class OrderType(Enum):
        """ 
        Placeholder enum class to be overwritten in subclass

        There must be at least market/limit type placeholders

        As a default, here are the following formats for implementations:
        
        ------------------------------------------------------------
        LIMIT = 0
        MARKET = 1
        STOP_LOSS = 2
        STOP_LOSS_LIMIT = 3
        TAKE_PROFIT = 4
        TAKE_PROFIT_LIMIT = 5
        ------------------------------------------------------------
        """
        pass
    
    @classmethod
    def to_type(cls, value: int) -> str:
        try:
            return cls.OrderType(value).name
        except ValueError:
            raise ValueError(f"Unknown order type value: {value}")

    @classmethod
    def to_int(cls, name: str) -> int:
        try:
            return cls.OrderType[name].value
        except KeyError:
            raise ValueError(f"Unknown order type name: {name}")
        

class BaseOrderSides:
    class OrderSide(Enum):
        """ 
        Placeholder enum class to be overwritten in subclass

        As a default, here are the following formats for implementations:
        
        ------------------------------------------------------------
        BUY = 0
        SELL = 1
        ------------------------------------------------------------
        """
        pass
    
    @classmethod
    def to_side(cls, value: int) -> str:
        try:
            return cls.OrderSide(value).name 
        except ValueError:
            raise ValueError(f"Unknown order side value: {value}")

    @classmethod
    def to_int(cls, name: str) -> int:
        try:
            return cls.OrderSide[name].value
        except KeyError:
            raise ValueError(f"Unknown order type name: {name}")