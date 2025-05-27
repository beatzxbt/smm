from typing import List, Tuple, Optional, Dict

from framework.tools.logger import Logger
from framework.tools.time import time_ms
from framework.base.exchange import BaseExchange
from framework.okx.client import OkxRestTradeClient, OkxWsTradeClient

from framework.base.internal_structs import ExecutionMsg, OrderMsg, OrderbookMsg, TickerMsg, Trade, TradeMsg, PositionMsg, AccountMsg, OrderTimeInForce

# OKX API endpoints
ENDPOINT_POST_CREATE_ORDER = "https://www.okx.com/api/v5/trade/order"
ENDPOINT_POST_AMEND_ORDER = "https://www.okx.com/api/v5/trade/amend-order"
ENDPOINT_POST_CANCEL_ORDER = "https://www.okx.com/api/v5/trade/cancel-order"
ENDPOINT_POST_CANCEL_ALL = "https://www.okx.com/api/v5/trade/cancel-all"
ENDPOINT_GET_TRADES = "https://www.okx.com/api/v5/market/trades"
ENDPOINT_GET_ORDERBOOK = "https://www.okx.com/api/v5/market/books"
ENDPOINT_GET_TICKERS = "https://www.okx.com/api/v5/market/tickers"
ENDPOINT_GET_ORDERS = "https://www.okx.com/api/v5/trade/orders-pending"
ENDPOINT_GET_POSITION = "https://www.okx.com/api/v5/account/positions"
ENDPOINT_GET_EXECUTIONS = "https://www.okx.com/api/v5/trade/fills"
ENDPOINT_GET_ACCOUNT = "https://www.okx.com/api/v5/account/balance"
ENDPOINT_GET_INSTRUMENTS_INFO = "https://www.okx.com/api/v5/public/instruments"

class OkxExchange(BaseExchange):
    def __init__(self, api_key: str, api_secret: str, passphrase: str, logger: Logger):
        """
        Initializes the OKX Exchange.

        Args:
            api_key (str): OKX API key.
            api_secret (str): OKX API secret.
            passphrase (str): OKX API passphrase.
            logger (Logger): Logger instance for logging.
        """
        # This allows the client to be used for unsigned requests in cases
        # where the API key and secret are not needed.
        if api_key is not None and api_secret is not None and passphrase is not None:
            _rest_client = OkxRestTradeClient(api_key, api_secret, passphrase, logger)
            _ws_client = OkxWsTradeClient(api_key, api_secret, passphrase, logger)
        else:
            _rest_client = None
            _ws_client = None

        super().__init__(
            logger=logger,
            rest_client=_rest_client,
            ws_client=_ws_client,
            max_cloid_length=32
        )

        self._tif_enum_to_str = {
            OrderTimeInForce.GTC: "GTC",
            OrderTimeInForce.IOC: "IOC",
            OrderTimeInForce.FOK: "FOK",
            OrderTimeInForce.PO: "post_only",
        }
        self._tif_str_to_enum = {v: k for k, v in self._tif_enum_to_str.items()}
        
    async def create_order(
        self, 
        symbol: str, 
        is_maker: bool, 
        sz: float, 
        is_buy: bool, 
        px: Optional[float] = None, 
        tif: OrderTimeInForce = OrderTimeInForce.GTC, 
        reduce_only: bool = False, 
        cloid: Optional[str] = None
    ) -> Optional[Dict]:
        self.ensure_running(ws_only=True)
        
        if px is not None and px < 0.0:
            raise ValueError(f"Invalid px; expected >=0.0 but got {px}")
        
        if sz is not None and sz <= 0.0:
            raise ValueError(f"Invalid sz; expected >0.0 but got {sz}")
        
        payload = {
            "instId": symbol,
            "tdMode": "cross",  # OKX requires trade mode
            "side": "buy" if is_buy else "sell",
            "ordType": "limit" if is_maker else "market",
            "sz": str(sz),
        }
        
        if cloid is not None:
            payload["clOrdId"] = cloid

        if is_maker and px is not None:
            payload["px"] = str(px)
        elif not is_maker:
            # Market orders don't need price
            pass
        else:
            raise ValueError(f"Invalid px; expected for maker orders but got {px}")
        
        if reduce_only:
            payload["reduceOnly"] = "true"
        
        # Add time in force for limit orders
        if is_maker and tif != OrderTimeInForce.GTC:
            payload["tgtCcy"] = self._tif_enum_to_str[tif]
        
        payload = {
            "op": "order",
            "args": [payload]
        }

        response = await self._ws_client.submit(payload)
        return response

    async def amend_order(
        self,
        symbol: str,
        sz: Optional[float] = None,
        px: Optional[float] = None,
        oid: Optional[str] = None,
        cloid: Optional[str] = None
    ) -> Optional[Dict]:
        """
        Amends an existing order via OKX's Trade WS API.
        """
        self.ensure_running(ws_only=True)
        
        if not oid and not cloid:
            raise ValueError("Missing oid and/or cloid; either 'oid' or 'cloid' must be provided for an amendment")
        
        if px is not None and px < 0.0:
            raise ValueError(f"Invalid px; expected >=0.0 but got {px}")
        
        if sz is not None and sz <= 0.0:
            raise ValueError(f"Invalid sz; expected >0.0 but got {sz}")
        
        payload = {
            "instId": symbol,
        }

        if oid is not None:
            payload["ordId"] = oid
        elif cloid is not None:
            payload["clOrdId"] = cloid

        if px is not None:
            payload["newPx"] = str(px)
        if sz is not None:
            payload["newSz"] = str(sz)

        payload = {
            "op": "amend-order",
            "args": [payload]
        }

        response = await self._ws_client.submit(payload)
        return response

    async def cancel_order(
        self,
        symbol: str,
        oid: Optional[str] = None,
        cloid: Optional[str] = None
    ) -> Optional[Dict]:
        """
        Cancels a single open order via OKX's Trade WS API.
        """
        self.ensure_running(ws_only=True)

        if not oid and not cloid:
            raise ValueError("Missing oid and/or cloid; either 'oid' or 'cloid' must be provided for cancellation")
        
        payload = {
            "instId": symbol,
        }

        if oid is not None:
            payload["ordId"] = oid
        elif cloid is not None:
            payload["clOrdId"] = cloid

        payload = {
            "op": "cancel-order",
            "args": [payload]
        }

        response = await self._ws_client.submit(payload)
        return response

    async def cancel_all_orders(self, symbol: str) -> Optional[Dict]:
        """
        Cancels all open orders for the default symbol via REST API.

        Returns:
            dict | None: The API response as a dict if successful, or None if error.
        """
        self.ensure_running(rest_only=True)

        payload = {
            "instId": symbol
        }

        try:
            resp_json = await self._rest_client.submit(
                endpoint=ENDPOINT_POST_CANCEL_ALL,
                payload=payload,
                method="POST"
            )

            if resp_json and resp_json.get("code") == "0":
                return resp_json
            else:
                self._logger.error(f"OKX REST [{ENDPOINT_POST_CANCEL_ALL}] request failed; {resp_json}")
                return resp_json

        except Exception as e:
            raise Exception(f"OKX REST [{ENDPOINT_POST_CANCEL_ALL}] request exception; {str(e)}")

    async def get_trades(self, symbol: str) -> Optional[TradeMsg]:
        payload = {
            "instId": symbol,
            "limit": "500"
        }
        
        try:
            async with self.unauth_session.get(
                url=ENDPOINT_GET_TRADES, 
                params=payload
            ) as response:
                resp_text = await response.text()
                resp_json = self._json_decoder.decode(resp_text)
                
                if resp_json["code"] == "0":
                    trades: list[Trade] = []

                    # The trades are returned in reverse chronological order, so we 
                    # reverse the list to get the correct order.
                    for trade in resp_json["data"][::-1]:
                        trades.append(Trade(
                            time=float(trade["ts"]),
                            px=float(trade["px"]),
                            is_buy=trade["side"] == "buy",
                            sz=float(trade["sz"])
                        ))

                    return TradeMsg(
                        symbol=symbol,
                        time=time_ms(),
                        trades=trades
                    )
                else:
                    self._logger.error(f"OKX REST [{ENDPOINT_GET_TRADES}] request failed; {resp_json}")
                    return None
                    
        except Exception as e:
            raise Exception(f"OKX REST [{ENDPOINT_GET_TRADES}] request exception; {str(e)}")
    
    async def get_orderbook(self, symbol: str) -> Optional[OrderbookMsg]:
        payload = {
            "instId": symbol,
            "sz": "400"  # OKX uses sz parameter for depth
        }

        try:
            async with self.unauth_session.get(
                url=ENDPOINT_GET_ORDERBOOK,
                params=payload
            ) as response:
                resp_text = await response.text()
                resp_json = self._json_decoder.decode(resp_text)
                
                if resp_json["code"] == "0":
                    data = resp_json["data"][0]
                    return OrderbookMsg(
                        symbol=symbol,
                        time=float(data["ts"]),
                        bids=[[float(x[0]), float(x[1])] for x in data["bids"]],
                        asks=[[float(x[0]), float(x[1])] for x in data["asks"]],
                        is_bbo=False,
                        is_snapshot=True
                    )
                else:
                    self._logger.error(f"OKX REST [{ENDPOINT_GET_ORDERBOOK}] request failed; {resp_json}")
                    return None
                    
        except Exception as e:
            raise Exception(f"OKX REST [{ENDPOINT_GET_ORDERBOOK}] request exception; {str(e)}")
                
    async def get_ticker(self, symbol: str) -> Optional[TickerMsg]:
        payload = {
            "instType": "SWAP",
            "instId": symbol
        }
        
        try:
            async with self.unauth_session.get(
                url=ENDPOINT_GET_TICKERS, 
                params=payload
            ) as response:
                resp_text = await response.text()
                resp_json = self._json_decoder.decode(resp_text)
                
                if resp_json["code"] == "0" and resp_json["data"]:
                    ticker_data = resp_json["data"][0]
                    return TickerMsg(
                        symbol=symbol,
                        time=float(ticker_data["ts"]),
                        mark_px=float(ticker_data["markPx"]) if ticker_data["markPx"] else None,
                        index_px=float(ticker_data["idxPx"]) if ticker_data["idxPx"] else None,
                        funding_rate=float(ticker_data["fundingRate"]) if ticker_data["fundingRate"] else None,
                        funding_time=float(ticker_data["nextFundingTime"]) if ticker_data["nextFundingTime"] else None,
                        adv=float(ticker_data["vol24h"]) if ticker_data["vol24h"] else None,
                        px_chg_24h=float(ticker_data["sodUtc8"]) if ticker_data["sodUtc8"] else None,
                        oi=float(ticker_data["openInterest"]) if ticker_data["openInterest"] else None,
                    )
                else:
                    self._logger.error(f"OKX REST [{ENDPOINT_GET_TICKERS}] request failed; {resp_json}")
                    return None
                    
        except Exception as e:
            raise Exception(f"OKX REST [{ENDPOINT_GET_TICKERS}] request exception; {str(e)}")

    async def get_orders(self, symbol: str) -> Optional[List[OrderMsg]]:
        self.ensure_running(rest_only=True)

        payload = {
            "instId": symbol,
            "instType": "SWAP"
        }
        
        try:
            resp_json = await self._rest_client.submit(
                endpoint=ENDPOINT_GET_ORDERS, 
                payload=payload, 
                method="GET"
            )

            if resp_json and resp_json["code"] == "0":
                orders: list[OrderMsg] = []

                for order in resp_json["data"]:
                    orders.append(OrderMsg(
                        symbol=symbol,
                        time=float(order["cTime"]),
                        create_time_ms=float(order["cTime"]),
                        oid=order["ordId"],
                        cloid=order["clOrdId"],
                        px=float(order["px"]) if order["px"] else 0.0,
                        is_buy=order["side"] == "buy",
                        sz=float(order["sz"]),
                        sz_rem=float(order["fillSz"]),
                        tif=self._tif_str_to_enum.get(order.get("tgtCcy", "GTC"), OrderTimeInForce.GTC),
                        is_cancelled=order["state"] == "canceled",
                        is_reduce_only=order.get("reduceOnly", "false") == "true",
                    ))

                return orders
            else:
                self._logger.error(f"OKX REST [{ENDPOINT_GET_ORDERS}] request failed; {resp_json}")
                return None
                
        except Exception as e:
            raise Exception(f"OKX REST [{ENDPOINT_GET_ORDERS}] request exception; {str(e)}")
    
    async def get_position(self, symbol: str) -> Optional[PositionMsg]:
        self.ensure_running(rest_only=True)

        payload = {
            "instId": symbol,
            "instType": "SWAP"
        }
        
        try:
            resp_json = await self._rest_client.submit(
                endpoint=ENDPOINT_GET_POSITION, 
                payload=payload, 
                method="GET"
            )

            if resp_json and resp_json["code"] == "0":
                if resp_json["data"]:
                    position_data = resp_json["data"][0]
                    
                    return PositionMsg(
                        symbol=symbol,
                        time=float(position_data["uTime"]),
                        px=float(position_data["avgPx"]) if position_data["avgPx"] else 0.0,
                        is_long=position_data["posSide"] == "long" or (position_data["posSide"] == "net" and float(position_data["pos"]) > 0),
                        sz=abs(float(position_data["pos"])),
                        # This field is difficult to calculate on infrequent updates, so we 
                        # use the time of the last update as the age. This is inaccurate, and 
                        # should not be used from this request. For accurate age, the websocket
                        # feed is sufficient, and ideally you calculate it yourself.
                        age=0.0,
                    )
                else:
                    # No position found, return empty position
                    return PositionMsg(
                        symbol=symbol,
                        time=time_ms(),
                        px=0.0,
                        is_long=True,
                        sz=0.0,
                        age=0.0,
                    )
            else:
                self._logger.error(f"OKX REST [{ENDPOINT_GET_POSITION}] request failed; {resp_json}")
                return None
                
        except Exception as e:
            raise Exception(f"OKX REST [{ENDPOINT_GET_POSITION}] request exception; {str(e)}")
    
    async def get_executions(self, symbol: str) -> Optional[List[ExecutionMsg]]:
        self.ensure_running(rest_only=True)

        payload = {
            "instId": symbol,
            "instType": "SWAP",
            "limit": "100"
        }

        try:
            resp_json = await self._rest_client.submit(
                endpoint=ENDPOINT_GET_EXECUTIONS,
                payload=payload,
                method="GET"
            )

            if resp_json and resp_json["code"] == "0":
                executions: list[ExecutionMsg] = []

                for execution in resp_json["data"]:
                    executions.append(ExecutionMsg(
                        symbol=symbol,  
                        time=float(execution["ts"]),
                        px=float(execution["fillPx"]),
                        is_buy=execution["side"] == "buy",
                        sz=float(execution["fillSz"]),
                        is_maker=execution["execType"] == "M",
                        fee_paid=float(execution["fee"]),
                    ))

                return executions
            else:
                self._logger.error(f"OKX REST [{ENDPOINT_GET_EXECUTIONS}] request failed; {resp_json}")
                return None
                
        except Exception as e:
            raise Exception(f"OKX REST [{ENDPOINT_GET_EXECUTIONS}] request exception; {str(e)}")
    
    async def get_account(self) -> Optional[AccountMsg]:
        self.ensure_running(rest_only=True)
        
        payload = {}
        
        try:
            resp_json = await self._rest_client.submit(
                endpoint=ENDPOINT_GET_ACCOUNT, 
                payload=payload, 
                method="GET"
            )
            
            if resp_json and resp_json["code"] == "0":
                account_data = resp_json["data"][0]
                
                # Calculate total equity and unrealized PnL
                total_equity = 0.0
                total_upnl = 0.0
                
                for detail in account_data["details"]:
                    total_equity += float(detail["eq"])
                    if detail["upl"]:
                        total_upnl += float(detail["upl"])
                
                return AccountMsg(
                    time=float(account_data["uTime"]),
                    bal=total_equity,
                    im=float(account_data["imr"]) if account_data["imr"] else 0.0,
                    mm=float(account_data["mmr"]) if account_data["mmr"] else 0.0,
                    uPnl=total_upnl,
                )
            else:
                self._logger.error(f"OKX REST [{ENDPOINT_GET_ACCOUNT}] request failed; {resp_json}")
                return None
                
        except Exception as e:
            raise Exception(f"OKX REST [{ENDPOINT_GET_ACCOUNT}] request exception; {str(e)}")
    
    async def get_precision(self, symbol: str) -> Optional[Tuple[float, float]]:
        payload = {
            "instType": "SWAP",
            "instId": symbol
        }
        
        try:
            async with self.unauth_session.get(
                url=ENDPOINT_GET_INSTRUMENTS_INFO, 
                params=payload
            ) as response:
                resp_text = await response.text()
                resp_json = self._json_decoder.decode(resp_text)

                if resp_json["code"] == "0" and resp_json["data"]:
                    instrument_data = resp_json["data"][0]
                    tick_size = float(instrument_data["tickSz"])
                    lot_size = float(instrument_data["lotSz"])

                    return (tick_size, lot_size)
                else:
                    self._logger.error(f"OKX REST [{ENDPOINT_GET_INSTRUMENTS_INFO}] request failed; {resp_json}")
                    return None
                
        except Exception as e:
            raise Exception(f"OKX REST [{ENDPOINT_GET_INSTRUMENTS_INFO}] request exception; {str(e)}") 