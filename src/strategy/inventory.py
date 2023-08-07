

class Inventory:
    

    def __init__(self, sharedstate) -> None:
        self.ss = sharedstate


    def calculate_delta(self, data) -> float:
        """
        Calculates the current position delta relative to account size
        """
        
        for position_data in data:

            side = position_data['side']

            if side == '':
                continue

            value = float(position_data['positionValue'])
            lev = float(position_data['leverage'])

            acc_max = (self.ss.account_size * lev) / 2

            if side == 'Buy':
                self.ss.inventory_delta = value / acc_max

            elif side == 'Sell':
                self.ss.inventory_delta = -value / acc_max


