"""Tests for SimpleMap with Symbol/Instrument types."""

from framework.base.common import Instrument, InstrumentType, Venue, SimpleMap


def test_simple_map_add_and_get():
    """Test adding and retrieving items from SimpleMap."""
    smap = SimpleMap({})

    instrument = Instrument(
        venue=Venue.BYBIT,
        symbol="BTCUSDT",
        base="BTC",
        quote="USDT",
        code=0,
        instrument_type=InstrumentType.PERPETUAL,
        tick_size=0.01,
        lot_size=0.001,
    )

    # Add by symbol
    smap["BTCUSDT"] = instrument

    # Retrieve by symbol
    assert smap.get("BTCUSDT") == instrument

    # Retrieve by instrument (reverse lookup)
    assert smap.get(instrument) == "BTCUSDT"


def test_simple_map_multiple_instruments():
    """Test SimpleMap with multiple instruments."""
    smap = SimpleMap({})

    instruments = [
        Instrument(
            venue=Venue.BYBIT,
            symbol="BTCUSDT",
            base="BTC",
            quote="USDT",
            code=0,
            instrument_type=InstrumentType.PERPETUAL,
            tick_size=0.01,
            lot_size=0.001,
        ),
        Instrument(
            venue=Venue.BYBIT,
            symbol="ETHUSDT",
            base="ETH",
            quote="USDT",
            code=0,
            instrument_type=InstrumentType.PERPETUAL,
            tick_size=0.01,
            lot_size=0.001,
        ),
        Instrument(
            venue=Venue.BYBIT,
            symbol="SOLUSDT",
            base="SOL",
            quote="USDT",
            code=0,
            instrument_type=InstrumentType.PERPETUAL,
            tick_size=0.01,
            lot_size=0.001,
        ),
    ]

    for inst in instruments:
        smap[inst.symbol] = inst

    assert smap.get("BTCUSDT") == instruments[0]
    assert smap.get("ETHUSDT") == instruments[1]
    assert smap.get("SOLUSDT") == instruments[2]

    # Reverse lookup
    assert smap.get(instruments[0]) == "BTCUSDT"
    assert smap.get(instruments[1]) == "ETHUSDT"


def test_simple_map_contains():
    """Test 'in' operator for SimpleMap."""
    smap = SimpleMap({})

    instrument = Instrument(
        venue=Venue.BYBIT,
        symbol="BTCUSDT",
        base="BTC",
        quote="USDT",
        code=0,
        instrument_type=InstrumentType.PERPETUAL,
        tick_size=0.01,
        lot_size=0.001,
    )

    smap["BTCUSDT"] = instrument

    assert "BTCUSDT" in smap
    assert instrument in smap
    assert "ETHUSDT" not in smap


def test_simple_map_get_none():
    """Test that get returns None for non-existent keys."""
    smap = SimpleMap({})

    assert smap.get("NONEXISTENT") is None
    assert smap.get(None) is None


def test_simple_map_symbol_case_handling():
    """Test SimpleMap with different symbol formats."""
    smap = SimpleMap({})

    # Binance uses lowercase
    btc_binance = Instrument(
        venue=Venue.BINANCE_USDM,
        symbol="btcusdt",
        base="BTC",
        quote="USDT",
        code=0,
        instrument_type=InstrumentType.PERPETUAL,
        tick_size=0.01,
        lot_size=0.001,
    )

    # Bybit uses uppercase
    btc_bybit = Instrument(
        venue=Venue.BYBIT,
        symbol="BTCUSDT",
        base="BTC",
        quote="USDT",
        code=0,
        instrument_type=InstrumentType.PERPETUAL,
        tick_size=0.01,
        lot_size=0.001,
    )

    smap["btcusdt"] = btc_binance
    smap["BTCUSDT"] = btc_bybit

    assert smap.get("btcusdt") == btc_binance
    assert smap.get("BTCUSDT") == btc_bybit
    assert smap.get(btc_binance) == "btcusdt"
    assert smap.get(btc_bybit) == "BTCUSDT"
