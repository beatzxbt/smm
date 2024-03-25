import os
from typing import Dict
from frameworks.sharedstate import SharedState


class SmmSharedState(SharedState):
    def set_parameters_path(self) -> str:
        return os.path.dirname(os.path.realpath(__file__)) + "/../parameters.yaml"  
    
    def process_parameters(self, settings: Dict, reload: bool) -> None:
        if not reload:
            self.exchange = settings["exchange"]
            self.symbol = settings["symbol"]
            self.quote_generator = settings["quote_generator"]

        self.parameters = settings["parameters"]

    def __init__(self) -> None:
        super().__init__()