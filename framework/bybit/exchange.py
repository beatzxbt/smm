from typing import List, Tuple
from framework.base.exchange import BaseExchange
from framework.bybit.client import BybitRestTradeClient, BybitWsTradeClient
from framework.tools.logger import Logger
from framework.tools.time import time_ms

from framework.base.internal_structs import ExecutionMsg, OrderMsg, OrderbookMsg, TickerMsg, Trade, TradeMsg, PositionMsg, AccountMsg, OrderTimeInForce

RECV_WINDOW = 1000

ENDPOINT_POST_CREATE_ORDER = "https://api.bybit.com/v5/order/create"
ENDPOINT_POST_AMEND_ORDER = "https://api.bybit.com/v5/order/amend"
ENDPOINT_POST_CANCEL_ORDER = "https://api.bybit.com/v5/order/cancel"
ENDPOINT_POST_CANCEL_ALL = "https://api.bybit.com/v5/order/cancel-all"
ENDPOINT_GET_TRADES = "https://api.bybit.com/v5/market/recent-trade"
ENDPOINT_GET_ORDERBOOK = "https://api.bybit.com/v5/market/orderbook"
ENDPOINT_GET_TICKERS = "https://api.bybit.com/v5/market/tickers"
ENDPOINT_GET_ORDERS = "https://api.bybit.com/v5/order/realtime"
ENDPOINT_GET_POSITION = "https://api.bybit.com/v5/position/list"
ENDPOINT_GET_EXECUTIONS = "https://api.bybit.com/v5/execution/list"
ENDPOINT_GET_ACCOUNT = "https://api.bybit.com/v5/account/wallet-balance"
ENDPOINT_GET_INSTRUMENTS_INFO = "https://api.bybit.com/v5/market/instruments-info"

# As Bybit supports WS trade quite well, we solely use the WS client for trade operations.
# Rest clients are primarily used for GET requests, as well as acting as a backup incase 
# the WS client is not running or is having issues. 
class BybitExchange(BaseExchange):
    def __init__(self, api_key, api_secret, logger: Logger):
        """
        Initializes the OrderClient.

        Args:
            api_key (str): Bybit API key.
            api_secret (str): Bybit API secret.
            logger (Logger): Logger instance for logging.
        """
        # This allows the client to be used for unsigned requests in cases
        # where the API key and secret are not needed.
        if api_key is not None and api_secret is not None:
            _rest_client = BybitRestTradeClient(api_key, api_secret, logger)
            _ws_client = BybitWsTradeClient(api_key, api_secret, logger)
        else:
            _rest_client = None
            _ws_client = None

        super().__init__(
            logger=logger,
            rest_client=_rest_client,
            ws_client=_ws_client,
            max_cloid_length=36
        )

        self._tif_enum_to_str = {
            OrderTimeInForce.GTC: "GTC",
            OrderTimeInForce.IOC: "IOC",
            OrderTimeInForce.FOK: "FOK",
            OrderTimeInForce.PO: "PostOnly",
        }
        self._tif_str_to_enum = {v: k for k, v in self._tif_enum_to_str.items()}
        
    async def create_order(
        self, 
        symbol, 
        is_maker, 
        sz, 
        is_buy, 
        px=None, 
        tif=OrderTimeInForce.GTC, 
        reduce_only=False, 
        cloid=None
    ):
        self.ensure_running(ws_only=True)
        
        if px is not None and px < 0.0:
            raise ValueError(f"Invalid px; expected >=0.0 but got {px}")
        
        if sz is not None and sz <= 0.0:
            raise ValueError(f"Invalid sz; expected >0.0 but got {sz}")
        
        payload = {
            "category": "linear",
            "symbol": symbol,
            "side": "Buy" if is_buy else "Sell",
            "orderType": "Limit" if is_maker else "Market",
            "timeInForce": self._tif_enum_to_str[tif],
            "qty": str(sz),
            "reduceOnly": reduce_only,
        }
        
        if cloid is not None:
            payload["orderLinkId"] = cloid

        if is_maker and px is not None:
            payload["price"] = str(px)
        else:
            raise ValueError(f"Invalid px; expected for maker orders but got {px}")
        
        payload = {
            "op": "order.create",
            "header": {
                "X-BAPI-TIMESTAMP": int(time_ms()),
                "X-BAPI-RECV-WINDOW": RECV_WINDOW
            },
            "args": [payload]
        }

        response = await self._ws_client.submit(payload)
        return response

    async def amend_order(
        self,
        symbol,
        sz: float = None,
        px: float = None,
        oid = None,
        cloid = None
    ):
        """
        Amends an existing order via Bybit's Trade WS API.
        """
        self.ensure_running(ws_only=True)
        
        if not oid and not cloid:
            raise ValueError("Missing oid and/or cloid; either 'oid' or 'cloid' must be provided for an amendment")
        
        if px is not None and px < 0.0:
            raise ValueError(f"Invalid px; expected >=0.0 but got {px}")
        
        if sz is not None and sz <= 0.0:
            raise ValueError(f"Invalid sz; expected >0.0 but got {sz}")
        
        payload = {
            "category": "linear",
            "symbol": symbol,
        }

        if oid is not None:
            payload["orderId"] = oid
        elif cloid is not None:
            payload["orderLinkId"] = cloid

        if px is not None:
            payload["price"] = str(px)
        if sz is not None:
            payload["qty"] = str(sz)

        payload = {
            "op": "order.amend",
            "header": {
                "X-BAPI-TIMESTAMP": int(time_ms()),
                "X-BAPI-RECV-WINDOW": RECV_WINDOW
            },
            "args": [payload]
        }

        response = await self._ws_client.submit(payload)
        return response

    async def cancel_order(
        self,
        symbol,
        oid = None,
        cloid = None
    ):
        """
        Cancels a single open order via Bybit's Trade WS API.
        """
        self.ensure_running(ws_only=True)

        if not oid and not cloid:
            raise ValueError("Missing oid and/or cloid; either 'oid' or 'cloid' must be provided for cancellation")
        
        payload = {
            "category": "linear",
            "symbol": symbol,
        }

        if oid is not None:
            payload["orderId"] = oid
        elif cloid is not None:
            payload["orderLinkId"] = cloid

        payload = {
            "op": "order.cancel",
            "header": {
                "X-BAPI-TIMESTAMP": int(time_ms()),
                "X-BAPI-RECV-WINDOW": RECV_WINDOW
            },
            "args": [payload]
        }

        response = await self._ws_client.submit(payload)
        return response

    async def cancel_all_orders(self, symbol):
        """
        Cancels all open orders for the default symbol via REST API.

        Returns:
            dict | None: The API response as a dict if successful, or None if error.
        """
        self.ensure_running(rest_only=True)
        
        payload = {
            "category": "linear",
            "symbol": symbol,
        }
        
        response = await self._rest_client.submit(
            endpoint=ENDPOINT_POST_CANCEL_ALL, 
            payload=payload, 
            method="POST"
        )
        return response

    async def get_trades(self, symbol):
        payload = {
            "category": "linear",
            "symbol": symbol,
            "limit": 1000
        }
        
        try:
            async with self.unauth_session.get(
                url=ENDPOINT_GET_TRADES, 
                params=payload
            ) as response:
                resp_text = await response.text()
                resp_json = self._json_decoder.decode(resp_text)
                
                if resp_json["retCode"] == 0:
                    trades: list[Trade] = []

                    # The trades are returned in reverse chronological order, so we 
                    # reverse the list to get the correct order.
                    for trade in resp_json["result"]["list"][::-1]:
                        trades.append(Trade(
                            time=float(trade["time"]),
                            px=float(trade["price"]),
                            is_buy=trade["side"] == "Buy",
                            sz=float(trade["size"])
                        ))

                    return TradeMsg(
                        symbol=symbol,
                        time=float(resp_json["time"]),
                        trades=trades
                    )
                else:
                    self._logger.error(f"BYBIT REST [{ENDPOINT_GET_TRADES}] request failed; {resp_json}")
                    return None
                    
        except Exception as e:
            raise Exception(f"BYBIT REST [{ENDPOINT_GET_TRADES}] request exception; {str(e)}")
    
    async def get_orderbook(self, symbol):
        payload = {
            "category": "linear",
            "symbol": symbol,
            "limit": 500
        }

        try:
            async with self.unauth_session.get(
                url=ENDPOINT_GET_ORDERBOOK,
                params=payload
            ) as response:
                resp_text = await response.text()
                resp_json = self._json_decoder.decode(resp_text)
                
                if resp_json["retCode"] == 0:
                    return OrderbookMsg(
                        symbol=symbol,
                        time=float(resp_json["time"]),
                        bids=[[float(x[0]), float(x[1])] for x in resp_json["result"]["b"]],
                        asks=[[float(x[0]), float(x[1])] for x in resp_json["result"]["a"]],
                        is_bbo=False,
                        is_snapshot=True
                    )
                else:
                    self._logger.error(f"BYBIT REST [{ENDPOINT_GET_ORDERBOOK}] request failed; {str(resp_json['retMsg'])}")
                    return None
                    
        except Exception as e:
            raise Exception(f"BYBIT REST [{ENDPOINT_GET_ORDERBOOK}] request exception; {str(e)}")
                
    async def get_ticker(self, symbol):
        payload = {
            "category": "linear",
            "symbol": symbol
        }
        
        try:
            async with self.unauth_session.get(
                url=ENDPOINT_GET_TICKERS, 
                params=payload
            ) as response:
                resp_text = await response.text()
                resp_json = self._json_decoder.decode(resp_text)
                
                if resp_json["retCode"] == 0:
                    return TickerMsg(
                        symbol=symbol,
                        time=float(resp_json["time"]),
                        mark_px=float(resp_json["result"]["list"][0]["markPrice"]),
                        index_px=float(resp_json["result"]["list"][0]["indexPrice"]),
                        funding_rate=float(resp_json["result"]["list"][0]["fundingRate"]),
                        funding_time=float(resp_json["result"]["list"][0]["nextFundingTime"]),
                        adv=float(resp_json["result"]["list"][0]["volume24h"]),
                        px_chg_24h=float(resp_json["result"]["list"][0]["price24hPcnt"]),
                        oi=float(resp_json["result"]["list"][0]["openInterest"]),
                    )
                else:
                    self._logger.error(f"BYBIT REST [{ENDPOINT_GET_TICKERS}] request failed; {resp_json}")
                    return None
                    
        except Exception as e:
            raise Exception(f"BYBIT REST [{ENDPOINT_GET_TICKERS}] request exception; {str(e)}")

    async def get_orders(self, symbol):
        self.ensure_running(rest_only=True)

        payload = {
            "category": "linear",
            "symbol": symbol,
            "limit": 50
        }
        
        try:
            resp_json = await self._rest_client.submit(
                endpoint=ENDPOINT_GET_ORDERS, 
                payload=payload, 
                method="GET"
            )

            if resp_json["retCode"] == 0:
                orders: list[OrderMsg] = []

                for order in resp_json["result"]["list"]:
                    orders.append(OrderMsg(
                        symbol=symbol,
                        time=float(order["createTime"]),
                        create_time_ms=float(order["createTime"]),
                        oid=order["orderId"],
                        cloid=order["orderLinkId"],
                        px=float(order["price"]),
                        is_buy=order["side"] == "Buy",
                        sz=float(order["qty"]),
                        sz_rem=float(order["cumExecQty"]),
                        tif=self._tif_str_to_enum[order["timeInForce"]],
                        is_cancelled=False,
                        is_reduce_only=order["reduceOnly"],
                    ))

                return orders
            else:
                self._logger.error(f"BYBIT REST [{ENDPOINT_GET_ORDERS}] request failed; {resp_json}")
                return None
                
        except Exception as e:
            raise Exception(f"BYBIT REST [{ENDPOINT_GET_ORDERS}] request exception; {str(e)}")
    
    async def get_position(self, symbol):
        self.ensure_running(rest_only=True)

        payload = {
            "category": "linear",
            "symbol": symbol
        }
        
        try:
            resp_json = await self._rest_client.submit(
                endpoint=ENDPOINT_GET_POSITION, 
                payload=payload, 
                method="GET"
            )

            if resp_json["retCode"] == 0:
                position_data = resp_json["result"]["list"][0]
                
                return PositionMsg(
                    symbol=symbol,
                    time=float(position_data["updatedTime"]),
                    px=float(position_data["avgPrice"]),
                    is_long=position_data["side"] == "Buy",
                    sz=float(position_data["size"]),

                    # This field is difficult to calculate on infrequent updates, so we 
                    # use the time of the last update as the age. This is inaccurate, and 
                    # should not be used from this request. For accurate age, the websocket
                    # feed is sufficient, and ideally you calculate it yourself.
                    age=0.0,
                )
            else:
                self._logger.error(f"BYBIT REST [{ENDPOINT_GET_POSITION}] request failed; {resp_json}")
                return None
                
        except Exception as e:
            raise Exception(f"BYBIT REST [{ENDPOINT_GET_POSITION}] request exception; {str(e)}")
    
    async def get_executions(self, symbol: str) -> List[ExecutionMsg] | None:
        self.ensure_running(rest_only=True)

        payload = {
            "category": "linear",
            "symbol": symbol,
            "limit": 100
        }

        try:
            resp_json = await self._rest_client.submit(
                endpoint=ENDPOINT_GET_EXECUTIONS,
                payload=payload,
                method="GET"
            )

            if resp_json["retCode"] == 0:
                executions: list[ExecutionMsg] = []

                for execution in resp_json["result"]["list"]:
                    executions.append(ExecutionMsg(
                        symbol=symbol,  
                        time=float(execution["tradeTime"]),
                        px=float(execution["execPrice"]),
                        is_buy=execution["side"] == "Buy",
                        sz=float(execution["execQty"]),
                        is_maker=execution["isMaker"],
                        fee_paid=float(execution["execFee"]),
                    ))

                return executions
            else:
                self._logger.error(f"BYBIT REST [{ENDPOINT_GET_EXECUTIONS}] request failed; {resp_json}")
                return None
                
        except Exception as e:
            raise Exception(f"BYBIT REST [{ENDPOINT_GET_EXECUTIONS}] request exception; {str(e)}")
    
    async def get_account(self):
        self.ensure_running(rest_only=True)
        
        payload = {
            "accountType": "UNIFIED"
        }
        
        try:
            resp_json = await self._rest_client.submit(
                endpoint=ENDPOINT_GET_ACCOUNT, 
                payload=payload, 
                method="GET"
            )
            
            if resp_json["retCode"] == 0:
                account_data = resp_json["result"]["list"][0]
                
                return AccountMsg(
                    time=float(resp_json["time"]),
                    bal=float(account_data["totalEquity"]),
                    im=float(account_data["accountIMRate"]),
                    mm=float(account_data["accountMMRate"]),
                    uPnl=float(account_data["totalPerpUPL"]),
                )
            else:
                self._logger.error(f"BYBIT REST [{ENDPOINT_GET_ACCOUNT}] request failed; {resp_json}")
                return None
                
        except Exception as e:
            raise Exception(f"BYBIT REST [{ENDPOINT_GET_ACCOUNT}] request exception; {str(e)}")
    
    async def get_precision(self, symbol):
        self.ensure_running(rest_only=True)

        payload = {
            "category": "linear",
            "symbol": symbol
        }
        
        try:
            async with self.unauth_session.get(
                url=ENDPOINT_GET_INSTRUMENTS_INFO, 
                params=payload
            ) as response:
                resp_text = await response.text()
                resp_json = self._json_decoder.decode(resp_text)

                if resp_json["retCode"] == 0:
                    tick_size = float(resp_json["result"]["list"][0]["priceFilter"]["tickSize"])
                    lot_size = float(resp_json["result"]["list"][0]["lotSizeFilter"]["qtyStep"])

                    return (tick_size, lot_size)
                else:
                    self._logger.error(f"BYBIT REST [{ENDPOINT_GET_INSTRUMENTS_INFO}] request failed; {resp_json}")
                    return None
                
        except Exception as e:
            raise Exception(f"BYBIT REST [{ENDPOINT_GET_INSTRUMENTS_INFO}] request exception; {str(e)}")
