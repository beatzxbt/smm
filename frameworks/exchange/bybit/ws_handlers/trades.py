from typing import List, Dict, Any

from frameworks.exchange.base.ws_handlers.trades import Trade, Trades, TradesHandler
from frameworks.exchange.bybit.types import BybitSideConverter


class BybitTradesHandler(TradesHandler):
    def __init__(self, trades: Trades) -> None:
        super().__init__(trades)

        self.side_converter = BybitSideConverter()

    def refresh(self, recv: List[Dict]) -> None:
        try:
            new_trades: List[Trade] = []
 
            for trade in recv:
                new_trades.append(Trade(
                    timestamp=float(trade.get("time")),
                    side=self.side_converter.to_num(trade["side"]),
                    price=float(trade.get("price")),
                    size=float(trade.get("size"))
                ))
            
            self.trades.add_many(new_trades)

        except Exception as e:
            raise Exception(f"Trades refresh - {e}")

    def process(self, recv: Dict[str, Any]) -> None:
        try:
            for trade in recv["data"]:
                self.trades.add_single(Trade(
                    timestamp=float(trade.get("T")),
                    side=self.side_converter.to_num(trade["S"]),
                    price=float(trade.get("p")),
                    size=float(trade.get("v"))
                ))

        except Exception as e:
            raise Exception(f"Trades process - {e}")
