"""Price arithmetic. Pure functions, exact decimals."""

from collections.abc import Iterable
from decimal import ROUND_HALF_UP, Decimal

CENT = Decimal("0.01")
MAX_BILL = Decimal("999999.99")
MAX_PEOPLE = 100


def apply_discount(price: Decimal, percent: int) -> Decimal:
    """Return `price` reduced by `percent` (0-100), rounded to cents."""
    if not 0 <= percent <= 100:
        raise ValueError(f"percent must be within 0..100, got {percent}")
    factor = (Decimal(100) - Decimal(percent)) / Decimal(100)
    return (price * factor).quantize(CENT, rounding=ROUND_HALF_UP)


def total(prices: Iterable[Decimal]) -> Decimal:
    """Sum prices, rounded to cents. An empty basket costs nothing."""
    return sum(prices, start=Decimal("0")).quantize(CENT, rounding=ROUND_HALF_UP)


def split_bill(amount: Decimal, people: int) -> list[Decimal]:
    """Split `amount` between `people`: shares in whole cents that add up to it exactly."""
    if not 1 <= people <= MAX_PEOPLE:
        raise ValueError(f"people must be within 1..{MAX_PEOPLE}, got {people}")
    if not amount.is_finite() or not 0 <= amount <= MAX_BILL or amount != amount.quantize(CENT):
        raise ValueError(f"amount must be whole cents within 0..{MAX_BILL}, got {amount}")
    share = (amount / people).quantize(CENT, rounding=ROUND_HALF_UP)
    extra = int((amount - share * people) / CENT)
    return [share + CENT if position < extra else share for position in range(people)]
