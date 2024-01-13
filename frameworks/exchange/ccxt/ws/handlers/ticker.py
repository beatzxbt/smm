from typing import Dict

def ticker_handler(recv: Dict, market_data: Dict):
    market_data["ticker"].update(
        asks=recv["asks"],
        bids=recv["bids"]
    ) 