"""Price arithmetic. Pure functions, exact decimals."""

import re
from collections.abc import Iterable
from decimal import ROUND_HALF_UP, Decimal

CENT = Decimal("0.01")
MAX_PRICE = Decimal("9999999.99")
_PRICE_TEXT = re.compile(r"(?:\d{1,3}(?:,\d{3})?|\d+)\.\d{2}", re.ASCII)


def apply_discount(price: Decimal, percent: int) -> Decimal:
    """Return `price` reduced by `percent` (0-100), rounded to cents."""
    if not 0 <= percent <= 100:
        raise ValueError(f"percent must be within 0..100, got {percent}")
    factor = (Decimal(100) - Decimal(percent)) / Decimal(100)
    return (price * factor).quantize(CENT, rounding=ROUND_HALF_UP)


def total(prices: Iterable[Decimal]) -> Decimal:
    """Sum prices, rounded to cents. An empty basket costs nothing."""
    return sum(prices, start=Decimal("0")).quantize(CENT, rounding=ROUND_HALF_UP)


def format_price(price: Decimal) -> str:
    """The price as the shop prints it: thousands grouped by commas, always two decimals."""
    if not price.is_finite() or not 0 <= price <= MAX_PRICE or price != price.quantize(CENT):
        raise ValueError(f"not a price: {price}")
    return f"{price:,.2f}"


def parse_price(text: str) -> Decimal:
    """The price a printed text stands for; the commas may be left out."""
    if not _PRICE_TEXT.fullmatch(text):
        raise ValueError(f"not a price: {text!r}")
    price = Decimal(text.replace(",", ""))
    if price > MAX_PRICE:
        raise ValueError(f"not a price: {text!r}")
    return price
