from framework.base.tools.logger.structs import LogLevel


class LoggerConfig:
    def __init__(
        self,
        base_level: LogLevel,
        to_console: bool,
        str_format: str,
        buffer_timeout_s: float,
    ):
        """Initializes the LoggerConfig.

        Args:
            base_level (LogLevel): The minimum log level that will be logged.
            to_console (bool): If True, logs are also printed to stdout.
            str_format (str): The format string for log messages.
                Supports %(asctime)s, %(levelname)s, %(name)s, and %(message)s.
            buffer_timeout_s (float): Maximum time (in seconds) before forcing
                a buffer flush, even if it's not full. Must be > 0.

        """
        self.base_level = base_level
        self.to_console = to_console

        self.buffer_timeout_s = buffer_timeout_s

        if self.buffer_timeout_s <= 0.0:
            raise ValueError(
                f"Invalid buffer timeout; expected >0 but got {self.buffer_timeout_s}"
            )

        self.str_format = str_format

        if "%(message)s" not in self.str_format:
            raise ValueError("Format string must contain '%(message)s' placeholder")

    @classmethod
    def default(cls) -> "LoggerConfig":
        return cls(
            base_level=LogLevel.INFO,
            to_console=True,
            str_format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
            buffer_timeout_s=5.0,
        )
