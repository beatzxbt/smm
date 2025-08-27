# NOTE: ALL of the tools within this folder will be substituted with mm-toolbox sooner or later.
# If you are looking for better, faster implementations then check out that repository instead.
# Url: https://github.com/beatzxbt/mm-toolbox

from .logger import (
    Logger as Logger,
    LoggerConfig as LoggerConfig,
    FileLogHandler as FileLogHandler,
    DiscordLogHandler as DiscordLogHandler,
)
from .time import (
    time_ms as time_ms,
    time_s as time_s,
    time_ns as time_ns,
)
from .rounder import (
    Rounder as Rounder,
    RounderConfig as RounderConfig,
)
from .multiq import consume_multiq as consume_multiq
from .moving_average import ExponentialMovingAverage
from .websocket import (
    WebsocketConnection as WebsocketConnection,
    AuthenticationStrategy as AuthenticationStrategy,
)
from .symbol_formatter import format_symbol as format_symbol
from typing import TYPE_CHECKING, Any

__all__ = [
    "Logger",
    "LoggerConfig",
    "FileLogHandler",
    "DiscordLogHandler",
    "time_ms",
    "time_s",
    "time_ns",
    "Rounder",
    "RounderConfig",
    "consume_multiq",
    "ExponentialMovingAverage",
    "WebsocketConnection",
    "AuthenticationStrategy",
    "format_symbol",
    "Orderbook",
]
