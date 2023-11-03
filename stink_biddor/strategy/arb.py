
import asyncio

from frameworks.tools.rounding import round_step_size
from frameworks.tools.logging.logger import Logger
from frameworks.exchange.bybit.post.order import BybitOrder
from frameworks.sharedstate.market import MarketDataSharedState
from frameworks.sharedstate.private import PrivateDataSharedState


class StinkBiddor:


    def __init__(
        self, 
        mdss: MarketDataSharedState, 
        pdss: PrivateDataSharedState, 
        symbol: str,
        params: list
    ) -> None:

        self.mdss = mdss
        self.pdss = pdss
        self.symbol = symbol
        self.bybit_mdss = self.mdss.bybit[self.symbol]

        self.logging = Logger()

        self.entry_bps, self.exit_bps, self.quote_size = params


    def _bid_enter(self) -> float:
        """
        Bybit midprice - defined offset 

        Returns a correctly rounded value
        """

        base_price = self.bybit_mdss["mid_price"]
        offset = self.entry_bps / 10_000

        entry_price = base_price * (1 - offset)

        return round_step_size(entry_price, self.bybit_mdss["tick_size"])


    def _ask_enter(self) -> float:
        """
        Bybit midprice + defined offset 

        Returns a correctly rounded value
        """

        base_price = self.bybit_mdss["mid_price"]
        offset = self.entry_bps / 10_000

        entry_price = base_price * (1 + offset)

        return round_step_size(entry_price, self.bybit_mdss["tick_size"])


    def _bid_exit(self) -> float:
        """
        Bybit bid entry + defined offset 

        Returns a correctly rounded value
        """

        base_price = self.bybit_mdss["mid_price"]
        offset = self.exit_bps / 10_000

        exit_price = base_price * (1 - offset)

        return round_step_size(exit_price, self.bybit_mdss["tick_size"])


    def _ask_exit(self) -> float:
        """
        Bybit ask entry + defined offset 

        Returns a correctly rounded value
        """

        base_price = self.bybit_mdss["mid_price"]
        offset = self.exit_bps / 10_000

        exit_price = base_price * (1 + offset)

        return round_step_size(exit_price, self.bybit_mdss["tick_size"])
    

    async def buy(self):
        orderId = None

        try: 
            # Initial order
            price = self._bid_enter()
            exit_price = self._bid_exit()
            qty = self.quote_size
            init_order_params = ('Buy', price, qty)
            init_order = await BybitOrder(self.pdss, self.symbol).order_limit(init_order_params, tp=exit_price)
            
            # If the initial order fails (cant be handled), raise Execption 
            if init_order is None:
                raise Exception 

            # Will be used to cancel order
            orderId = init_order['return']['orderId']

            while True:
                # Chase new bid, if any, every second
                await asyncio.sleep(1)

                # Order filled, break loop
                if orderId not in self.pdss.bybit["Data"]["current_orders"]:
                    return

                new_price = self._bid_enter()

                # If entry price changes, replace order
                if price != new_price:
                    price = new_price
                    new_order_params = ('Buy', price, qty)
                    exit_price = self._bid_exit()

                    result = await asyncio.gather(
                        asyncio.create_task(BybitOrder(self.pdss, self.symbol).order_limit(new_order_params, tp=exit_price)),
                        asyncio.create_task(BybitOrder(self.pdss, self.symbol).cancel(orderId))
                    )

                    orderId = result[0]['return']['orderId']


        # If task is cancelled, cancel the order and break loop
        except asyncio.CancelledError:
            if orderId is not None:
                await BybitOrder(self.pdss, self.symbol).cancel(orderId)
                
            return 

        # Handle any other potential exceptions
        except Exception as e:
            self.logging.error(e)
            
            if orderId is not None:
                await BybitOrder(self.pdss, self.symbol).cancel(orderId)
                
            return 


    async def sell(self):
        orderId = None

        try: 
            # Initial order
            price = self._ask_enter()
            exit_price = self._ask_exit()
            qty = self.quote_size
            init_order_params = ('Sell', price, qty)
            init_order = await BybitOrder(self.pdss, self.symbol).order_limit(init_order_params, tp=exit_price)
            
            # If the initial order fails (cant be handled), raise Execption 
            if init_order is None:
                raise Exception 

            # Will be used to cancel order
            orderId = init_order['return']['orderId']

            while True:
                # Chase new bid, if any, every second
                await asyncio.sleep(1)

                # Order filled, break loop
                if orderId not in self.pdss.bybit["Data"]["current_orders"]:
                    return
                    
                # New price
                new_price = self._ask_enter()

                # If entry price changes, amend
                if price != new_price:
                    price = new_price
                    new_order_params = ('Sell', price, qty)
                    exit_price = self._ask_exit()

                    result = await asyncio.gather(
                        asyncio.create_task(BybitOrder(self.pdss, self.symbol).order_limit(new_order_params, tp=exit_price)),
                        asyncio.create_task(BybitOrder(self.pdss, self.symbol).cancel(orderId))
                    )

                    orderId = result[0]['return']['orderId']

        # If task is cancelled, cancel the order
        except asyncio.CancelledError:
            if orderId is not None:
                await BybitOrder(self.pdss, self.symbol).cancel(orderId)
                
            return 

        # Handle any other potential exceptions
        except Exception as e:
            self.logging.error(e)

            if orderId is not None:
                await BybitOrder(self.pdss, self.symbol).cancel(orderId)
                
            return 
