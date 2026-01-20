"""Trader registry and public exports.

Usage: call `load_trader()` to resolve a trader class by id.
Components: registry, trader class exports, loader helper.
"""

from __future__ import annotations

from smm.config import TraderId
from smm.traders.base.trader import BaseTrader
from smm.traders.plain.trader import PlainTrader
from smm.traders.stinky.trader import StinkyTrader


def load_trader(trader_id: TraderId) -> type[BaseTrader]:
    """Resolve a trader class from the configured identifier.

    Args:
        trader_id (TraderId): Trader identifier from configuration.

    Returns:
        type[BaseTrader]: Trader class implementing the chosen strategy.
    """
    match trader_id:
        case TraderId.PLAIN:
            return PlainTrader
        case TraderId.STINKY:
            return StinkyTrader
        case _:
            raise ValueError(f"Unknown trader id: {trader_id}")


__all__ = ["BaseTrader", "PlainTrader", "StinkyTrader", "load_trader"]
