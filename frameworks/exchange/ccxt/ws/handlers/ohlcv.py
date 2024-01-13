from typing import Dict

def ohlcv_handler(recv: Dict, market_data: Dict):
    market_data["ohlcv"].update(
        asks=recv["asks"],
        bids=recv["bids"]
    ) 