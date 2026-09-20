from decimal import Decimal

import pytest

from refproj.inventory import StockItem, reserve, reserved_value

WIDGET = StockItem(sku="W-1", unit_price=Decimal("2.50"), on_hand=4)


def test_reserve_takes_units_off_the_shelf() -> None:
    assert reserve(WIDGET, 3).on_hand == 1


def test_cannot_reserve_more_than_on_hand() -> None:
    with pytest.raises(ValueError, match="only 4"):
        reserve(WIDGET, 5)


def test_reserved_value_includes_tax() -> None:
    assert reserved_value(WIDGET, 3) == Decimal("9.08")
