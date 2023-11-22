
import asyncio
import yaml


class StrategyParameters:

    PARAMETER_FILE_DIRECTORY = ""

    def __init__(self, param_dir: str) -> None:
        self.param_dir = param_dir
        
        if not len(self.param_dir):
            raise AttributeError("Missing parameter file path!")

        self.load_initial_settings()


    def load_settings(self, settings):
        self.symbols = list(settings["symbols"])

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


    def load_initial_settings(self):
        with open(self.param_dir, "r") as f:
            settings = yaml.safe_load(f)
            self.load_settings(settings)


    async def refresh_settings(self):
        while True:
            await asyncio.sleep(60)
            with open(self.param_dir, "r") as f:
                settings = yaml.safe_load(f)
                self.load_settings(settings)
    