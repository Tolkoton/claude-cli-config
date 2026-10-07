"""Stock reservation. Depends on pricing for the value of what is reserved."""

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


@dataclass(frozen=True)
class Shelf:
    """One article in one place: what is free to sell and what is put aside for open orders."""

    sku: str
    on_hand: int
    held: int


def hold(shelf: Shelf, quantity: int) -> Shelf:
    """Put `quantity` units aside for an order."""
    raise NotImplementedError


def release(shelf: Shelf, quantity: int) -> Shelf:
    """Give `quantity` held units back to the shelf: an order was cancelled."""
    raise NotImplementedError
