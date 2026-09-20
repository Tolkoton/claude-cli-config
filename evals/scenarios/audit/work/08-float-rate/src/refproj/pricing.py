"""Price arithmetic. Pure functions, exact decimals."""

from collections.abc import Iterable
from decimal import ROUND_HALF_UP, Decimal

CENT = Decimal("0.01")


def apply_discount(price: Decimal, percent: int) -> Decimal:
    """Return `price` reduced by `percent` (0-100), rounded to cents."""
    if not 0 <= percent <= 100:
        raise ValueError(f"percent must be within 0..100, got {percent}")
    factor = (Decimal(100) - Decimal(percent)) / Decimal(100)
    return (price * factor).quantize(CENT, rounding=ROUND_HALF_UP)


def total(prices: Iterable[Decimal]) -> Decimal:
    """Sum prices, rounded to cents. An empty basket costs nothing."""
    return sum(prices, start=Decimal("0")).quantize(CENT, rounding=ROUND_HALF_UP)


def with_tax(price: Decimal, rate: float) -> Decimal:
    """Return `price` increased by a fractional tax rate (0.21 = 21 %), rounded to cents."""
    if rate < 0:
        raise ValueError(f"rate must not be negative, got {rate}")
    factor = Decimal(1) + Decimal(str(rate))
    return (price * factor).quantize(CENT, rounding=ROUND_HALF_UP)
