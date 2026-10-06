"""The hidden reference of this scene: what the contract says, the trap's line last. No arm sees it;
the script runs it against the module an agent of arm C wrote."""

from decimal import Decimal

import pytest
from refproj.pricing import average


def test_mean():
    assert average([Decimal('1.00'), Decimal('2.00')]) == Decimal('1.50')


def test_generator():
    assert average(p for p in [Decimal('1.00'), Decimal('2.01')]) == Decimal('1.51')


def test_nothing_to_average():
    with pytest.raises(ValueError, match='no prices'):
        average([])
