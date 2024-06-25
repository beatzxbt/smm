import os
from typing import Dict

from frameworks.sharedstate import SharedState


class SmmSharedState(SharedState):
    required_keys = {"max_position", "total_orders"}

    def __init__(self, debug: bool=False) -> None:
        super().__init__(debug)

    def set_parameters_path(self) -> str:
        return os.path.dirname(os.path.realpath(__file__)) + "/parameters.yaml"

    def process_parameters(self, settings: Dict, reload: bool) -> None:
        try:
            if not reload:
                self.symbol: str = settings["symbol"]
                self.quote_generator: str = settings["quote_generator"]
                self.load_exchange(settings["exchange"])

            self.parameters: Dict = settings["parameters"][self.quote_generator]

            if self.required_keys > self.parameters.keys():
                for key in self.required_keys:
                    if key in self.parameters:
                        continue

                    raise Exception(
                        f"Missing '{key}' in {self.quote_generator}'s parameters!"
                    )
                
        except Exception as e:
            raise e
