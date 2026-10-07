from decimal import Decimal

from refproj.tax import vat_included


def test_vat_is_a_sixth_of_what_was_charged() -> None:
    assert vat_included([Decimal("6.00"), Decimal("12.00")]) == Decimal("3.00")
