from typing import Dict

def orderbook_handler(recv: Dict, market_data: Dict):
    market_data["orderbook"].update(
        asks=recv["asks"],
        bids=recv["bids"]
    ) 