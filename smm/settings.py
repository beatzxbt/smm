from typing import Dict
from frameworks.config.custom_parameters import CustomParameters


class SmmParameters(CustomParameters):

    def process_parameters(self, settings: Dict) -> None:
        self.primary_exchange = str(settings["primary_exchange"])
        self.pairs = list(settings["symbols"])
        self.parameters = str(settings["parameters"])
        