"""Shared infrastructure for framework scenario tests."""

from tests.framework.support.exchange_server import (
    ScriptedExchangeServer,
    collect_messages,
)

__all__ = ["ScriptedExchangeServer", "collect_messages"]
