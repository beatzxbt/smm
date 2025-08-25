import asyncio
import aiohttp
from abc import abstractmethod
from typing import Self, Protocol, Callable, Optional, final, cast


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


@final
class WebsocketConnection:
    global_seq_id: int = 0

    def __init__(
        self,
        wss_url: str,
        on_connect: list[bytes],
        auth_strategy: Optional[AuthenticationStrategy] = None,
    ):
        """Initialize WebSocket connection."""
        self.wss_url = wss_url
        self.on_connect = on_connect
        self.auth_strategy = auth_strategy or NoAuthenticationStrategy()

        self.ws: aiohttp.ClientWebSocketResponse | None = None

        self.seq_id = 0
        self.remaining_reconnect_attempts = 3
        self.reconnect_delay = 0.5

        self.is_connected = False

        self._session: aiohttp.ClientSession | None = None
        self._ws_iter = None

    def _increment_seq_id(self) -> None:
        self.seq_id += 1
        type(self).global_seq_id += 1

    async def connect(self, on_message: Callable[[bytes], None]) -> None:
        """Connect to WebSocket and handle authentication if needed."""
        attempts = self.remaining_reconnect_attempts
        delay = self.reconnect_delay
        for _ in range(attempts):
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
                            await on_message(msg)
                        return
            except aiohttp.WSServerHandshakeError:
                await asyncio.sleep(delay)
                delay *= 2.0
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
        return cast(bytes, msg)
