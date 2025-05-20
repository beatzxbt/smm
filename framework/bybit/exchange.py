from framework.base.exchange import BaseExchange
from framework.bybit.client import BybitRestTradeClient, BybitWsTradeClient
from framework.tools.logger import Logger
from framework.tools.time import time_ms

from framework.base.internal_structs import OrderMsg, OrderbookMsg, TickerMsg, Trade, TradeMsg, PositionMsg, AccountMsg

RECV_WINDOW = 1000

ENDPOINT_GET_ORDERS = "https://api.bybit.com/v5/order/realtime"
ENDPOINT_GET_POSITION = "https://api.bybit.com/v5/position/list"
ENDPOINT_GET_ACCOUNT = "https://api.bybit.com/v5/account/wallet-balance"
ENDPOINT_GET_INSTRUMENTS_INFO = "https://api.bybit.com/v5/market/instruments-info"
ENDPOINT_GET_TICKERS = "https://api.bybit.com/v5/market/tickers"
ENDPOINT_GET_TRADES = "https://api.bybit.com/v5/market/recent-trade"
ENDPOINT_GET_ORDERBOOK = "https://api.bybit.com/v5/market/orderbook"
ENDPOINT_POST_CREATE_ORDER = "https://api.bybit.com/v5/order/create"
ENDPOINT_POST_AMEND_ORDER = "https://api.bybit.com/v5/order/amend"
ENDPOINT_POST_CANCEL_SINGLE = "https://api.bybit.com/v5/order/cancel"
ENDPOINT_POST_CANCEL_ALL = "https://api.bybit.com/v5/order/cancel-all"
ENDPOINT_POST_SET_LEVERAGE = "https://api.bybit.com/v5/position/set-leverage"

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

        self._valid_tifs = ["GTC", "IOC", "FOK", "PO"]
        self._tif_map = {
            "GTC": "GTC",
            "IOC": "IOC",
            "FOK": "FOK",
            "PO": "PostOnly",
        }
        
    async def create_order(
        self, 
        symbol, 
        is_maker, 
        sz, 
        is_buy, 
        px=None, 
        tif="GTC", 
        reduce_only=False, 
        cloid=None
    ):
        self.is_running(ws_only=True)
        
        if tif not in self._valid_tifs:
            raise ValueError(f"Invalid time-in-force value; expected one of {self._valid_tifs} but got {tif}")
        
        if px is not None and px < 0.0:
            raise ValueError(f"Invalid px; expected >=0.0 but got {px}")
        
        if sz is not None and sz <= 0.0:
            raise ValueError(f"Invalid sz; expected >0.0 but got {sz}")
        
        payload = {
            "category": "linear",
            "symbol": symbol,
            "side": "Buy" if is_buy else "Sell",
            "orderType": "Limit" if is_maker else "Market",
            "timeInForce": self._tif_map.get(tif, "GTC"),
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
        self.is_running(ws_only=True)
        
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
        self.is_running(ws_only=True)

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

    async def cancel_all(self, symbol):
        """
        Cancels all open orders for the default symbol via REST API.

        Returns:
            dict | None: The API response as a dict if successful, or None if error.
        """
        self.is_running(rest_only=True)
        
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

    async def get_orders(self, symbol):
        self.is_running(rest_only=True)

        payload = {
            "category": "linear",
            "symbol": symbol
        }
        
        response = await self._rest_client.submit(
            endpoint=ENDPOINT_GET_ORDERS, 
            payload=payload, 
            method="GET"
        )
        return response
    
    async def get_position(self, symbol):
        self.is_running(rest_only=True)

        payload = {
            "category": "linear",
            "symbol": symbol
        }
        
        response = await self._rest_client.submit(
            endpoint=ENDPOINT_GET_POSITION, 
            payload=payload, 
            method="GET"
        )
        return response
    
    async def get_account(self):
        self.is_running(rest_only=True)
        
        payload = {
            "category": "linear"
        }
        
        response = await self._rest_client.submit(
            endpoint=ENDPOINT_GET_ACCOUNT, 
            payload=payload, 
            method="GET"
        )
        return response
    
    async def get_instruments_info(self, symbol = None):
        self.is_running(rest_only=True)

        payload = {
            "category": "linear"
        }
        
        if symbol:
            payload["symbol"] = symbol
        
        response = await self._unauthenticated_session.get(
            url=ENDPOINT_GET_INSTRUMENTS_INFO, 
            params=payload
        )
        return response

    async def get_tickers(self, symbol = None):
        payload = {
            "category": "linear"
        }
        
        if symbol is not None:
            payload["symbol"] = symbol
        
        try:
            time_sent = time_ms()
            async with self.unauth_session.get(
                url=ENDPOINT_GET_TICKERS, 
                params=payload
            ) as response:
                time_recv = time_ms()
                resp_text = await response.text()
                resp_json = orjson.loads(resp_text)
                
                if resp_json["retMsg"] in ["OK", "success"]:
                    latency = round(time_recv - time_sent, 2)
                    self.logger.debug(f"Trade REST {ENDPOINT_GET_TICKERS} latency; {latency}ms")
                    return resp_json
                else:
                    self.logger.error(f"get_tickers() request failed; {resp_json}")
                    return None
                    
        except Exception as e:
            self.logger.error(f"get_tickers() request exception; {e}")
            return None

    async def get_trades(self, symbol, limit: int = 1000):
        payload = {
            "category": "linear",
            "symbol": symbol,
            "limit": limit
        }
        
        try:
            time_sent = time_ms()
            async with self.unauth_session.get(
                url=ENDPOINT_GET_TRADES, 
                params=payload
            ) as response:
                time_recv = time_ms()
                resp_text = await response.text()
                resp_json = orjson.loads(resp_text)
                
                if resp_json["retMsg"] in ["OK", "success"]:
                    latency = round(time_recv - time_sent, 2)
                    self.logger.debug(f"Trade REST [{ENDPOINT_GET_TRADES}] latency; {latency}ms")
                    return resp_json
                else:
                    self.logger.error(f"get_trades() request failed; {resp_json}")
                    return None
                    
        except Exception as e:
            self.logger.error(f"get_trades() request exception; {e}")
            return None
        
    async def set_leverage(self, symbol, leverage: float):
        """
        Sets the leverage for a symbol via REST API.

        Args:
            symbol (str): The trading symbol.
            leverage (float): Leverage to set.

        Returns:
            dict | None: The API response.
        """
        self.is_running(rest_only=True)
        
        # If you're 200x and higher, seek god.
        if leverage < 1.0 or leverage > 200.0:
            raise ValueError(f"Invalid leverage; expected >1.0 but got {leverage}")
        
        payload = {
            "category": "linear",
            "symbol": symbol,
            "buyLeverage": leverage,
            "sellLeverage": leverage
        }
        
        response = await self._rest_client.submit(
            endpoint=ENDPOINT_POST_SET_LEVERAGE, 
            payload=payload, 
            method="POST"
        )
        return response
