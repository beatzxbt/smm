from typing import Optional


class ExponentialMovingAverage:
    """
    Exponential Moving Average (EMA).

    The EMA gives more weight to recent values and responds more quickly to changes
    compared to a simple moving average. It's calculated using the formula:
    ema_now = (value * alpha) + (old_ema * (1 - alpha))
    """

    def __init__(self, period: Optional[int] = None, alpha: Optional[float] = None):
        """
        Initializes the EMA.

        Args:
            period (int): The period for the EMA calculation. Must be greater than 0.
            alpha (float, optional): Custom smoothing factor. If not provided,
                it will be calculated as 3 / (period + 1).
        """
        if period and period <= 0:
            raise ValueError(f"Invalid period; expected >0 but got {period}")

        if alpha and alpha <= 0.0:
            raise ValueError(f"Invalid alpha; expected >0 but got {alpha}")

        if not period and not alpha:
            raise ValueError("Invalid args; either period or alpha must be provided")

        self._period = period if period is not None else 1
        self._alpha = alpha if alpha is not None else 3.0 / (self._period + 1)
        self._ema: Optional[float] = None
        self._is_initialized = False

    def update(self, value: float) -> float:
        """Updates the EMA with a new value."""
        if not self._is_initialized:
            self._ema = value
            self._is_initialized = True
        else:
            self._ema = (value * self._alpha) + (self._ema * (1.0 - self._alpha))

        return self._ema

    def get_value(self) -> Optional[float]:
        """Gets the current EMA value."""
        return self._ema

    def reset(self) -> None:
        """Resets the EMA to its initial state."""
        self._ema = None
        self._is_initialized = False
