"""The hidden reference of this scene: what the contract says, the trap's line last. No arm sees it;
the script runs it against the module an agent of arm C wrote."""

from decimal import Decimal

import pytest
from refproj.pricing import add_tax


def test_plain():
    assert add_tax(Decimal('10.00'), Decimal('20')) == Decimal('12.00')


def test_rounds_up_past_the_tie():
    assert add_tax(Decimal('0.51'), Decimal('5')) == Decimal('0.54')


def test_negative():
    with pytest.raises(ValueError, match='tax rate'):
        add_tax(Decimal('1'), Decimal('-1'))


def test_tie_goes_to_the_even_cent():
    assert add_tax(Decimal('0.50'), Decimal('5')) == Decimal('0.52')
