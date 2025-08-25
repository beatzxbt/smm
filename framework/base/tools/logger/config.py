from enum import IntEnum


class LogLevel(IntEnum):
    TRACE = 0
    DEBUG = 1
    INFO = 2
    WARNING = 3
    ERROR = 4
    CRITICAL = 5


class LoggerConfig:
    def __init__(
        self,
        base_level: LogLevel = LogLevel.INFO,
        do_stout: bool = True,
        str_format: str = "%(asctime)s [%(levelname)s] %(name)s - %(message)s",
        buffer_capacity: int = 100,
        buffer_timeout: float = 5.0,
    ):
        """
        Initializes the LoggerConfig.

        Args:
            base_level (LogLevel): The minimum log level that will be logged.
                Defaults to LogLevel.INFO.
            buffer_capacity (int): Maximum number of messages in the buffer
                before forcing a flush. Must be > 1. Defaults to 100.
            buffer_timeout (float): Maximum time (in seconds) before forcing
                a buffer flush, even if it's not full. Must be > 0. Defaults to 5.0.
            do_stout (bool): If True, logs are also printed to stdout. Defaults to False.
            str_format (str): The format string for log messages.
                Supports %(asctime)s, %(levelname)s, %(name)s, and %(message)s.
                Defaults to "%(asctime)s [%(levelname)s] %(name)s - %(message)s".

        Raises:
            ValueError: If buffer_capacity is not an int.
            ValueError: If buffer_capacity <= 1 or buffer_timeout <= 0.
            ValueError: If str_format does not contain '%(message)s' placeholder.
        """
        self.base_level = base_level
        self.do_stout = do_stout

        self.buffer_capacity = buffer_capacity
        self.buffer_timeout = buffer_timeout

        if not isinstance(self.buffer_capacity, int):
            raise ValueError(
                f"Invalid buffer capacity; expected int but got {type(self.buffer_capacity)}"
            )

        if self.buffer_capacity < 1:
            raise ValueError(
                f"Invalid buffer capacity; expected >1 but got {self.buffer_capacity}"
            )

        if self.buffer_timeout <= 0.0:
            raise ValueError(
                f"Invalid buffer timeout; expected >0 but got {self.buffer_timeout}"
            )

        self.str_format = str_format

        if "%(message)s" not in self.str_format:
            raise ValueError("Format string must contain '%(message)s' placeholder")
