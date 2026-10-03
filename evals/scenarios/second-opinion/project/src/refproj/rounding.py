"""Rounding an amount the way it is paid."""

from decimal import ROUND_HALF_UP, Decimal

from refproj.orders import OrderError

CENT = Decimal("0.01")
SMALLEST_COIN = Decimal("0.05")


def round_card(amount: Decimal) -> Decimal:
    return amount.quantize(CENT, rounding=ROUND_HALF_UP)


def round_cash(amount: Decimal) -> Decimal:
    return (amount / SMALLEST_COIN).quantize(Decimal("1"), rounding=ROUND_HALF_UP) * SMALLEST_COIN


def average_price(amounts: list[Decimal]) -> Decimal:
    if not amounts:
        raise OrderError("no line has a known price: nothing to average")
    return round_card(sum(amounts, start=Decimal("0")) / len(amounts))
