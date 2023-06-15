import asyncio
import numpy as np
from src.bybit.client import HTTP_PrivateRequests
from src.utils.rounding import round_step_size


class Order:


    def __init__(self, api_key: str, api_secret: str, symbol: str):
        self.api_key = api_key
        self.api_secret = api_secret
        self.symbol = symbol
     

    async def batch_orders(self, orders: list):
        """
        Orders is a list that contain tuples | struct (side: string, price: float, qty: float)\n
        Keep in mind, rate limits are at 10 orders per sec so don't send too many!
        """

        endpoint = '/v5/order/create'

        try:
            batchOrders = []

            for order in orders:

                payload = {
                    "category": "linear",
                    "symbol": self.symbol,
                    "side": order[0],
                    "orderType": "Limit",
                    "price": order[1],
                    "qty": order[2],
                    "timeInForce": "PostOnly"
                } 
                
                _order = batchOrders.append(asyncio.create_task(
                    HTTP_PrivateRequests(self.api_key, self.api_secret, 5000).send("POST", endpoint, payload)
                    )
                )
                     
            _results = await asyncio.gather(*batchOrders)

        except Exception as e:
            # Enter error handling here \
            print(e)


    async def taker_twap(self, side: str, duration: int, num: int, qty: float, \
                            lot_size: float, randomize: bool):
        """
        {side}: Either 'Buy' or 'Sell', quite self explanatory \n
        {duration}: Total duration in seconds \n
        {num}: Number of orders executed \n
        {qty}: Total quantity executed over the duration \n
        {lot_size}: Minimum order quantity on specified contract \n

        {randomize}: Utilizes normally distributed quantity sizes to reduce detection \n
        """

        endpoint = '/v5/order/create'

        if side == 'Buy' or side == 'Sell':
            pass

        else:
            print("Side must be either 'Buy' or 'Sell'!")
            raise Exception

        interval = duration/num
        
        if randomize:
            total = 0.

            for i in range(num):
                
                remaining_qty = round_step_size(qty-total, lot_size)
                
                # Reduces risk of remaining quantity being too low to get executed \
                # Lot size multiplier can be adjusted if needed, though 5 should suffice \
                if remaining_qty < lot_size * 5:
                    
                    payload = {
                        "category": "linear",
                        "symbol": self.symbol,
                        "side": side,
                        "orderType": "Market",
                        "qty": remaining_qty
                    } 

                    _order = await HTTP_PrivateRequests(
                                self.api_key, self.api_secret, 5000
                            ).send("POST", endpoint, payload)

                    break

                else:
                    if i != num - 1:
                        order_size = np.abs(np.random.normal(qty/num, qty/num))
                        rounded_size = round_step_size(order_size, lot_size)

                        # Skip orders which are too small, they will get collected \
                        # and executed the end anyways if the nested loop ends \
                        if rounded_size < lot_size:
                            pass

                        else:
                            payload = {
                                "category": "linear",
                                "symbol": self.symbol,
                                "side": side,
                                "orderType": "Market",
                                "qty": round_step_size(order_size, lot_size)
                            } 

                            _order = await HTTP_PrivateRequests(
                                        self.api_key, self.api_secret, 5000
                                    ).send("POST", endpoint, payload)

                            total += rounded_size

                    else: 
                        payload = {
                            "category": "linear",
                            "symbol": self.symbol,
                            "side": side,
                            "orderType": "Market",
                            "qty": remaining_qty
                        } 

                        _order = await HTTP_PrivateRequests(
                                    self.api_key, self.api_secret, 5000
                                ).send("POST", endpoint, payload)

                _sleep = await asyncio.sleep(interval)
                

        else:
            # Classic TWAP, fixed size fixed intervals \
            order_size = round_step_size(qty/num, lot_size)

            if order_size < lot_size:
                print('Average size over the duration specified is too small...')
                raise Exception
            
            for i in range(num):
                
                try:
                    payload = {
                        "category": "linear",
                        "symbol": self.symbol,
                        "side": side,
                        "orderType": "Market",
                        "qty": order_size,
                    } 
                    
                    _order = await HTTP_PrivateRequests(
                                self.api_key, self.api_secret, 5000
                            ).send("POST", endpoint, payload)

                    _sleep = await asyncio.sleep(interval)

                except Exception as e:
                    # Enter error handling here \
                    print(e)


    async def cancel_all(self):
        """
        Cancels all orders for a symbol
        """

        endpoint = '/v5/order/cancel-all'

        payload = {
            "category": "linear",
            "symbol": self.symbol
        }

        try:
            _resp = await HTTP_PrivateRequests(
                        self.api_key, self.api_secret, 5000
                    ).send("POST", endpoint, payload)

        except Exception as e:
            print(e)


    async def set_leverage(self, leverage: int):
        """
        Changes leverage of the specified symbol in one-way mode
        """

        endpoint = '/v5/position/set-leverage'

        payload = {
            "category": "linear",
            "symbol": self.symbol,
            "buyLeverage": str(leverage),
            "sellLeverage": str(leverage)
        }

        try:
            _resp = await HTTP_PrivateRequests(
                        self.api_key, self.api_secret, 20000
                    ).send("POST", endpoint, payload)

        except Exception as e:
            print(e)
