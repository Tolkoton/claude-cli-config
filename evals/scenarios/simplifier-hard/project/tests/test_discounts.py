from decimal import Decimal

from refproj.discounts import FixedAmountDiscount, PercentDiscount


def test_percent_discount_reduces_by_a_percentage() -> None:
    assert PercentDiscount(50).apply(Decimal("9.50")) == Decimal("4.75")


def test_fixed_amount_discount_takes_the_amount_off() -> None:
    assert FixedAmountDiscount(Decimal("1.50")).apply(Decimal("4.00")) == Decimal("2.50")


def test_fixed_amount_discount_stops_at_zero() -> None:
    assert FixedAmountDiscount(Decimal("5.00")).apply(Decimal("4.00")) == Decimal("0.00")
