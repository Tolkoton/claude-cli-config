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


def transfer(source: StockItem, target: StockItem, quantity: int) -> tuple[StockItem, StockItem]:
    """Move `quantity` units from `source` to `target`; return both as they are afterwards."""
    if source.sku != target.sku:
        raise ValueError(f"cannot transfer between different SKUs: {source.sku} and {target.sku}")
    taken = reserve(source, quantity)
    return taken, StockItem(sku=target.sku, unit_price=target.unit_price, on_hand=target.on_hand + quantity)
