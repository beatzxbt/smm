import sys
import time
import traceback
import threading
from typing import Optional
from collections import deque

from framework.base.tools.time import time_s, time_ns
from framework.base.tools.logger.config import LoggerConfig
from framework.base.tools.logger.handlers import BaseLogHandler
from framework.base.tools.logger.structs import Log, LogLevel


class Logger:
    """
    A simple asynchronous logger that buffers messages and pushes them to
    configured handlers at an appropriate time or based on severity.
    """

    def __init__(
        self,
        name: str = "",
        config: LoggerConfig = None,
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
        self._name = name
        self._config = LoggerConfig.default() if config is None else config
        self._handlers = [] if handlers is None else handlers

        for handler in self._handlers:
            handler_base_class = handler.__class__.__base__
            if not handler_base_class == BaseLogHandler:
                raise TypeError(
                    f"Invalid handler base class; expected BaseLogHandler but got {handler_base_class}"
                )

            # Mainly for forwarding the str_format to the handler for formatting log messages
            # where the final point is not a code environment (eg Discord, Telegram, etc).
            handler.add_primary_config(self._config)

        self._buffer_size = 0
        self._buffer: list[Log] = []

        self._is_running = True
        self._queue: deque[Log] = deque()

        # Start the log ingestor task.
        self._timed_operations_thread = threading.Thread(
            target=self._timed_operations, daemon=True
        )
        self._timed_operations_thread.start()

    def _timed_operations(self):
        is_last_iteration = False
        next_expiry_time_s = time_s() + self._config.buffer_timeout_s

        while self._is_running or is_last_iteration:
            try:
                time.sleep(0.1)

                while len(self._queue) > 0:
                    log = self._queue.popleft()
                    self._buffer.append(log)
                    self._buffer_size += 1

                    if self._config.to_console:
                        print(log.format(self._name, self._config.str_format))

                if time_s() >= next_expiry_time_s:
                    for handler in self._handlers:
                        handler.push(self._buffer[: self._buffer_size])

                    self._buffer_size = 0
                    next_expiry_time_s += self._config.buffer_timeout_s

                # Loop just once more at the end of the logger lifecycle.
                if not self._is_running:
                    is_last_iteration = True
                if is_last_iteration:
                    break

            except Exception:
                traceback.print_exc(file=sys.stderr)

    def trace(self, msg: str) -> None:
        """Send a trace-level log message."""
        if not self._is_running:
            return

        log = Log(
            time_ns=time_ns(),
            level=LogLevel.TRACE,
            message=msg,
        )
        self._queue.append(log)

    def debug(self, msg: str) -> None:
        """
        Send a debug-level log message.
        """
        if not self._is_running:
            return

        if LogLevel.DEBUG >= self._config.base_level:
            log = Log(
                time_ns=time_ns(),
                level=LogLevel.DEBUG,
                message=msg,
            )
            self._queue.append(log)

    def info(self, msg: str) -> None:
        """Send an info-level log message."""
        if not self._is_running:
            return

        if LogLevel.INFO >= self._config.base_level:
            log = Log(
                time_ns=time_ns(),
                level=LogLevel.INFO,
                message=msg,
            )
            self._queue.append(log)

    def warning(self, msg: str) -> None:
        """
        Send a warning-level log message.
        """
        if not self._is_running:
            return

        if LogLevel.WARNING >= self._config.base_level:
            log = Log(
                time_ns=time_ns(),
                level=LogLevel.WARNING,
                message=msg,
            )
            self._queue.append(log)

    def error(self, msg: str) -> None:
        """
        Send an error-level log message.
        """
        if not self._is_running:
            return

        if LogLevel.ERROR >= self._config.base_level:
            log = Log(
                time_ns=time_ns(),
                level=LogLevel.ERROR,
                message=msg,
            )
            self._queue.append(log)

    def shutdown(self):
        """
        Shuts down the logger, ensuring all buffered messages are flushed
        and handlers are closed.
        """
        # Block any further log messages from being added to the queue.
        self._is_running = False

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
