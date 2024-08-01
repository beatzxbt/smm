from typing import List, Dict, Any

from frameworks.tools.logging import iso8601_to_unix
from frameworks.exchange.base.ws_handlers.trades import Trade, Trades, TradesHandler
from frameworks.exchange.dydx_v4.types import DydxSideConverter


class DydxTradesHandler(TradesHandler):
    def __init__(self, trades: Trades) -> None:
        super().__init__(trades)

        self.side_converter = DydxSideConverter()

    def refresh(self, recv: Dict[str, Any]) -> None:
        try:
            new_trades: List[Trade] = []
 
            for trade in recv["contents"]["trades"]:
                new_trades.append(Trade(
                    timestamp=iso8601_to_unix(trade["createdAt"]),
                    side=self.side_converter.to_num(trade["side"]),
                    price=float(trade.get("price")),
                    size=float(trade.get("size"))
                ))
            
            self.trades.add_many(new_trades)

        except Exception as e:
            raise Exception(f"Trades refresh - {e}")

    def process(self, recv: Dict[str, Any]) -> None:
        try:
            message_id = recv.get("message_id")

            if message_id == 1:
                self.refresh(recv)
                return None
            
            for trade in recv["contents"]["trades"]:
                self.trades.add_single(Trade(
                    timestamp=iso8601_to_unix(trade["createdAt"]),
                    side=self.side_converter.to_num(trade["side"]),
                    price=float(trade.get("price")),
                    size=float(trade.get("size"))
                ))

        except Exception as e:
            raise Exception(f"Trades process - {e}")
        