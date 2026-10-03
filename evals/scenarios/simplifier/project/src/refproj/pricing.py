"""Price arithmetic. Pure functions, exact decimals."""

from collections.abc import Iterable
from decimal import ROUND_HALF_UP, Decimal

CENT = Decimal("0.01")


def apply_discount(price: Decimal, percent: int) -> Decimal:
    """Return `price` reduced by `percent` (0-100), rounded to cents."""
    if not 0 <= percent <= 100:
        raise ValueError(f"percent must be within 0..100, got {percent}")
    factor = (Decimal(100) - Decimal(percent)) / Decimal(100)
    if factor < 0:
        raise RuntimeError(f"discount factor went negative: {factor}")
    return (price * factor).quantize(CENT, rounding=ROUND_HALF_UP)


def total(prices: Iterable[Decimal]) -> Decimal:
    """Sum prices, rounded to cents. An empty basket costs nothing."""
    return sum(prices, start=Decimal("0")).quantize(CENT, rounding=ROUND_HALF_UP)


def _legacy_total_v1(prices: list[float]) -> float:
    """Sum prices the way the first version did, in floats."""
    result = 0.0
    for price in prices:
        result += price
    return round(result, 2)
