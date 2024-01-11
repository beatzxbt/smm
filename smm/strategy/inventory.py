
class InventoryTools:
    
    def __init__(self, max_position: float):
        self.max_position = max_position

    def position_to_delta(self, position: float) -> float:
        """Converts a position to the account's delta"""
        return position/self.max_position

    def delta_to_position(self, delta) -> float:
        """Converts a delta to a position"""
        return delta * self.max_position
