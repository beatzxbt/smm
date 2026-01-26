"""
Base stream package exports.

Usage: import connection, handlers, managers, and models from this package.
Components: WebSocketConnection, handler base classes, and stream managers.

Note: Managers are NOT exported here to avoid circular imports. Import them
directly from framework.base.stream.manager when needed.
"""

from __future__ import annotations

from framework.base.stream.connection import WebSocketConnection
from framework.base.stream.handlers import (
    BaseStreamHandler,
    BBOStreamHandler,
    OrderbookStreamHandler,
    TickerStreamHandler,
    TradesStreamHandler,
)
from framework.base.stream.models import *  # noqa: F403

__all__ = [
    "WebSocketConnection",
    "BaseStreamHandler",
    "TickerStreamHandler",
    "BBOStreamHandler",
    "OrderbookStreamHandler",
    "TradesStreamHandler",
]
