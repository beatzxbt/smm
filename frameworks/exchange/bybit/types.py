from frameworks.exchange.base.types import BaseStrNumConverter

class BybitOrderSides(BaseStrNumConverter):
    str_to_num = {"Buy": 0.0, "Sell": 1.0}
    num_to_str = {v: k for k, v in str_to_num.items()}


class BybitOrderTypes(BaseStrNumConverter):
    str_to_num = {"Limit": 0.0, "Market": 1.0, "StopLoss": 2.0, "TakeProfit": 3.0}
    num_to_str = {v: k for k, v in str_to_num.items()}