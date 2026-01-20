"""Public package API for the simple market maker.

Usage: import config and trader helpers from the package root.
Components: config types, trader registry, and version export.
"""

from __future__ import annotations

from smm.config import AppConfig, TraderId, load_config
from smm.traders import BaseTrader, PlainTrader, StinkyTrader, load_trader


__all__ = [
    "AppConfig",
    "BaseTrader",
    "PlainTrader",
    "StinkyTrader",
    "TraderId",
    "load_config",
    "load_trader",
]

__VERSION__ = "2.0.0"
