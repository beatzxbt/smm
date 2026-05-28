"""Tests for Bybit trade stream message parsing and conversions."""

import msgspec
from framework.base.common import Asset, Instrument, InstrumentType, Symbol, Venue
from framework.bybit.stream.models import BybitTrade, BybitTradeMsg
from framework.bybit.trading.exchange import BybitExchange
from mm_toolbox.logging.standard import Logger


def test_bybit_trade_public_msg_parsing():
    """Test parsing of Bybit trade message structure."""
    json_str = """{
        "topic": "publicTrade.BTCUSDT",
        "type": "snapshot",
        "ts": 1234567890,
        "data": [
            {
                "T": 1234567890000,
                "S": "BTCUSDT",
                "s": "Buy",
                "v": 0.1,
                "p": 50000.5,
                "i": "12345",
                "seq": 100
            },
            {
                "T": 1234567890001,
                "S": "BTCUSDT",
                "s": "Sell",
                "v": 0.2,
                "p": 50001.0,
                "i": "12346",
                "seq": 101
            }
        ]
    }"""

    decoder = msgspec.json.Decoder(BybitTradeMsg)
    msg = decoder.decode(json_str.encode())

    assert msg.topic == "publicTrade.BTCUSDT"
    assert msg.type == "snapshot"
    assert msg.ts == 1234567890
    assert len(msg.data) == 2
    assert msg.data[0].seq == 100
    assert msg.data[1].seq == 101


def test_bybit_trade_msg_conversion():
    """Test conversion of BybitTradeMsg to framework Trade struct."""
    trade_msg = BybitTrade(
        time_ms=1234567890000,
        symbol="BTCUSDT",
        side="Buy",
        size=0.1,
        price=50000.5,
        id="12345",
        seq=100,
    )

    # Convert to framework Trade
    trade = trade_msg.to_trade()

    assert trade.time_ms == 1234567890000
    assert trade.price == 50000.5
    assert trade.is_buy is True
    assert trade.size == 0.1
    assert trade.value == 5000.05


def test_bybit_instrument_to_symbol():
    """Test Bybit symbol formatting."""

    logger = Logger()
    exchange = BybitExchange(logger=logger, load_secrets=False)

    instrument = Instrument(
        venue=Venue.BYBIT,
        symbol=Symbol("BTCUSDT"),
        base=Asset("BTC"),
        quote=Asset("USDT"),
        code=0,
        instrument_type=InstrumentType.PERPETUAL,
        tick_size=0.01,
        lot_size=0.001,
    )

    symbol = exchange.instrument_to_symbol(instrument)
    assert symbol == "BTCUSDT"


def test_bybit_multi_trade_in_single_message():
    """Test handling of multiple trades in a single message."""
    json_str = """{
        "topic": "publicTrade.BTCUSDT",
        "type": "snapshot",
        "ts": 1234567890,
        "data": [
            {"T": 1000, "S": "BTCUSDT", "s": "Buy", "v": 1.0, "p": 1000.0, "i": "1", "seq": 1},
            {"T": 1001, "S": "BTCUSDT", "s": "Sell", "v": 2.0, "p": 1001.0, "i": "2", "seq": 2},
            {"T": 1002, "S": "BTCUSDT", "s": "Buy", "v": 3.0, "p": 1002.0, "i": "3", "seq": 3}
        ]
    }"""

    decoder = msgspec.json.Decoder(BybitTradeMsg)
    msg = decoder.decode(json_str.encode())

    assert len(msg.data) == 3
    assert msg.data[0].seq == 1
    assert msg.data[1].seq == 2
    assert msg.data[2].seq == 3
