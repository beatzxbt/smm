import asyncio
from abc import abstractmethod
from collections.abc import Callable, Awaitable
from typing import Protocol, Self, cast, Any

import aiohttp


class AuthenticationStrategy(Protocol):
    """Protocol for authentication strategies."""

    @abstractmethod
    async def authenticate(self, ws: aiohttp.ClientWebSocketResponse) -> bool:
        """Authenticate the WebSocket connection."""
        ...


class NoAuthenticationStrategy(AuthenticationStrategy):
    """Strategy for unauthenticated connections."""

    async def authenticate(self, ws: aiohttp.ClientWebSocketResponse) -> bool:
        """No authentication needed for public feeds."""
        return True


class WebsocketConnection:
    global_seq_id: int = 0

    def __init__(
        self,
        wss_url: str,
        on_connect: list[bytes],
        auth_strategy: AuthenticationStrategy | None = None,
        *,
        enable_reconnect: bool = True,
        max_reconnect_attempts: int = 3,
        reconnect_base_delay: float = 0.5,
        reconnect_backoff_factor: float = 2.0,
    ):
        """Initialize WebSocket connection."""
        self.wss_url = wss_url
        self.on_connect = on_connect
        self.auth_strategy = auth_strategy or NoAuthenticationStrategy()

        self.ws: aiohttp.ClientWebSocketResponse | None = None

        self.seq_id = 0

        # Reconnection configuration
        self.enable_reconnect = enable_reconnect
        self.max_reconnect_attempts = max_reconnect_attempts
        self.reconnect_base_delay = reconnect_base_delay
        self.reconnect_backoff_factor = reconnect_backoff_factor

        self.is_connected = False

        self._session: aiohttp.ClientSession | None = None
        self._ws_iter = None

    def _increment_seq_id(self) -> None:
        self.seq_id += 1
        self.global_seq_id += 1

    async def connect(self, on_message: Callable[[bytes], Awaitable[None]]) -> None:
        """Connect to WebSocket and stream messages to the provided handler."""
        attempts = 1 if not self.enable_reconnect else max(self.max_reconnect_attempts, 1)
        delay = self.reconnect_base_delay
        backoff = self.reconnect_backoff_factor
        for attempt_idx in range(attempts):
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.ws_connect(self.wss_url) as ws:
                        self.ws = ws
                        self._session = session

                        if not await self.auth_strategy.authenticate(ws):
                            raise RuntimeError(
                                f"Authentication failed; url: {self.wss_url}"
                            )

                        for payload in self.on_connect:
                            await ws.send_bytes(payload)

                        async for msg in ws:
                            self._increment_seq_id()
                            await on_message(self._to_bytes(msg))
                        return
            except aiohttp.WSServerHandshakeError:
                if attempt_idx >= attempts - 1:
                    break
                await asyncio.sleep(delay)
                delay *= backoff
            except asyncio.CancelledError:
                break
        raise RuntimeError(f"Max reconnection attempts reached; url: {self.wss_url}")

    async def __aenter__(self) -> Self:
        """Enter the async context manager, connect and authenticate, and send on_connect payloads."""
        self._session = aiohttp.ClientSession()
        self.ws = await self._session.ws_connect(self.wss_url)

        if not await self.auth_strategy.authenticate(self.ws):
            await self.ws.close()
            await self._session.close()
            raise RuntimeError(f"Authentication failed; url: {self.wss_url}")

        for payload in self.on_connect:
            await self.ws.send_bytes(payload)

        self.is_connected = True
        return self

    async def __aexit__(self, exc_type, exc_value, traceback) -> None:
        if self.ws is not None:
            await self.ws.close()
        if self._session is not None:
            await self._session.close()
        self.is_connected = False

    def __aiter__(self) -> Self:
        """Return the async iterator for messages."""
        if self.ws is None:
            raise RuntimeError(
                "WebSocket connection is not established. Use 'async with' to connect first."
            )
        self._ws_iter = self.ws.__aiter__()
        return self

    async def __anext__(self) -> bytes:
        """Yield the next message from the WebSocket."""
        if self._ws_iter is None:
            raise RuntimeError(
                "WebSocket async iterator not initialized. Use 'async for' after 'async with'."
            )
        msg = await self._ws_iter.__anext__()
        self._increment_seq_id()
        return self._to_bytes(msg)

    def _to_bytes(self, msg: Any) -> bytes:
        """Normalize messages (bytes/str/aiohttp WSMessage) to bytes."""
        # aiohttp.WSMessage has a .data attribute
        data = getattr(msg, "data", msg)
        if isinstance(data, (bytes, bytearray, memoryview)):
            return bytes(data)
        if isinstance(data, str):
            return data.encode("utf-8")
        # Fallback: best-effort string conversion
        return str(data).encode("utf-8")
