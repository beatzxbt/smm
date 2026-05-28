"""Shared order and state structures for pricing and OMS components.

Usage: pricing engines emit DesiredState for OMS reconciliation.
Components: DesiredOrder and DesiredState structs.
"""

from __future__ import annotations

from typing import Self

import msgspec

from framework.base.common import ClientOrderId, Instrument


class DesiredOrder(msgspec.Struct):
    """Desired order representation emitted by pricing engines.

    Attributes:
        price (float): Order price (0 for market orders).
        is_buy (bool): True if buy order.
        size (float): Order size in base units.
        is_maker (bool): True for maker orders.
        reduce_only (bool): True to prevent position flips.
        client_order_id (ClientOrderId | None): Optional client order id.
    """

    price: float
    is_buy: bool
    size: float
    is_maker: bool
    reduce_only: bool
    client_order_id: ClientOrderId | None = None

    def __post_init__(self) -> None:
        """Validate desired order fields."""
        if self.price <= 0.0 and self.is_maker:
            raise ValueError("price must be > 0 for maker orders")
        if self.size <= 0.0:
            raise ValueError("size must be > 0")


class DesiredState(msgspec.Struct):
    """Pricing output representing the intended exchange state.

    Attributes:
        instrument (Instrument): Instrument for the desired state.
        delta_is_positive (bool): Direction of delta adjustment.
        delta_size (float): Delta size adjustment.
        bids (list[DesiredOrder]): Desired bid orders.
        asks (list[DesiredOrder]): Desired ask orders.
    """

    instrument: Instrument
    delta_is_positive: bool
    delta_size: float
    bids: list[DesiredOrder]
    asks: list[DesiredOrder]

    @classmethod
    def empty(cls, instrument: Instrument) -> Self:
        """Create an empty desired state for an instrument.

        Args:
            instrument (Instrument): Instrument to associate with the desired state.

        Returns:
            DesiredState: Empty desired state instance.
        """
        return cls(
            instrument=instrument,
            delta_is_positive=False,
            delta_size=0.0,
            bids=[],
            asks=[],
        )
