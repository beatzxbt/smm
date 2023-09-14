
from decimal import Decimal


def round_step_size(quantity: float, step_size: float) -> float:
    """
    Originally from binance.helpers.round_step_size
    
    Rounds a float to a given step size
    """

    quantity = Decimal(str(quantity))
    return float(quantity - quantity % Decimal(str(step_size)))
