import json


class BybitTickerHandler:


    def __init__(self, sharedstate, data: json) -> None:
        self.ss = sharedstate
        self.data = data

    
    def process(self):
        
        if 'markPrice' in self.data:

            mark_price = float(self.data['markPrice'])

            self.ss.bybit_mark_price = mark_price