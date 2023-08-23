
from src.sharedstate import SharedState


class BybitOrderHandler:


    def __init__(self, sharedstate: SharedState, data) -> None:
        self.ss = sharedstate
        self.data = data
    

    def process(self):

        for order in self.data:
            
            try:
                id = order['orderId']
                status = order['orderStatus']

                # Remove the order if filled \
                if status == 'Filled':
                    self.ss.current_orders.pop(id)

                # If new, the order info to the dict \
                elif status == 'New':
                    
                    modified_order = {} 
                    
                    modified_order['price'] = order['price']
                    modified_order['qty'] = order['qty']
                    modified_order['side'] = order['side']

                    self.ss.current_orders[id] = modified_order

            except KeyError:
                pass
