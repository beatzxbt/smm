from typing import Dict

def bba_handler(recv: Dict, market_data: Dict):
    market_data["bba"][0, 0] = float(recv["bids"][0][0])
    market_data["bba"][0, 1] = float(recv["bids"][0][1])
    market_data["bba"][1, 0] = float(recv["asks"][0][0])
    market_data["bba"][1, 1] = float(recv["asks"][0][1])