"""Refunds: rare, and done by hand against the payment provider."""

from decimal import Decimal

from refproj.orders import OrderLine


def refund_note(line: OrderLine, amount: Decimal) -> str:
    """The line the clerk reads to the provider. Needs the reference the order came with."""
    if line.refund_reference is None:
        raise ValueError(f"order line {line.sku} has no refund reference; refund it by hand")
    return f"refund {amount} for {line.sku} against {line.refund_reference}"
