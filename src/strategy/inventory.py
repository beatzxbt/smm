

class Inventory:
    

    def __init__(self, sharedstate) -> None:
        self.ss = sharedstate


    def position_delta(self, side: str, value: float, leverage: int) -> None:
        """
        Calculates the current position delta relative to account size
        """
        
        try:
            if side:
                acc_max = (self.ss.account_size * leverage) / 2.05

                if side == 'Buy':
                    self.ss.inventory_delta = value / acc_max

                elif side == 'Sell':
                    self.ss.inventory_delta = -value / acc_max

        except Exception as e:
            print(e)
            print(side, value, leverage)



