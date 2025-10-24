import pytest

from framework.base.common import Venue
from framework.base.tools.symbol_formatter import format_symbol


@pytest.mark.parametrize(
    "symbol,venue,expected",
    [
        ("btcusdt", Venue.BINANCE_USDM, "BTCUSDT"),
        ("ethusdc", Venue.BINANCE_USDM, "ETHUSDC"),
        ("btcusdt", Venue.BINANCE_COINM, "BTCUSDT"),
        ("btc", Venue.BYBIT, "BTC"),
        ("doge", Venue.OKX, "DOGE"),
        ("arb", Venue.HYPERLIQUID, "ARB"),
    ],
)
def test_format_symbol_valid(symbol, venue, expected):
    assert format_symbol(symbol, venue) == expected


@pytest.mark.parametrize(
    "symbol,venue",
    [
        ("btc", Venue.BINANCE_USDM),
        ("eth-perp", Venue.BINANCE_USDM),
        ("eth1.5x", Venue.BINANCE_COINM),
        ("btc-perp", Venue.BYBIT),
        ("eth1.5x", Venue.OKX),
    ],
)
def test_format_symbol_invalid(symbol, venue):
    with pytest.raises(ValueError):
        format_symbol(symbol, venue)
