import hmac
import hashlib
import msgspec
import aiohttp
import asyncio
from typing import Optional

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
    OrderMsg
)

WS_PUBLIC_STREAM = "wss://ws.okx.com:8443/ws/v5/public"
WS_PRIVATE_STREAM = "wss://ws.okx.com:8443/ws/v5/private"

class OkxMarketData(BaseMarketData):
    def __init__(self, symbols: list[str], logger: Logger, consumer_queues: list[asyncio.Queue]) -> None:
        super().__init__(symbols, logger, consumer_queues)

        self.ws_sub_req = {
            "op": "subscribe", 
            "args": [
                item for symbol in self.symbols 
                for item in [
                    {
                        "channel": "tickers",
                        "instId": symbol
                    },
                    {
                        "channel": "books",
                        "instId": symbol
                    },
                    {
                        "channel": "trades",
                        "instId": symbol
                    }
                ]
            ]
        }

        self.topic_handler_map = {}
        for symbol in self.symbols:
            self.topic_handler_map.update({
                f"tickers:{symbol}": self.process_ticker,
                f"books:{symbol}": self.process_orderbook,
                f"trades:{symbol}": self.process_trade
            })
        
        # OKX sends partial ticker data sometimes, so we store a snapshot
        # of all ticker data to copy from in the handler.
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

    async def process_ticker(self, data):
        try:
            channel = data["arg"]["channel"]
            symbol = data["arg"]["instId"]
            time = int(data["data"][0]["ts"])
            ticker_data = data["data"][0]
            
            # Copy from the latest ticker data for this symbol
            latest_msg = self.latest_ticker_data[symbol]
            latest_msg.time = time

            # Update the existing ticker object with new data
            if "markPx" in ticker_data:
                latest_msg.mark_px = float(ticker_data["markPx"])
            if "idxPx" in ticker_data:
                latest_msg.index_px = float(ticker_data["idxPx"])
            if "fundingRate" in ticker_data:
                latest_msg.funding_rate = float(ticker_data["fundingRate"])
            if "nextFundingTime" in ticker_data:
                latest_msg.funding_time = float(ticker_data["nextFundingTime"])
            if "volCcy24h" in ticker_data:
                latest_msg.adv = float(ticker_data["volCcy24h"])
            if "change24h" in ticker_data:
                latest_msg.px_chg_24h = float(ticker_data["change24h"])
            if "openInterest" in ticker_data:
                latest_msg.oi = float(ticker_data["openInterest"])
            
            self.broadcast(latest_msg)
            self.logger.trace(f"Ticker data received; {latest_msg}")
                
        except Exception as e:
            self.logger.error(f"Error processing Ticker data; {e}")
            self.logger.debug(f"Raw ticker data; {data}")

    async def process_orderbook(self, data):
        try:
            symbol = data["arg"]["instId"]
            time = int(data["data"][0]["ts"])
            orderbook_data = data["data"][0]
            
            bids = [[float(price), float(qty)] for price, qty in orderbook_data.get("bids", [])]
            asks = [[float(price), float(qty)] for price, qty in orderbook_data.get("asks", [])]
            
            # Determine if this is a BBO update or a snapshot
            is_bbo = len(bids) <= 1 and len(asks) <= 1
            is_snapshot = "action" in orderbook_data and orderbook_data["action"] == "snapshot"

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

    async def process_trade(self, data):
        try:
            symbol = data["arg"]["instId"]
            time = int(data["data"][0]["ts"])
            trade_data = data["data"]
            trades: list[Trade] = []

            for event in trade_data:
                trade = Trade(
                    time=float(event["ts"]),
                    px=float(event["px"]),
                    is_buy=event["side"] == "buy",
                    sz=float(event["sz"]),
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
                            
                            if "event" in recv and recv["event"] == "subscribe":
                                self.logger.debug(f"Market data subscription successful; {recv}")
                                continue

                            if "arg" in recv and "channel" in recv["arg"] and "instId" in recv["arg"]:
                                channel = recv["arg"]["channel"]
                                symbol = recv["arg"]["instId"]
                                handler = self.topic_handler_map.get(f"{channel}:{symbol}")
                                if handler:
                                    await handler(recv)
                                else:
                                    self.logger.warning(f"Unknown topic; {channel}:{symbol}")
                            else:
                                self.logger.warning(f"Unexpected message format: {recv}")
                        
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

class OkxPrivateData(BasePrivateData):
    """
    Handles private data streams from OKX WebSocket API.
    Manages connection, subscription, and processing of private data like orders and positions.
    """
    def __init__(self, api_key: str, api_secret: str, symbols: list[str], logger: Logger, consumer_queues: list[asyncio.Queue], passphrase: str):
        super().__init__(api_key, api_secret, symbols, logger, consumer_queues)
        self.passphrase = passphrase

        self.ws_sub_req = {
            "op": "subscribe",
            "args": [
                item for symbol in self.symbols 
                for item in [
                    {
                        "channel": "orders",
                        "instType": "SWAP",
                        "instId": symbol
                    },
                    {
                        "channel": "positions",
                        "instType": "SWAP",
                        "instId": symbol
                    },
                    {
                        "channel": "account"
                    }
                ]
            ]
        }

        self.topic_handler_map = {}
        for symbol in self.symbols:
            self.topic_handler_map.update({
                f"orders:{symbol}": self.process_order,
                f"positions:{symbol}": self.process_position,
            })
        
        self.topic_handler_map["account"] = self.process_account
        
        # Track position age for each symbol
        self.position_age_map = {symbol: 0.0 for symbol in self.symbols}

    async def process_order(self, data):
        try:
            for order_data in data["data"]:
                symbol = order_data["instId"]

                if symbol not in self.symbols:
                    continue

                msg = OrderMsg(
                    symbol=symbol,
                    time=float(order_data["uTime"]),
                    create_time_ms=float(order_data["cTime"]),
                    oid=order_data["ordId"],
                    cloid=order_data.get("clOrdId", ""),
                    px=float(order_data.get("px", 0)),
                    is_buy=order_data["side"] == "buy",
                    sz=float(order_data.get("sz", 0)),
                    sz_rem=float(order_data.get("fillSz", 0)),
                    tif=order_data.get("tgtCcy", ""),
                    is_cancelled=order_data.get("state", "") in ["filled", "canceled"],
                    is_reduce_only=order_data.get("reduceOnly", False),
                )

                self.broadcast(msg)
                self.logger.trace(f"Order data received; {msg}")

        except Exception as e:
            self.logger.error(f"Error processing order data: {e}")
            self.logger.debug(f"Raw order data; {data}")

    async def process_position(self, data):
        try:
            for position_data in data["data"]:
                symbol = position_data["instId"]

                if symbol not in self.symbols:
                    continue
                
                # OKX does not give the immediate age of the position, so we 
                # track it from the first non-zero size update.
                prev_size = self.position_age_map[symbol]
                new_size = float(position_data.get("pos", 0))

                if prev_size == 0 and new_size != 0:
                    self.position_age_map[symbol] = float(position_data["uTime"])
                elif new_size == 0:
                    self.position_age_map[symbol] = 0.0

                msg = PositionMsg(
                    symbol=symbol,
                    time=float(position_data["uTime"]),
                    px=float(position_data.get("avgPx", 0)),
                    is_long=position_data.get("posSide", "") == "long",
                    sz=abs(float(position_data.get("pos", 0))),
                    age=float(position_data["uTime"]) - self.position_age_map[symbol],
                )

                self.broadcast(msg)
                self.logger.trace(f"Position data received; {msg}")

        except Exception as e:
            self.logger.error(f"Error processing position data: {e}")
            self.logger.debug(f"Raw position data; {data}")

    async def process_execution(self, data):
        try:
            for execution_data in data["data"]:
                symbol = execution_data["instId"]

                if symbol not in self.symbols:
                    continue
                
                msg = ExecutionMsg(
                    symbol=symbol,
                    time=float(execution_data["fillTime"]),  
                    px=float(execution_data["fillPx"]),
                    is_buy=execution_data["side"] == "buy",
                    sz=float(execution_data["fillSz"]),
                    is_maker=execution_data.get("execType", "") == "M",
                    fee_paid=float(execution_data.get("fillFee", 0))
                )

                self.broadcast(msg)
                self.logger.trace(f"Execution data received; {msg}")

        except Exception as e:
            self.logger.error(f"Error processing execution data: {e}")
            self.logger.debug(f"Raw execution data; {data}")

    async def process_account(self, data):
        try:
            for account_data in data["data"]:
                msg = AccountMsg(
                    time=time_s(),
                    bal=float(account_data.get("totalEq", 0)),
                    im=float(account_data.get("imr", 0)),
                    mm=float(account_data.get("mmr", 0)),
                    uPnl=float(account_data.get("upl", 0))
                )

                self.broadcast(msg)
                self.logger.trace(f"Account data received; {msg}")

        except Exception as e:
            self.logger.error(f"Error processing account data: {e}")
            self.logger.debug(f"Raw account data; {data}")

    def get_signature(self, timestamp: str, method: str, request_path: str, body: str = ''):
        message = timestamp + method + request_path + body
        mac = hmac.new(
            bytes(self.api_secret, encoding='utf8'),
            bytes(message, encoding='utf-8'),
            digestmod='sha256'
        )
        return mac.hexdigest()

    async def authenticate(self, ws):
        timestamp = str(int(time_ms()))
        signature = self.get_signature(timestamp, 'GET', '/users/self/verify')
        
        auth_params = {
            "op": "login",
            "args": [{
                "apiKey": self.api_key,
                "passphrase": self.passphrase,
                "timestamp": timestamp,
                "sign": signature
            }]
        }

        await ws.send_bytes(self.json_encoder.encode(auth_params))

        auth_response = await ws.receive()
        resp = self.json_decoder.decode(auth_response.data)
        
        if resp.get("code") == "0" and resp.get("event") == "login":
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
                            
                            if "event" in recv and recv["event"] == "subscribe":
                                self.logger.debug(f"Private data subscription successful; {recv}")
                                continue

                            if "arg" in recv and "channel" in recv["arg"]:
                                channel = recv["arg"]["channel"]
                                
                                if channel == "account":
                                    handler = self.topic_handler_map.get(channel)
                                    if handler:
                                        await handler(recv)
                                elif "instId" in recv["arg"]:
                                    symbol = recv["arg"]["instId"]
                                    handler = self.topic_handler_map.get(f"{channel}:{symbol}")
                                    if handler:
                                        await handler(recv)
                                    else:
                                        self.logger.warning(f"Unknown topic; {channel}:{symbol}")
                                else:
                                    self.logger.warning(f"Unexpected message format: {recv}")
                            else:
                                self.logger.warning(f"Unexpected message format: {recv}")
                        
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