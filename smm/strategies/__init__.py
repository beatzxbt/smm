from .base.strategy import BaseStrategy as BaseStrategy
from .plain.strategy import PlainStrategy as PlainStrategy
from .stinky.strategy import StinkyStrategy as StinkyStrategy

def load_strategy(name: int) -> BaseStrategy:
    match name:
        case 0:
            return PlainStrategy
        case 1:
            return StinkyStrategy
        case _:
            raise ValueError(f"Strategy {name} not found")

__all__ = ["BaseStrategy", "PlainStrategy", "StinkyStrategy"]