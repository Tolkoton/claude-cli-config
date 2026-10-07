"""Stock reservation. Depends on pricing for the value of what is reserved."""

import re
from dataclasses import dataclass
from decimal import Decimal

from refproj.pricing import total


@dataclass(frozen=True)
class StockItem:
    sku: str
    unit_price: Decimal
    on_hand: int


def reserve(item: StockItem, quantity: int) -> StockItem:
    """Return the item with `quantity` units taken off the shelf."""
    if quantity <= 0:
        raise ValueError("quantity must be positive")
    if quantity > item.on_hand:
        raise ValueError(f"only {item.on_hand} of {item.sku} on hand, asked for {quantity}")
    return StockItem(sku=item.sku, unit_price=item.unit_price, on_hand=item.on_hand - quantity)


def reserved_value(item: StockItem, quantity: int) -> Decimal:
    """Value of `quantity` units of `item` at its unit price."""
    return total(item.unit_price for _ in range(quantity))


def normalize_sku(text: str) -> str:
    """The one spelling of an article number: upper case, its parts joined by single hyphens."""
    joined = re.sub(r"[_-]+", "-", text.upper().strip(" \t"))
    joined = re.sub(r"[ \t]+", "-", joined).strip("-")
    if not joined:
        raise ValueError(f"no article number in {text!r}")
    return joined
