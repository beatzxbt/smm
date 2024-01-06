import yaml
import asyncio
from typing import Dict

class CustomParameters:

    def __init__(self, param_dir: str) -> None:
        if not param_dir:
            raise ValueError("Missing parameter file path!")

        self.param_dir = param_dir
        self._load_initial_parameters_()

    def load_parameters(self, parameters):
        """Process raw parameters dict from .yaml file and map to sharedstate"""
        raise NotImplementedError("Derived classes should implement this method")

    def _load_initial_parameters_(self) -> Dict:
        """Load parameters from .yaml file and process them"""
        with open(self.param_dir, "r") as f:
            parameters = yaml.safe_load(f)
            self.load_parameters(parameters)

    async def refresh_parameters(self) -> Dict:
        """Refresh parameters every 60s"""
        while True:
            await asyncio.sleep(60)
            self._load_initial_parameters_()
