

class Inventory:
    

    def __init__(self, sharedstate) -> None:
        self.ss = sharedstate


    def calculate_delta(self) -> float:
        """
        Calculates the current position delta relative to account size
        """

        if len(self.ss.position_feed) == 0:
            pass

        else:
            side = self.ss.position_feed['side']
            size = float(self.ss.position_feed['size'])

            if side == 'Buy':
                self.ss.inventory_delta += size

            elif side == 'Sell':
                self.ss.inventory_delta -= size

            else:
                self.ss.inventory_delta = float()

            self.ss.position_feed = self.ss.position_feed[-1]
