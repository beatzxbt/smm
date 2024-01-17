from typing import Dict
from frameworks.config.custom_parameters import CustomParameters

class StinkBiddorParameters(CustomParameters):
    def process_parameters(self, settings: Dict) -> None:
        self.pair = list(settings["pair"])
        self.levels = str(settings["levels"])
        