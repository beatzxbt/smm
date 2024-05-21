from frameworks.exchange.base.types import BaseStrNumConverter

class BinanceOrderSides(BaseStrNumConverter):
    str_to_num = {"BUY": 0.0, "SELL": 1.0}
    num_to_str = {v: k for k, v in str_to_num.items()}


class BinanceOrderTypes(BaseStrNumConverter):
    str_to_num = {"LIMIT": 0.0, "MARKET": 1.0, "STOP": 2.0, "TAKE_PROFIT": 3.0, "LIQUIDATION": 9.0}
    num_to_str = {v: k for k, v in str_to_num.items()}
