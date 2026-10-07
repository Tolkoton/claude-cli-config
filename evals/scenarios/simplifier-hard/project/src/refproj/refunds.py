"""Refunds: rare, and done by hand against the payment provider."""

import hmac
from decimal import ROUND_HALF_UP, Decimal

from refproj.orders import OrderError, OrderLine
from refproj.pricing import CENT, apply_discount


def pin_matches(typed: str, expected: str) -> bool:
    """Whether what was typed is the manager's PIN."""
    return bool(expected) and hmac.compare_digest(typed.encode(), expected.encode())


def refund_amount(prices: dict[str, Decimal], percent: int, line: OrderLine) -> Decimal:
    """What the order line cost the customer."""
    unit = prices.get(line.sku)
    if unit is None:
        raise OrderError(f"unknown SKU {line.sku}")
    reduced = apply_discount(unit, percent)
    return (reduced * Decimal(line.quantity)).quantize(CENT, rounding=ROUND_HALF_UP)


def refund_note(line: OrderLine, amount: Decimal) -> str:
    """The line the clerk reads to the provider. Needs the reference the order came with."""
    if line.refund_reference is None:
        raise ValueError(f"order line {line.sku} has no refund reference; refund it by hand")
    return f"refund {amount} for {line.sku} against {line.refund_reference}"
