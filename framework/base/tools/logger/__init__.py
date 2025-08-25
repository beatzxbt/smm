# this is copy pasted from the mm_toolbox v1.0, which isnt out yet
# so we need to keep it here for now. upon release, this should be
# in the files to simply import 'from mm_toolbox.logging.standard import *'

from .logger import (
    Logger as Logger,
)

from .config import (
    LogLevel as LogLevel,
    LoggerConfig as LoggerConfig,
)

from .handlers import (
    BaseLogHandler as BaseLogHandler,
    FileLogHandler as FileLogHandler,
    DiscordLogHandler as DiscordLogHandler,
    TelegramLogHandler as TelegramLogHandler,
)

__all__ = [
    "Logger",
    "LogLevel",
    "LoggerConfig",
    "BaseLogHandler",
    "FileLogHandler",
    "DiscordLogHandler",
    "TelegramLogHandler",
]
