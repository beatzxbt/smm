"""tests.conftest"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

# Ensure project root is importable during tests
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


@pytest.fixture
def test_logger():
    """Logger for testing - available to all tests.

    Returns:
        Logger: Test logger with WARNING level to reduce noise.
    """
    from mm_toolbox.logging.standard import Logger
    from mm_toolbox.logging.standard.config import LoggerConfig, LogLevel

    config = LoggerConfig(base_level=LogLevel.WARNING, do_stdout=False)
    return Logger(name="test", config=config)


@pytest.fixture
def mock_http_response():
    """Factory for creating mock HTTP responses.

    Returns:
        Callable: Function that creates mock aiohttp responses with specified
            status, JSON data, or exceptions.

    Example:
        mock_resp = mock_http_response(status=200, json_data={"key": "value"})
        mock_resp = mock_http_response(raises=aiohttp.ClientError())
    """

    def _make_response(
        status: int = 200,
        json_data: dict | None = None,
        raises: Exception | None = None,
    ):
        from unittest.mock import AsyncMock

        import msgspec

        mock_resp = AsyncMock()
        mock_resp.status = status
        if raises:
            mock_resp.read = AsyncMock(side_effect=raises)
        else:
            mock_resp.read = AsyncMock(
                return_value=msgspec.json.encode(json_data or {})
            )
        mock_resp.raise_for_status = lambda: None
        return mock_resp

    return _make_response


@pytest.fixture
def mock_ws():
    """Generic WebSocket mock for all tests.

    Returns:
        AsyncMock: Mock aiohttp.ClientWebSocketResponse with common methods.
    """
    from unittest.mock import AsyncMock

    import aiohttp

    ws = AsyncMock(spec=aiohttp.ClientWebSocketResponse)
    ws.closed = False
    ws.send_bytes = AsyncMock()
    ws.send_str = AsyncMock()
    ws.receive = AsyncMock()
    ws.close = AsyncMock()
    return ws
