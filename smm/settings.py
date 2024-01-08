from frameworks.config.custom_parameters import CustomParameters
from frameworks.sharedstate import SharedState
from typing import Dict

class SmmParameters(CustomParameters):

    def __init__(self, ss: SharedState, param_dir: str) -> None:
        self.ss = ss
        super().__init__(param_dir)
        
    def load_parameters(self, settings: Dict):
        self.pairs = list(settings["symbols"])

        self.bollinger_band_length = int(settings["bollinger_band_length"])
        self.bollinger_band_std = int(settings["bollinger_band_std"])

        self.price_offset = float(settings["price_offset"])
        self.size_offset = float(settings["size_offset"])
        self.volatility_offset = float(settings["volatility_offset"])
        
        self.minimum_spread = float(settings["minimum_spread"])
        self.num_orders = int(settings["number_of_orders"])
        self.min_order_size = float(settings["min_order_size"])
        self.max_order_size = float(settings["max_order_size"])
        self.max_inventory_delta = float(settings["max_inventory_delta"])
    