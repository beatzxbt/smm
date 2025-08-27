from enum import IntEnum
from msgspec import Struct

from framework.base.tools.time import unix_to_iso8601


class LogLevel(IntEnum):
    TRACE = 0
    DEBUG = 1
    INFO = 2
    WARNING = 3
    ERROR = 4


class Log(Struct, frozen=True):
    time_ns: int
    level: LogLevel
    message: str

    def format(self, name: str, format_string: str) -> str:
        return format_string.format(
            asctime=unix_to_iso8601(self.time_ns),
            level=self.level,
            name=name,
            message=self.message,
        )
