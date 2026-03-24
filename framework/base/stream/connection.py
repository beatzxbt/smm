"""
WebSocket connection wrapper with reconnect support.

Usage: create WebSocketConnection(url, logger) and use connect/send/async iteration.
Components: connection lifecycle, exponential backoff reconnects, and message normalization.
"""

from __future__ import annotations

import asyncio
from typing import AsyncIterator, Awaitable, Callable

import aiohttp

from mm_toolbox.logging.standard import Logger


ReconnectCallback = Callable[[], Awaitable[None]]


class WebSocketConnection:
    """Low-level websocket connection wrapper with reconnect handling.

    Args:
        url: WebSocket endpoint URL.
        logger: Logger for diagnostics.
        auto_reconnect: Whether to attempt reconnection on disconnects.
        reconnect_delay_s: Base delay in seconds for exponential backoff.
        max_reconnect_attempts: Maximum reconnect attempts before giving up.
    """

    def __init__(
        self,
        url: str,
        logger: Logger,
        auto_reconnect: bool = True,
        reconnect_delay_s: float = 1.0,
        max_reconnect_attempts: int = 5,
    ) -> None:
        """Initialize the websocket connection wrapper.

        Args:
            url: WebSocket endpoint URL.
            logger: Logger for diagnostics.
            auto_reconnect: Whether to attempt reconnection on disconnects.
            reconnect_delay_s: Base delay in seconds for exponential backoff.
            max_reconnect_attempts: Maximum reconnect attempts before giving up.

        """
        self._url = url
        self._logger = logger
        self._auto_reconnect = auto_reconnect
        self._reconnect_delay_s = reconnect_delay_s
        self._max_reconnect_attempts = max_reconnect_attempts

        self._session: aiohttp.ClientSession | None = None
        self._ws: aiohttp.ClientWebSocketResponse | None = None
        self._is_connected = False
        self._closing = False
        self._reconnect_callbacks: list[ReconnectCallback] = []

    @property
    def url(self) -> str:
        """Return the configured websocket endpoint URL.

        Returns:
            str: Current websocket URL.
        """
        return self._url

    @property
    def is_connected(self) -> bool:
        """Return whether the websocket is currently connected.

        Returns:
            bool: True if connected, False otherwise.
        """
        return self._is_connected and self._ws is not None and not self._ws.closed

    def set_url(self, url: str) -> None:
        """Update the websocket endpoint URL used for future connections.

        Args:
            url: New websocket URL.

        Raises:
            ValueError: If the URL is empty.
        """
        if not url:
            raise ValueError("Invalid url; expected non-empty string.")
        self._url = url

    def add_reconnect_callback(self, callback: ReconnectCallback) -> None:
        """Register a callback to run after a reconnect succeeds.

        Args:
            callback: Awaitable callback invoked after reconnection.

        """
        self._reconnect_callbacks.append(callback)

    async def connect(self) -> None:
        """Open the websocket connection."""
        if self.is_connected:
            return
        self._closing = False
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession()
        self._ws = await self._session.ws_connect(self._url)
        self._is_connected = True

    async def disconnect(self) -> None:
        """Close the websocket connection and session."""
        self._closing = True
        self._is_connected = False
        if self._ws is not None and not self._ws.closed:
            await self._ws.close()
        self._ws = None
        if self._session is not None and not self._session.closed:
            await self._session.close()
        self._session = None

    async def send(self, data: bytes) -> None:
        """Send a payload over the websocket.

        Args:
            data: Serialized payload bytes to send.
        """
        ws = self._ws
        if not self.is_connected or ws is None:
            raise ConnectionError("WebSocket is not connected.")
        await ws.send_frame(data, aiohttp.WSMsgType.TEXT)

    async def receive(self) -> bytes | None:
        """Receive a single websocket message payload.

        Returns:
            bytes | None: Raw payload bytes, or None if the socket is closed.
        """
        if not self.is_connected or self._ws is None:
            raise ConnectionError("WebSocket is not connected.")
        msg = await self._ws.receive()
        return self._normalize_message(msg)

    async def __aiter__(self) -> AsyncIterator[bytes]:
        """Yield incoming websocket messages as raw bytes.

        Returns:
            AsyncIterator[bytes]: Iterator over raw websocket payloads.
        """
        while True:
            if self._closing:
                break

            if not self.is_connected:
                try:
                    await self.connect()
                except Exception as exc:
                    self._logger.error(f"WebSocket connect failed; {exc}")
                    if not self._auto_reconnect:
                        break
                    reconnected = await self._reconnect_with_backoff()
                    if not reconnected:
                        break
                    await self._notify_reconnect()

            if self._ws is None:
                break

            try:
                async for msg in self._ws:
                    payload = self._normalize_message(msg)
                    if payload is None:
                        continue
                    yield payload
            except asyncio.CancelledError:
                break
            except Exception as exc:
                self._logger.warning(f"WebSocket receive error; {exc}")

            self._is_connected = False
            if not self._auto_reconnect or self._closing:
                break

            reconnected = await self._reconnect_with_backoff()
            if not reconnected:
                break
            await self._notify_reconnect()

    def _normalize_message(self, msg: aiohttp.WSMessage) -> bytes | None:
        """Normalize aiohttp websocket messages to raw bytes.

        Args:
            msg: WebSocket message from aiohttp.

        Returns:
            bytes | None: Normalized payload bytes or None to skip.
        """
        if msg.type in (aiohttp.WSMsgType.CLOSED, aiohttp.WSMsgType.ERROR):
            self._is_connected = False
            return None
        if msg.type is not aiohttp.WSMsgType.TEXT:
            return None
        data = msg.data
        if isinstance(data, str):
            return data.encode()
        return None

    async def _notify_reconnect(self) -> None:
        """Invoke registered reconnect callbacks."""
        for callback in self._reconnect_callbacks:
            try:
                await callback()
            except Exception as exc:
                self._logger.warning(f"Reconnect callback failed; {exc}")

    async def _reconnect_with_backoff(self) -> bool:
        """Attempt reconnection with exponential backoff.

        Returns:
            bool: True if reconnect succeeds, False otherwise.
        """
        delay = self._reconnect_delay_s
        attempts = 0
        while self._auto_reconnect and not self._closing:
            attempts += 1
            try:
                await asyncio.sleep(delay)
                await self.connect()
                return True
            except Exception as exc:
                self._logger.warning(f"Reconnect attempt {attempts} failed; {exc}")
                if attempts >= self._max_reconnect_attempts:
                    break
                delay *= 2
        return False
