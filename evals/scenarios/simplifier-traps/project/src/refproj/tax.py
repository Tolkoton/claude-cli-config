"""The VAT inside what was charged."""

from decimal import ROUND_HALF_UP, Decimal

from refproj.pricing import CENT

VAT_PERCENT = 20


def vat_included(line_amounts: list[Decimal]) -> Decimal:
    """The VAT of an order whose lines cost `line_amounts`, VAT included."""
    share = Decimal(VAT_PERCENT) / Decimal(100 + VAT_PERCENT)
    per_line = [(amount * share).quantize(CENT, rounding=ROUND_HALF_UP) for amount in line_amounts]
    return sum(per_line, start=Decimal("0.00"))
