import json


class BybitExecutionHandler:


    def __init__(self, sharedstate, data: json) -> None:
        self.ss = sharedstate
        self.data = data

        self.ef = self.ss.execution_feed
    

    def process(self):

        for execution in self.data:

            symbol = execution['symbol']

            if symbol == self.ss.bybit_symbol:
                
                orderId = execution['orderId']
                side = execution['side']
                price = float(execution['execPrice'])
                qty = float(execution['execQty'])

                self.ef[orderId] = {
                    'side': side, 'price': price, 'qty': qty
                }

