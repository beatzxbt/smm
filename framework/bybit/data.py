import hmac
import hashlib
import msgspec
import aiohttp
import asyncio

from framework.tools import (
    time_ms, 
    time_s, 
    Logger
)

from framework.base.data import BaseMarketData, BasePrivateData
from framework.base.internal_structs import (
    TickerMsg, 
    OrderbookMsg, 
    Trade, 
    TradeMsg, 
    ExecutionMsg, 
    AccountMsg, 
    PositionMsg, 
    OrderMsg,
    OrderTimeInForce
)

WS_PUBLIC_STREAM = "wss://stream.bybit.com/v5/public/linear"
WS_PRIVATE_STREAM = "wss://stream.bybit.com/v5/private" 

class BybitMarketData(BaseMarketData):
    def __init__(self, symbols: list[str], logger: Logger, consumer_queues: list[asyncio.Queue]) -> None:
        super().__init__(symbols, logger, consumer_queues)

        self.ws_sub_req = {
            "op": "subscribe",
            "args": [
                item for symbol in self.symbols 
                for item in [
                    f"tickers.{symbol}", 
                    f"orderbook.1.{symbol}", 
                    f"orderbook.500.{symbol}",
                    f"publicTrade.{symbol}"
                ]
            ]
        }

        self.topic_handler_map = {}
        for symbol in self.symbols:
            self.topic_handler_map.update({
                f"tickers.{symbol}": self.process_ticker,
                f"orderbook.1.{symbol}": self.process_orderbook,
                f"orderbook.500.{symbol}": self.process_orderbook,
                f"publicTrade.{symbol}": self.process_trade
            })
        
        # Bybit sends partial ticker data sometimes, so we store a snapshot
        # of all ticker data to copy from in the handler.
        self.latest_ticker_data = {}
        for symbol in self.symbols:
            self.latest_ticker_data[symbol] = TickerMsg(
                symbol=symbol,
                time=None,
                mark_px=None,
                index_px=None,
                funding_rate=None,
                funding_time=None,
                adv=None,
                px_chg_24h=None,
                oi=None
            )

    def process_ticker(self, data):
        try:
            symbol = data["topic"].split(".")[1]
            time = data["ts"]
            ticker_data = data["data"]
            
            # Copy from the latest ticker data for this symbol
            latest_msg = self.latest_ticker_data[symbol]
            latest_msg.time = time

            # Update the existing ticker object with new data
            if "markPrice" in ticker_data:
                latest_msg.mark_px = float(ticker_data["markPrice"])
            if "indexPrice" in ticker_data:
                latest_msg.index_px = float(ticker_data["indexPrice"])
            if "fundingRate" in ticker_data:
                latest_msg.funding_rate = float(ticker_data["fundingRate"])
            if "nextFundingTime" in ticker_data:
                latest_msg.funding_time = float(ticker_data["nextFundingTime"])
            if "volume24h" in ticker_data:
                latest_msg.adv = float(ticker_data["volume24h"])
            if "price24hPcnt" in ticker_data:
                latest_msg.px_chg_24h = float(ticker_data["price24hPcnt"])
            if "openInterest" in ticker_data:
                latest_msg.oi = float(ticker_data["openInterest"])
            
            self.broadcast(latest_msg)
            self.logger.trace(f"Ticker data received; {latest_msg}")
                
        except Exception as e:
            self.logger.error(f"Error processing Ticker data; {e}")
            self.logger.debug(f"Raw ticker data; {data}")

    def process_orderbook(self, data):
        try:
            _, nlevels, symbol = data["topic"].split(".")
            time = data["ts"]
            orderbook_data = data["data"]
            
            bids = [[float(price), float(qty)] for price, qty in orderbook_data.get("b", [])]
            asks = [[float(price), float(qty)] for price, qty in orderbook_data.get("a", [])]
            is_bbo = nlevels == "1"
            is_snapshot = data["type"] == "snapshot" and not is_bbo

            msg = OrderbookMsg(
                symbol=symbol,
                time=time,
                bids=bids,
                asks=asks,
                is_bbo=is_bbo,
                is_snapshot=is_snapshot
            )
            
            self.broadcast(msg)
            self.logger.trace(f"Orderbook data received; {msg}")
            
        except Exception as e:
            self.logger.error(f"Error processing Orderbook data; {e}")
            self.logger.debug(f"Raw orderbook data; {data}")

    def process_trade(self, data):
        try:
            symbol = data["topic"].split(".")[1]
            time = data["ts"]
            trade_data = data["data"]
            trades: list[Trade] = []

            for event in trade_data:
                trade = Trade(
                    time=float(event["T"]),
                    px=float(event["p"]),
                    is_buy=event["S"] == "Buy",
                    sz=float(event["v"]),
                ) 
                trades.append(trade)
            
            msg = TradeMsg(
                symbol=symbol,
                time=time,
                trades=trades
            )

            self.broadcast(msg)
            self.logger.trace(f"Trade data received; {msg}")

        except Exception as e:
            self.logger.error(f"Error processing trade data; {e}")
            self.logger.debug(f"Raw trade data; {data}")

    async def start(self):
        for attempt in range(3):
            try:
                async with aiohttp.ClientSession() as session, session.ws_connect(WS_PUBLIC_STREAM) as websocket:
                    self.logger.info(f"Market data connection started; ")
                    await websocket.send_bytes(self.json_encoder.encode(self.ws_sub_req))
                    
                    while True:
                        msg = await websocket.receive()
                        
                        if msg.type == aiohttp.WSMsgType.TEXT:
                            recv = self.json_decoder.decode(msg.data)
                            
                            if "success" in recv:
                                self.logger.debug(f"Market data subscription successful; {recv}")
                                continue

                            handler = self.topic_handler_map.get(recv["topic"])
                            if handler:
                                handler(recv)
                            else:
                                self.logger.warning(f"Unknown topic; {recv['topic']}")
                        
                        elif msg.type in [aiohttp.WSMsgType.CLOSED, aiohttp.WSMsgType.ERROR]:
                            self.logger.warning("Market data websocket stale, restarting...")
                            break  
                
                # If we reach here, the loop exited without errors - unlikely but possible
                self.logger.warning("WebSocket loop exited normally, reconnecting...")
                await asyncio.sleep(1)
                continue
                
            except asyncio.CancelledError:
                self.logger.info("Market data feed cancelled; closing connection")
                return
                
            except ConnectionError as ce:
                # Critical errors we want to propagate to the main 
                # loop directly without retrying 
                raise ce
                
            except Exception as e:
                self.logger.error(f"Connection attempt {attempt+1}/3 failed; error: {e}")
                if attempt >= 2:
                    self.logger.error("Maximum reconnection attempts reached; closing connection")
                    raise RuntimeError(f"Failed to connect to market feed after 3 attempts") from e
                
                await asyncio.sleep(1)

class BybitPrivateData(BasePrivateData):
    """
    Handles private data streams from Bybit WebSocket API.
    Manages connection, subscription, and processing of private data like orders and positions.
    """
    def __init__(self, api_key: str, api_secret: str, symbols: list[str], logger: Logger, consumer_queues: list[asyncio.Queue]):
        super().__init__(api_key, api_secret, symbols, logger, consumer_queues)

        self.ws_sub_req = {
            "op": "subscribe",
            "args": ["order", "position", "execution", "wallet"]
        }

        self.topic_handler_map = {
            "order": self.process_order,
            "position": self.process_position,
            "execution": self.process_execution,
            "wallet": self.process_account
        }

        self.position_age_map = {symbol: 0.0 for symbol in self.symbols}

        self.tif_map = {
            "GTC": OrderTimeInForce.GTC,
            "IOC": OrderTimeInForce.IOC,
            "PostOnly": OrderTimeInForce.PO,
            "FOK": OrderTimeInForce.FOK
        }

    def process_order(self, data):
        try:
            for order_data in data["data"]:
                symbol = order_data["symbol"]

                if symbol not in self.symbols:
                    continue
                
                msg = OrderMsg(
                    symbol=symbol,
                    time=float(order_data["createdTime"]),
                    create_time_ms=float(order_data["createdTime"]),
                    oid=order_data["orderId"],
                    cloid=order_data["clientOrderId"],
                    px=float(order_data.get("price", 0)),
                    is_buy=order_data["side"] == "Buy",
                    sz=float(order_data.get("qty", 0)),
                    sz_rem=float(order_data.get("cumExecQty", 0)),
                    tif=self.tif_map.get(order_data.get("timeInForce", ""), OrderTimeInForce.GTC),
                    is_cancelled=order_data.get("orderStatus", "") in ["Filled", "Rejected", "Cancelled"],
                    is_reduce_only=order_data.get("reduceOnly", False),
                )

                self.broadcast(msg)
                self.logger.trace(f"Order data received; {msg}")

        except Exception as e:
            self.logger.error(f"Error processing order data: {e}")
            self.logger.debug(f"Raw order data; {data}")

    def process_position(self, data):
        try:
            for position_data in data["data"]:
                symbol = position_data["symbol"]

                if symbol not in self.symbols:
                    continue
                
                # Bybit does not give the immidiate age of the position, so we 
                # track it from the first non-zero size update.
                prev_size = self.position_age_map[symbol]
                new_size = float(position_data.get("size", 0))

                if prev_size == 0 and new_size > 0:
                    self.position_age_map[symbol] = float(position_data["updatedTime"])
                elif new_size == 0:
                    self.position_age_map[symbol] = 0.0

                msg = PositionMsg(
                    symbol=symbol,
                    time=float(position_data["updatedTime"]),
                    px=float(position_data.get("avgPrice", 0)),
                    is_long=position_data.get("side", "") == "Buy",
                    sz=float(position_data.get("size", 0)),
                    age=float(position_data["updatedTime"]) - self.position_age_map[symbol],
                )

                self.broadcast(msg)
                self.logger.trace(f"Position data received; {msg}")

        except Exception as e:
            self.logger.error(f"Error processing position data: {e}")
            self.logger.debug(f"Raw position data; {data}")

    def process_execution(self, data):
        try:
            for execution_data in data["data"]:
                symbol = execution_data["symbol"]

                if symbol not in self.symbols:
                    continue
                
                msg = ExecutionMsg(
                    symbol=symbol,
                    time=float(execution_data["execTime"]),  
                    px=float(execution_data["execPrice"]),
                    is_buy=execution_data["side"] == "Buy",
                    sz=float(execution_data["execQty"]),
                    is_maker=execution_data.get("execType", "") == "Limit",
                    fee_paid=float(execution_data.get("execFee", 0))
                )

                self.broadcast(msg)
                self.logger.trace(f"Execution data received; {msg}")

        except Exception as e:
            self.logger.error(f"Error processing execution data: {e}")
            self.logger.debug(f"Raw execution data; {data}")

    def process_account(self, data):
        try:
            for account_data in data["data"]:
                msg = AccountMsg(
                    time=time_s(),
                    bal=float(account_data.get("totalEquity", 0)),
                    im=float(account_data.get("totalInitialMargin", 0)),
                    mm=float(account_data.get("totalMaintenanceMargin", 0)),
                    uPnl=float(account_data.get("totalPnl", 0))
                )

                self.broadcast(msg)
                self.logger.trace(f"Account data received; {msg}")

        except Exception as e:
            self.logger.error(f"Error processing account data: {e}")
            self.logger.debug(f"Raw account data; {data}")

    async def authenticate(self, ws):
        expires = int(time_ms() + 5000)
        signature = hmac.new(
            bytes(self.api_secret, "utf-8"),
            bytes(f"GET/realtime{expires}", "utf-8"),
            hashlib.sha256
        ).hexdigest()
        
        auth_params = {
            "op": "auth",
            "args": [self.api_key, expires, signature]
        }

        await ws.send_bytes(self.json_encoder.encode(auth_params))

        auth_response = await ws.receive()
        resp = self.json_decoder.decode(auth_response.data)
        
        if resp.get("success", False):
            self.logger.debug("Private data authentication successful")
            return True
        else:
            self.logger.error(f"Private data authentication failed; error: {resp}")
            return False

    async def start(self):
        for attempt in range(3):
            try:
                async with aiohttp.ClientSession() as session, session.ws_connect(WS_PRIVATE_STREAM) as websocket:
                    self.logger.info(f"Private data connection started;")
                    
                    if not await self.authenticate(websocket):
                        raise ConnectionError("Authentication failed;")
                    
                    await websocket.send_bytes(self.json_encoder.encode(self.ws_sub_req))
                    
                    while True:
                        msg = await websocket.receive()
                        
                        if msg.type == aiohttp.WSMsgType.TEXT:
                            recv = self.json_decoder.decode(msg.data)
                            
                            if "success" in recv:
                                self.logger.debug(f"Private data subscription successful; {recv}")
                                continue

                            handler = self.topic_handler_map.get(recv["topic"])
                            if handler:
                                handler(recv)
                            else:
                                self.logger.warning(f"Unknown topic; {recv['topic']}")
                        
                        elif msg.type in [aiohttp.WSMsgType.CLOSED, aiohttp.WSMsgType.ERROR]:
                            self.logger.warning("Private data websocket stale, restarting...")
                            break  
                
                # If we reach here, the loop exited without errors - unlikely but possible
                self.logger.warning("WebSocket loop exited normally, reconnecting...")
                await asyncio.sleep(1)
                continue
                
            except asyncio.CancelledError:
                self.logger.info("Private data feed cancelled; closing connection")
                return
                
            except ConnectionError as ce:
                # Critical errors we want to propagate to the main 
                # loop directly without retrying 
                raise ce
                
            except Exception as e:
                self.logger.error(f"Connection attempt {attempt+1}/3 failed; error: {e}")
                if attempt >= 2:
                    self.logger.error("Maximum reconnection attempts reached; closing connection")
                    raise RuntimeError(f"Failed to connect to private feed after 3 attempts") from e
                
                await asyncio.sleep(1)