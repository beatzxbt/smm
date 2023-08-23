

class OrderTypesSpot:

    
    def __init__(self, symbol: str, margin: bool):
        self.symbol = symbol
        
        if margin == True:
            self.margin = 1

        if margin == False:
            self.margin = 0

    
    def limit(self, side: str, price: str, qty: str):

        payload = {
            "category": "spot",
            "symbol": self.symbol,
            "isLeverage": self.margin,
            "side": side,
            "orderType": "Limit",
            "price": price,
            "qty": qty,
            "timeInForce": "PostOnly"
        }

        return payload

    
    def market(self, side: str, qty: str):

        payload = {
            "category": "spot",
            "symbol": self.symbol,
            "isLeverage": self.margin,
            "side": side,
            "orderType": "Market",
            "qty": qty,
        }

        return payload


    def cancel(self, orderId: str):

        payload = {
            "category": "spot",
            "symbol": self.symbol,
            "orderId": orderId
        }

        return payload



class OrderTypesFutures:

    
    def __init__(self, symbol: str):
        self.symbol = symbol

    
    def limit(self, order):

        payload = {
            "category": "linear",
            "symbol": self.symbol,
            "side": str(order[0]),
            "orderType": "Limit",
            "qty": str(order[2]),
            "price": str(order[1]),
            "timeInForce": "PostOnly"
        }

        return payload

    
    def market(self, order):

        payload = {
            "category": "linear",
            "symbol": self.symbol,
            "side": str(order[0]),
            "orderType": "Market",
            "qty": str(order[1]),
        }

        return payload


    def amend(self, order):
        
        payload = {
            "category": "linear",
            "symbol": self.symbol,
            "orderId": str(order[0]),
            "qty": str(order[2]),
            "price": str( order[1])
        }

        return payload


    def cancel(self, orderId: str):

        payload = {
            "category": "linear",
            "symbol": self.symbol,
            "orderId": orderId
        }

        return payload


    def cancel_all(self):

        payload = {
            "category": "linear",
            "symbol": self.symbol
        }

        return payload


    