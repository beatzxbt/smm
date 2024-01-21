from typing import Dict, Tuple, Optional, Union
from frameworks.tools.logger import ms as time_ms

class Ratelimit:
    def __init__(self) -> None:
        self.update_map = None
        self.local_count = {}

    def initialize_update_map(self, keys: Dict):
        self.update_map = {
            "max": "X-Bapi-Limit",
            "remaining": "X-Bapi-Limit-Status",
            "reset": "X-Bapi-Limit-Reset-Timestamp",
        }

    def update(self, key: str, payload: dict) -> None:
        tag = self.endpoint_map.get(endpoint)
        self.rl[tag]["remining"] -= 1
        self.rl[tag]["reset"]
