import sys
import traceback
import asyncio
from typing import Optional

from framework.base.tools.time import time_iso8601, time_s
from framework.base.tools.logger.config import LogLevel, LoggerConfig
from framework.base.tools.logger.handlers import BaseLogHandler


class Logger:
    """
    A simple asynchronous logger that buffers messages and pushes them to
    configured handlers at an appropriate time or based on severity.
    """

    def __init__(
        self,
        config: LoggerConfig = None,
        name: str = "",
        handlers: Optional[list[BaseLogHandler]] = None,
    ):
        """
        Initializes a Logger with specified configuration and handlers.

        Args:
            config (LoggerConfig): Configuration settings for the logger (base level, stdout, buffer size, etc.).
            name (str): Name of the logger. Defaults to an empty string.
            handlers (list[BaseLogHandler], optional): A list of handler objects that inherit from BaseLogHandler.
                Defaults to an empty list if not provided.

        Raises:
            TypeError: If one of the provided handlers does not inherit from LogHandler.
        """
        self._config = config
        if self._config is None:
            self._config = LoggerConfig()

        self._name = name

        self._handlers = handlers
        if self._handlers is None:
            self._handlers = []

        for handler in self._handlers:
            handler_base_class = handler.__class__.__base__
            if not handler_base_class == BaseLogHandler:
                raise TypeError(
                    f"Invalid handler base class; expected BaseLogHandler but got {handler_base_class}"
                )

            # Mainly for forwarding the str_format to the handler for formatting log messages
            # where the final point is not a code environment (eg Discord, Telegram, etc).
            handler.add_primary_config(config)

        self._buffer_size = 0
        self._buffer: list[str] = [None] * self._config.buffer_capacity
        self._buffer_start_time = time_s()

        self._msg_queue = asyncio.Queue()
        self._ev_loop = asyncio.get_event_loop()
        self._is_running = True

        # Start the log ingestor task.
        self._log_ingestor_task = self._ev_loop.create_task(self._log_ingestor())

    async def _flush_buffer(self):
        """
        Flushes the log message buffer to all handlers.
        """
        for handler in self._handlers:
            await handler.push(self._buffer[: self._buffer_size])

        self._buffer_size = 0
        self._buffer_start_time = time_s()

    async def _log_ingestor(self):
        """
        Asynchronous loop that ingests log messages from the queue and flushes
        them based on severity or buffer fullness.

        Raises:
            Exception: If an error occurs during the log writing process.
        """
        while self._is_running or not self._msg_queue.empty():
            try:
                # (log_msg: str, level: LogLevel)
                log_msg, level = await self._msg_queue.get()

                self._buffer[self._buffer_size] = log_msg
                self._buffer_size += 1

                if self._config.do_stout:
                    print(log_msg)

                # Immediate buffer flush for ERROR or higher.
                if level.value >= LogLevel.ERROR.value:
                    await self._flush_buffer()
                else:
                    # For lower severity, flush if buffer is full or timed out.
                    is_buffer_full = self._buffer_size >= self._config.buffer_capacity
                    is_buffer_expired = (
                        time_s() - self._buffer_start_time
                    ) >= self._config.buffer_timeout

                    if is_buffer_full or is_buffer_expired:
                        await self._flush_buffer()

                self._msg_queue.task_done()

            except Exception:
                traceback.print_exc(file=sys.stderr)

        if self._is_running:
            return

    def _process_log(self, level: LogLevel, msg: str):
        """
        Submits a log message to the queue if it meets the minimum base level.

        Args:
            level (LogLevel): The severity level of the message.
            msg (str): The actual log message.
        """
        try:
            log_msg = self._config.str_format % {
                "asctime": time_iso8601(),
                "name": self._name,
                "levelname": level.name,
                "message": msg,
            }
            self._msg_queue.put_nowait((log_msg, level))
        except Exception:
            traceback.print_exc(file=sys.stderr)

    def set_format(self, format_string: str) -> None:
        """
        Modify the format string for log messages in runtime.

        Args:
            format_string (str): The new format string.
                Supports {timestamp}, {level}, and {message} placeholders.
        """
        self.debug(
            f"Changing format string from {self._config.str_format} to {format_string}"
        )
        self._config.str_format = format_string
        for handlers in self._handlers:
            handlers.add_primary_config(self._config)

    def set_log_level(self, level: LogLevel) -> None:
        """
        Modify the logger's base log level at runtime.

        Args:
            level (LogLevel): The new base log level.
        """
        self.debug(f"Changing base log level from {self._config.base_level} to {level}")
        self._config.base_level = level
        for handlers in self._handlers:
            handlers.add_primary_config(self._config)

    def trace(self, msg: str) -> None:
        """
        Send a trace-level log message.

        Args:
            msg (str): The log message text.
        """
        valid_level = self._config.base_level == LogLevel.TRACE
        if self._is_running and valid_level:
            self._process_log(LogLevel.TRACE, msg)

    def debug(self, msg: str) -> None:
        """
        Send a debug-level log message.

        Args:
            msg (str): The log message text.
        """
        valid_level = self._config.base_level <= LogLevel.DEBUG
        if self._is_running and valid_level:
            self._process_log(LogLevel.DEBUG, msg)

    def info(self, msg: str) -> None:
        """
        Send an info-level log message.

        Args:
            msg (str): The log message text.
        """
        valid_level = self._config.base_level <= LogLevel.INFO
        if self._is_running and valid_level:
            self._process_log(LogLevel.INFO, msg)

    def warning(self, msg: str) -> None:
        """
        Send a warning-level log message.

        Args:
            msg (str): The log message text.
        """
        valid_level = self._config.base_level <= LogLevel.WARNING
        if self._is_running and valid_level:
            self._process_log(LogLevel.WARNING, msg)

    def error(self, msg: str) -> None:
        """
        Send an error-level log message.

        Args:
            msg (str): The log message text.
        """
        valid_level = self._config.base_level <= LogLevel.ERROR
        if self._is_running and valid_level:
            self._process_log(LogLevel.ERROR, msg)

    def critical(self, msg: str) -> None:
        """
        Send a critical-level log message.

        Args:
            msg (str): The log message text.
        """
        valid_level = self._config.base_level <= LogLevel.CRITICAL
        if self._is_running and valid_level:
            self._process_log(LogLevel.CRITICAL, msg)

    async def shutdown(self):
        """
        Shuts down the logger, ensuring all buffered messages are flushed
        and handlers are closed.
        """
        # Let the log ingestor finish ingesting all the logs.
        # Shutdown flag automatically kills it once the queue is empty.
        self._is_running = False
        await self._msg_queue.join()

        if self._buffer_size > 0:
            await self._flush_buffer()
            self._buffer.clear()

    def is_running(self) -> bool:
        """
        Check if the master logger is running.
        """
        return self._is_running

    def get_name(self) -> str:
        """
        Get the name of the master logger.
        """
        return self._name

    def get_config(self) -> LoggerConfig:
        """
        Get the configuration of the master logger.
        """
        return self._config

    # def get_system_info(self) -> dict:
    #     """
    #     Get the system information of the master logger.
    #     """
    #     return self._system_info
