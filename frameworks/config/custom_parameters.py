import yaml
import asyncio
from typing import Dict

class CustomParameters:
    def __init__(self, param_dir: str) -> None:
        if not param_dir:
            raise ValueError("Missing parameter file path!")
        self.param_dir = param_dir
        self._load_initial_parameters()

    def process_parameters(self, parameters: Dict):
        """Process raw parameters dict from .yaml file"""
        raise NotImplementedError("Derived classes should implement this method")

    def _load_initial_parameters(self) -> None:
        """Load parameters from .yaml file and process them"""
        with open(self.param_dir, "r") as f:
            parameters = yaml.safe_load(f)
        self.process_parameters(parameters)

    async def refresh_parameters(self) -> None:
        """Refresh parameters every 60s"""
        while True:
            await asyncio.sleep(60)
            self._load_initial_parameters()
