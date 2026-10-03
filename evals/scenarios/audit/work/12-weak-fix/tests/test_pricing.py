from decimal import Decimal

import pytest

from refproj.pricing import apply_discount, total, with_tax


def test_discount_rounds_half_up_to_cents() -> None:
    assert apply_discount(Decimal("19.99"), 15) == Decimal("16.99")


def test_discount_of_zero_and_hundred_are_the_bounds() -> None:
    assert apply_discount(Decimal("10.00"), 0) == Decimal("10.00")
    assert apply_discount(Decimal("10.00"), 100) == Decimal("0.00")


def test_discount_outside_bounds_is_rejected() -> None:
    with pytest.raises(ValueError, match="0..100"):
        apply_discount(Decimal("10.00"), 101)


def test_total_of_empty_basket_is_zero() -> None:
    assert total([]) == Decimal("0.00")


def test_with_tax_rounds_half_up() -> None:
    result = with_tax(Decimal("0.50"), 21)
    assert isinstance(result, Decimal)
    assert result > Decimal("0.50")
    assert result == result.quantize(Decimal("0.01"))


def test_with_tax_rejects_negative_rate() -> None:
    with pytest.raises(ValueError, match="-5"):
        with_tax(Decimal("10.00"), -5)
