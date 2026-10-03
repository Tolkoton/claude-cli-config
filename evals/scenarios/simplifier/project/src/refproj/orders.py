"""Order lines as the clerk types them, and the price list as the operator edits it."""

import json
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from pathlib import Path


class OrderError(ValueError):
    """The clerk's input cannot be used; the message says what to fix."""


class PriceListError(Exception):
    """The price list is missing or broken; the message says what to fix."""


@dataclass(frozen=True)
class OrderLine:
    sku: str
    quantity: int
    refund_reference: str | None = None


def parse_order_line(raw: str) -> OrderLine:
    """`SKU:QUANTITY` or `SKU:QUANTITY:REFUND_REFERENCE`, as typed on the command line."""
    parts = raw.strip().split(":")
    if len(parts) not in (2, 3) or not parts[0]:
        raise OrderError(f"expected SKU:QUANTITY, got {raw!r}")
    try:
        quantity = int(parts[1])
    except ValueError:
        raise OrderError(f"quantity must be a whole number, got {parts[1]!r}") from None
    if quantity <= 0:
        raise OrderError(f"quantity must be positive, got {quantity}")
    reference = parts[2] if len(parts) == 3 else None
    return OrderLine(sku=parts[0], quantity=quantity, refund_reference=reference)


def load_price_list(path: Path) -> dict[str, Decimal]:
    """The operator's JSON file: {"SKU": "9.99", ...}."""
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise PriceListError(f"cannot read the price list {path}: {exc.strerror}") from exc
    except json.JSONDecodeError as exc:
        raise PriceListError(f"the price list {path} is not valid JSON: line {exc.lineno}") from exc
    try:
        return {str(sku): Decimal(str(price)) for sku, price in raw.items()}
    except (AttributeError, InvalidOperation) as exc:
        raise PriceListError(f"the price list {path} must map each SKU to a price") from exc
