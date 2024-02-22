
class Inventory:
    """
    Manages inventory calculations for trading positions, including the calculation
    of position delta relative to the account size and leverage.

    Attributes
    ----------
    ss : SharedState
        An instance of SharedState containing shared application data.

    Methods
    -------
    position_delta(side: str, value: float, leverage: int) -> None:
        Calculates and updates the current position delta relative to the account size,
        taking into account the trade side, position value, and leverage.
    """

    def __init__(self, ss) -> None:
        """
        Initializes the Inventory object with shared application state.

        Parameters
        ----------
        ss : SharedState
            An instance of SharedState containing shared application data.
        """
        self.ss = ss

    def position_delta(self, side: str, value: float, leverage: int) -> None:
        """
        Updates the shared state with the current position delta, a measure of the
        position size relative to what is maximally allowed by the account size and leverage.

        Parameters
        ----------
        side : str
            The side of the position, either 'Buy' or 'Sell'.
        value : float
            The value of the position.
        leverage : int
            The leverage applied to the position.

        Returns
        -------
        None
        """
        if side:
            # Calculate the maximum account value adjusted for leverage and a scaling factor.
            acc_max = (self.ss.account_size * leverage) / 2.05

            # Adjust the value based on the side of the position.
            value = value if side == 'Buy' else -value

            # Update the inventory delta in shared state.
            self.ss.inventory_delta = value / acc_max