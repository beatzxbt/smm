from typing import Dict, List, Tuple, Optional, Union, _T

class RateLimitManager:

    def __init__(self, rl: Dict, endpoint_map: Dict) -> None:
        self.rl = rl # NOTE: Pointer to rate limit dict in ss
        self.endpoint_map = endpoint_map
        self.update_map = None
    
    def initialize(self):
        # TODO: Must be initialized externally...
        self.update_map = {
            "max": "X-Bapi-Limit",
            "remaining": "X-Bapi-Limit-Status",
            "reset": "X-Bapi-Limit-Reset-Timestamp"
        }

    def update(self, endpoint: str, payload: dict) -> None:
        tag = self.endpoint_map.get(endpoint)
        self.rl[tag]["remining"] -= 1
        self.rl[tag]["reset"]