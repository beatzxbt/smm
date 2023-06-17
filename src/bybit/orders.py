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
        Orders is a list that contain tuples | struct (side: string, price: float, qty: float) \n
        For optimal order submission, list should be in order of what needs to be sent first \n
        """
        
        batch_endpoint = '/unified/v3/private/order/create-batch'
        # batch_max_sec = 2

        singles_endpoint = '/v5/order/create'
        # singles_max_sec = 10
        
        n = len(orders)
        orders_submitted = 0
        
        if n > 26:
            # This will send over a longer time, as ~26 orders a second hits rate limits for VIP0 \
            # True limit is 30 but this provides a little room for other potential API requests \
            # ABOVE 26 ORDERS STILL NEEDS TO BE IMPLEMENTED! #
            try:
                tasks = []

                # These will send 6 singles, near BBA first \
                for order in orders[:6]:

                    payload = {
                        "category": "linear",
                        "symbol": self.symbol,
                        "side": order[0],
                        "orderType": "Limit",
                        "price": order[1],
                        "qty": order[2],
                        "timeInForce": "PostOnly"
                    } 

                    _order = tasks.append(asyncio.create_task(
                        HTTP_PrivateRequests(self.api_key, self.api_secret, 5000).send("POST", singles_endpoint, payload)
                        )
                    )
                
                # These will send 20 in batches, still closest to BBA first \
                for i in range(2):
                    
                    singles_local = []

                    for order in orders[4+(10*i):4+(10*(i+1))]:

                        singles_local.append({
                            "category": "linear",
                            "symbol": self.symbol,
                            "side": order[0],
                            "orderType": "Limit",
                            "price": order[1],
                            "qty": order[2],
                            "timeInForce": "PostOnly"
                        })
                    
                    payload = {"category": "linear", "request": singles_local}

                    _order = tasks.append(asyncio.create_task(
                        HTTP_PrivateRequests(self.api_key, self.api_secret, 5000).send("POST", batch_endpoint, payload)
                    ))

                _batchresult = await asyncio.gather(*tasks)
            
            except Exception as e:
                print(e)

            pass

        else:
            # These will send 4 singles, near BBA first \
            try:
                singles_task = []

                for order in orders[:4]:

                    payload = {
                        "category": "linear",
                        "symbol": self.symbol,
                        "side": order[0],
                        "orderType": "Limit",
                        "price": order[1],
                        "qty": order[2],
                        "timeInForce": "PostOnly"
                    } 

                    _order = singles_task.append(asyncio.create_task(
                        HTTP_PrivateRequests(self.api_key, self.api_secret, 5000).send("POST", singles_endpoint, payload)
                        )
                    )

                    orders_submitted += 1
                
                _singlesresult = await asyncio.gather(*singles_task)
            
            except Exception as e:
                print(e)


            # If there are orders remaining, send them through batch orders \
            if n - orders_submitted > 0:
                
                try:
                    batches_to_send = int(np.ceil((n-orders_submitted)/10))
                    batches_task = []

                    for i in range(batches_to_send):
                        
                        singles_local = []

                        for order in orders[4+(10*i):4+(10*(i+1))]:

                            singles_local.append({
                                "category": "linear",
                                "symbol": self.symbol,
                                "side": order[0],
                                "orderType": "Limit",
                                "price": order[1],
                                "qty": order[2],
                                "timeInForce": "PostOnly"
                            })

                            orders_submitted += 1
                        
                        payload = {"category": "linear", "request": singles_local}

                        _order = batches_task.append(asyncio.create_task(
                            HTTP_PrivateRequests(self.api_key, self.api_secret, 5000).send("POST", batch_endpoint, payload)
                        ))

                    _batchresult = await asyncio.gather(*batches_task)

                except Exception as e:
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
