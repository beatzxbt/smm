

class BaseEndpoints:


    def mainnet1():
        return "https://api.bybit.com"


    def mainnet2():
        return "https://api.bytick.com"



class MarketEndpoints:


    def __init__(self, category: str, symbol: str) -> None:
        self.category = category
        self.symbol = symbol


    def klines(self, interval):
        category = f"category={self.category}"
        symbol = f"&symbol={self.symbol}"
        inter = f"&interval={interval}"
        
        return f"/v5/market/kline?{category}{symbol}{inter}"

    