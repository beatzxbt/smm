from typing import List, Dict, Any

from frameworks.exchange.base.constants import Side
from frameworks.exchange.base.ws_handlers.trades import Trade, Trades, TradesHandler


class BinanceTradesHandler(TradesHandler):
    def __init__(self, trades: Trades) -> None:
        super().__init__(trades)

    def refresh(self, recv: List[Dict]) -> None:
        try:
            new_trades: List[Trade] = []
 
            for trade in recv:
                new_trades.append(Trade(
                    timestamp=float(trade.get("time")),
                    side=Side.SELL if trade.get("isBuyerMaker") else Side.BUY,
                    price=float(trade.get("price")),
                    size=float(trade.get("qty"))
                ))
            
            self.trades.add_many(new_trades)

        except Exception as e:
            raise Exception(f"Trades refresh - {e}")

    def process(self, recv: Dict[str, Any]) -> None:
        try:
            self.trades.add_single(Trade(
                timestamp=float(recv.get("T")),
                side=Side.SELL if recv.get("m") else Side.BUY,
                price=float(recv.get("p")),
                size=float(recv.get("q"))
            ))

        except Exception as e:
            raise Exception(f"Trades process - {e}")
