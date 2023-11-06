import yaml
import asyncio

class CustomParameters:

    def __init__(self, param_dir: str) -> None:
        self.param_dir = param_dir
        if not len(self.param_dir):
            raise AttributeError("Missing parameter file path!")

        self.load_initial_settings()

    def load_settings(self, settings):
        raise NotImplementedError("Derived classes should implement this method")

    def load_initial_settings(self):
        with open(self.param_dir, "r") as f:
            settings = yaml.safe_load(f)
            self.load_settings(settings)
    
    async def refresh_settings(self):
        while True:
            await asyncio.sleep(60)
            self.load_initial_settings()