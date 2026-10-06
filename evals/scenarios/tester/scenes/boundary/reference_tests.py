"""The hidden reference of this scene: what the contract says, the trap's line last. No arm sees it;
the script runs it against the module an agent of arm C wrote."""

from decimal import Decimal

import pytest
from refproj.inventory import StockItem, needs_reorder

W = StockItem('W-1', Decimal('2.50'), 4)


def test_below():
    assert needs_reorder(W, 5) is True


def test_above():
    assert needs_reorder(W, 3) is False


def test_negative():
    with pytest.raises(ValueError, match='reorder point'):
        needs_reorder(W, -1)


def test_at_the_point():
    assert needs_reorder(W, 4) is True
