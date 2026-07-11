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

Tests should provide confidence in realistic framework behavior, not maximize the
number of functions, branches, or fields exercised independently.

### Scenario-First Testing

Prefer a small number of substantial behavioral scenarios that exercise the
largest practical portion of a workflow.

A scenario should begin at a public framework boundary and continue through the
real components involved in that operation. Mock or simulate only the external
boundary that the repository does not control, such as an exchange server,
network transport, clock, or operating system.

For example, a market-feed scenario should normally exercise:

```text
scripted exchange traffic
    → WebSocketConnection
    → stream manager
    → venue handlers and decoders
    → normalized models
    → consumer buffer
```

A trading scenario should normally exercise:

```text
Exchange operation
    → venue client and signing
    → scripted HTTP/WebSocket transport
    → response decoding
    → normalized response
```

Do not replace an internal component with a mock merely because doing so makes
the test easier to write. Internal mocks can make a test pass while the actual
components no longer work together.

### Test Realistic Stories

Organize tests around user-visible or operational stories rather than source
files and individual methods.

Good feed scenarios include:

- Subscribe, consume sustained traffic, unsubscribe, and shut down cleanly.
- Process snapshots and deltas while filtering duplicate or stale messages.
- Lose a connection, reconnect, resubscribe, and resume without corrupting state.
- Interleave order, execution, position, and account updates on a private stream.
- Handle control messages and malformed exchange data without losing subsequent
  valid traffic.

Good trading scenarios include:

- Synchronize time, authenticate, create, amend, and cancel an order.
- Fetch market snapshots and normalize them into framework models.
- Reconcile orders, executions, positions, and account state.
- Receive an exchange rejection or transport failure and return the correct
  normalized failure while remaining usable afterward.

Scenarios may process tens or hundreds of messages when message history,
deduplication, ordering, reconnects, or accumulated state are relevant. Message
volume should represent behavior, not serve as an arbitrary stress count.

### Simulate the Exchange Boundary

Tests must remain deterministic and must not depend on live exchange services.

Prefer reusable scripted exchange simulators or captured traffic transcripts.
The simulator should accept real client requests, record their wire
representation, and return realistic raw HTTP or WebSocket payloads.

Where practical, use an in-process HTTP/WebSocket server so that connection,
serialization, signing, routing, decoding, and lifecycle behavior are exercised
together. A lightweight injected transport is acceptable when using a server
would obscure the behavior under test.

Captured payloads should preserve the raw shape returned by the exchange.
Chronological transcripts are preferable to isolated response factories when
message order matters.

### Assertions

Assert externally meaningful outcomes and a few important intermediate
checkpoints:

- Messages delivered to consumers.
- Subscription and lifecycle state.
- Normalized orders, positions, executions, accounts, and market data.
- Externally transmitted requests or subscription frames.
- Recovery after failures.
- Absence of duplicates or stale state.

Avoid assertions against private fields, call counts, or implementation-specific
method ordering unless those details are themselves part of the required
contract.

A good scenario should continue to pass after internal refactoring that preserves
observable behavior.

### When Isolated Tests Are Appropriate

Use an isolated test only when at least one of these applies:

- The behavior is a critical invariant that fails at construction time.
- The logic is algorithmic or has a large input space that scenario tests cannot
  cover clearly.
- Exact cryptographic, serialization, timing, or numerical output is required.
- A rare failure or concurrency condition cannot be reproduced reliably through
  the public boundary.
- Testing through the complete workflow would make the failure materially harder
  to diagnose.

Examples include golden signing vectors, model invariants, time-synchronization
math, reconnect backoff limits, rate limiting, cache semantics, malformed schema
rejection, and concurrency races.

Do not add isolated tests solely because a function, property, branch, enum
value, or response model exists.

### Regression Tests

A bug fix should add the smallest realistic scenario that reproduces the bug at
the highest useful boundary.

Prefer extending an existing scenario or exchange transcript over creating a new
test for the specific internal function that happened to contain the defect.

### Test-Suite Maintenance

Tests are production code and carry maintenance cost.

- Prefer extending a coherent scenario over adding another test file.
- Remove isolated tests whose behavior is already covered by a stronger scenario.
- Do not pursue line or branch coverage as a goal by itself.
- Do not test behavior guaranteed entirely by the type checker or a dependency.
- Keep scenarios deterministic: use bounded waits, controlled clocks, and no
  arbitrary sleeps.
- Give scenarios clear checkpoints so failures identify which phase broke.

## Workflow

1. Create a feature branch: `git checkout -b feature/your-feature`
2. Make changes
3. Run `make fix` to format and typecheck
4. Run `make test` to verify all tests pass
5. Submit PR for review
