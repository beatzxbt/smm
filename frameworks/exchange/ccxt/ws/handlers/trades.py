from typing import Dict

def trades_handler(recv: Dict, market_data: Dict):
    market_data["trades"].update(
        asks=recv["asks"],
        bids=recv["bids"]
    ) 