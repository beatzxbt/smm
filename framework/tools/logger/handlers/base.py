import asyncio
import msgspec
import aiohttp
from abc import ABC, abstractmethod

from mm_toolbox.logging.standard.config import LoggerConfig

class BaseLogHandler(ABC):
    """
    Abstract base class for log handlers, defining how log messages 
    should be pushed to their respective destinations.
    """
    def __init__(self):
        self._json_encode = None
        self._http_session = None
        self._ev_loop = None
        self._primary_config = None

    @property
    def json_encode(self):
        """Lazily initialize the JSON encoder."""
        if self._json_encode is None:
            self._json_encode = msgspec.json.Encoder().encode
        return self._json_encode

    @property
    def http_session(self):
        """Lazily initialize the HTTP session."""
        if self._http_session is None:
            self._http_session = aiohttp.ClientSession()
        return self._http_session

    @property
    def ev_loop(self):
        """Lazily initialize the event loop."""
        if self._ev_loop is None:
            try:
                self._ev_loop = asyncio.get_event_loop()
            except RuntimeError:
                # If there's no event loop in the current context, create one
                self._ev_loop = asyncio.new_event_loop()
                asyncio.set_event_loop(self._ev_loop)
        return self._ev_loop

    @property
    def primary_config(self):
        """Get the primary config."""
        return self._primary_config
    
    def add_primary_config(self, config: LoggerConfig):
        """
        Add the primary configuration to the handler.
        """
        self._primary_config = config

    def __del__(self):
        """Clean up resources when the handler is garbage collected."""
        if self._http_session is not None and not self._http_session.closed:
            try:
                if self._ev_loop is None or self._ev_loop.is_closed():
                    loop = asyncio.new_event_loop()
                    loop.run_until_complete(self._http_session.close())
                    loop.close()
                else:
                    if asyncio.get_event_loop_policy().get_event_loop().is_running():
                        asyncio.create_task(self._http_session.close())
                    else:
                        self._ev_loop.run_until_complete(self._http_session.close())
            except Exception:
                # Suppress exceptions during cleanup
                pass

    @abstractmethod
    async def push(self, buffer: list[str]) -> None:
        """
        Flushes the given buffer of log entries in some way.

        Args:
            buffer (list[str]): The list of log messages to push.
        """
        pass