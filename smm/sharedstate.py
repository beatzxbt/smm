import os
from typing import Dict

from frameworks.sharedstate import SharedState


class SmmSharedState(SharedState):
    required_keys = {"max_position", "total_orders"}

    def __init__(self) -> None:
        super().__init__()

    def set_parameters_path(self) -> str:
        return os.path.dirname(os.path.realpath(__file__)) + "/parameters.yaml"

    def process_parameters(self, settings: Dict, reload: bool) -> None:
        self.parameters: Dict = settings["parameters"]

        if not reload:
            self.load_exchange(settings["exchange"])
            self.symbol: str = settings["symbol"]
            self.quote_generator: str = settings["quote_generator"]

        if self.required_keys <= self.parameters.keys():
            for key in self.required_keys:
                if key in self.parameters:
                    continue

                self.logging.error(f"Missing {key} in params, this is required!")
