from typing import Dict

from frameworks.exchange.base.formats import Formats
from frameworks.exchange.dydx_v4.types import DydxSideConverter, DydxTimeInForceConverter, DydxOrderTypeConverter


class DydxFormats(Formats):
    """Unused, using official SDK"""
    def __init__(self) -> None:
        super().__init__(
            convert_side=DydxSideConverter(),
            convert_order_type=DydxOrderTypeConverter(),
            convert_time_in_force=DydxTimeInForceConverter()
        )