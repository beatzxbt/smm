
class Inventory:
    def __init__(self, ss) -> None:
        self.ss = ss

    def position_delta(self, side: str, value: float, leverage: int) -> None:
        """
        Calculates the current position delta relative to account size
        """
        if side:
            acc_max = (self.ss.account_size * leverage) / 2.05
            value = value if side == 'Buy' else -value
            self.ss.inventory_delta = value / acc_max