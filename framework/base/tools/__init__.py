# NOTE: ALL of the tools within this folder will be substituted with mm-toolbox sooner or later.
# If you are looking for better, faster implementations then check out that repository instead.
# Url: https://github.com/beatzxbt/mm-toolbox

from typing import TYPE_CHECKING, Any

from .logger import (
    DiscordLogHandler as DiscordLogHandler,
)
from .logger import (
    FileLogHandler as FileLogHandler,
)
from .logger import (
    Logger as Logger,
)
from .logger import (
    LoggerConfig as LoggerConfig,
)
from .moving_average import ExponentialMovingAverage
from .multiq import consume_multiq as consume_multiq
from .rounder import (
    Rounder as Rounder,
)
from .rounder import (
    RounderConfig as RounderConfig,
)
from .symbol_formatter import format_symbol as format_symbol
from .time import (
    time_ms as time_ms,
)
from .time import (
    time_ns as time_ns,
)
from .time import (
    time_s as time_s,
)
from .websocket import (
    AuthenticationStrategy as AuthenticationStrategy,
)
from .websocket import (
    WebsocketConnection as WebsocketConnection,
)

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
