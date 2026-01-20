# Contributing

## Before Submitting a PR

Run the following command to format code and check types:

```bash
make fix
```

This runs `ruff format`, `ruff check --fix`, and `ty check` across the codebase. All issues must be resolved before submitting.

## Code Style

### Docstrings

All code must use **Google-style docstrings**.

**File Headers**: Every source file must begin with a concise header docstring summarizing its purpose:

```python
"""HTTP client implementation for Bybit REST API.

Provides authenticated and public request handling with automatic
retry logic and rate limiting.
"""
from __future__ import annotations
```

**Functions and Classes**:

```python
def calculate_mid_price(bid: float, ask: float) -> float:
    """Calculate the mid-price between bid and ask.

    Args:
        bid: Best bid price.
        ask: Best ask price.

    Returns:
        The arithmetic mean of bid and ask prices.

    Raises:
        ValueError: If bid exceeds ask (crossed market).
    """
    if bid > ask:
        raise ValueError("Crossed market: bid > ask")
    return (bid + ask) / 2
```

### Comments

- Docstrings handle most documentation; avoid over-commenting
- Add comments only for inherently complex logic
- Limit to one comment per code block

## Testing

### Philosophy

Tests use **static mock responses** to simulate exchange API behavior. This approach (inspired by [CCXT](https://github.com/ccxt/ccxt)) provides:

- Fast, deterministic test execution
- No network dependencies or rate limits
- Ability to test edge cases with crafted responses
- Reproducible CI builds

### Directory Structure

Test files mirror the source directory structure:

```
framework/
├── base/
│   ├── trading/
│   │   ├── client.py
│   │   └── exchange.py
│   └── stream/
│       └── market.py
├── bybit/
│   └── trading/
│       └── client.py
└── binance/
    └── ...

tests/
├── conftest.py
└── framework/
    ├── base/
    │   ├── trading/
    │   │   ├── test_base_client.py
    │   │   └── test_base_exchange.py
    │   └── stream/
    │       └── test_base_stream.py
    ├── bybit/
    │   ├── conftest.py
    │   └── trading/
    │       └── test_bybit_trading_client.py
    └── binance/
        └── ...
```

### Mock Responses as Raw Bytes

Mock API responses by capturing the **raw bytes** returned from the exchange. Store these as byte literals or dicts that get encoded, then inject them via dummy session/response classes:

```python
# Raw bytes captured from actual Bybit API response
ORDERBOOK_RESPONSE = b'{"retCode":0,"retMsg":"OK","result":{"s":"BTCUSDT","b":[["50000.00","1.5"]],"a":[["50000.50","1.0"]],"ts":1234567890000,"u":12345}}'

# Or as a dict that gets encoded during test
TICKER_RESPONSE = {
    "retCode": 0,
    "retMsg": "OK",
    "result": {"symbol": "BTCUSDT", "lastPrice": "50000.00"}
}


class DummyResponse:
    """Mock HTTP response returning raw bytes."""

    def __init__(self, payload: bytes | dict) -> None:
        self._payload = payload

    async def read(self) -> bytes:
        if isinstance(self._payload, bytes):
            return self._payload
        return msgspec.json.encode(self._payload)

    def raise_for_status(self) -> None:
        pass


class DummySession:
    """Mock aiohttp session for HTTP client tests."""

    def __init__(self, payload: bytes | dict) -> None:
        self._payload = payload

    def request(self, **_kwargs):
        return DummyResponse(self._payload)
```

Use in tests:

```python
class TestBybitHttpClient:
    """Layer 2: Request/response handling."""

    @pytest.mark.asyncio
    async def test_fetch_orderbook(self):
        client = BybitHttpClient(logger=Logger(name="test"), load_secrets=False)
        client._session = DummySession(ORDERBOOK_RESPONSE)

        result = await client.fetch_orderbook("BTCUSDT")

        assert result.bids[0].price == 50000.00
```

### Layered Test Structure

Tests follow a layered, class-based structure mirroring component dependencies:

**Layer 1 – Primitives**: Test standalone components in isolation (dataclasses, configs, value objects). Each primitive gets its own test class.

**Layer 2 – Composites**: Test components that consume primitives. Verify integration and business logic.

**Layer 3 – Integration**: Exercise realistic usage patterns combining multiple components.

```python
class TestOrderStruct:
    """Layer 1: Order dataclass validation."""

    def test_valid_order(self):
        ...

    def test_invalid_quantity_raises(self):
        ...


class TestOrderManager:
    """Layer 2: Order manager using Order structs."""

    def test_submit_order(self):
        ...


class TestTradingFlow:
    """Layer 3: Full order lifecycle."""

    def test_place_and_cancel(self):
        ...
```

### Guidelines

- Capture real API responses as raw bytes when adding new test cases
- Test exhaustively: edge cases, boundary values, invalid inputs
- Skip pointless tests for impossible scenarios
- Focus on behavior: validation logic, business rules, state transitions
- Assume the type checker catches type errors; don't test type validation unless runtime checks exist

## Workflow

1. Create a feature branch: `git checkout -b feature/your-feature`
2. Make changes
3. Run `make fix` to format and typecheck
4. Run `make test` to verify all tests pass
5. Submit PR for review
