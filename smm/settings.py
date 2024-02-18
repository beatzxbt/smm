from frameworks.config.custom_parameters import CustomParameters
from typing import Dict, List


class SmmParameters(CustomParameters):
    primary_exchange: List[str]
    pairs: List[List[str]]
    parameters: Dict

    def process_parameters(self, settings: Dict) -> None:
        self.primary_exchange = str(settings["primary_exchange"])
        self.pairs = list(settings["symbols"])
        self.parameters = dict(settings["parameters"])