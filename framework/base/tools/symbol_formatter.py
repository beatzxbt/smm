from framework.base.common import Venue


def format_symbol(symbol: str, venue: Venue) -> str:
    match venue:
        case Venue.BINANCE_USDM | Venue.BINANCE_COINM:
            upper_case = symbol.upper()
            if not upper_case.endswith("USDT") and not upper_case.endswith("USDC"):
                raise ValueError(
                    f"Invalid base currency; expected [USDT, USDC] but got {symbol}"
                )
            if not upper_case.isalpha():
                raise ValueError(
                    f"Invalid characters detected; expected alphabet only but got {symbol}"
                )
            return upper_case
        case (
            Venue.BYBIT
            | Venue.OKX
            | Venue.HYPERLIQUID
            | Venue.PARADEX
            | Venue.EXTENDED
            | Venue.DYDX
        ):
            upper_case = symbol.upper()
            if not upper_case.isalpha():
                raise ValueError(
                    f"Invalid characters detected; expected alphabet only but got {symbol}"
                )
            return upper_case
        case _:
            return symbol
