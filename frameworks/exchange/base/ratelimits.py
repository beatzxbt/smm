from typing import Dict, Tuple, Union

class Ratelimit:
    def __init__(self) -> None:
        self.rate_limits = {}

    def _initialize_ratelimit_map_(self, maps: Tuple[str, int]) -> Dict:
        raise NotImplementedError("Must be implimented in inherited class!")

    def update(self, endpoint: str, reset_ts: Union[float, int]) -> Dict:
        self.rate_limits[endpoint]["remining"] -= 1
        if self.rate_limits[endpoint]["reset"] < reset_ts:
            self.rate_limits[endpoint]["remining"] = self.rate_limits[endpoint]["max"]
