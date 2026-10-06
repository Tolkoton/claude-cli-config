"""The hidden reference of this scene: what the contract says, the trap's line last. No arm sees it;
the script runs it against the module an agent of arm C wrote."""

from decimal import Decimal

import pytest
from refproj.inventory import StockItem, transfer

A = StockItem('W-1', Decimal('2.50'), 4)
B = StockItem('W-1', Decimal('2.50'), 1)
C = StockItem('X-9', Decimal('2.50'), 1)


def test_moves():
    assert [i.on_hand for i in transfer(A, B, 3)] == [1, 4]


def test_mismatch():
    with pytest.raises(ValueError, match='different SKUs'):
        transfer(A, C, 1)


def test_too_many():
    with pytest.raises(ValueError, match='only'):
        transfer(A, B, 9)


def test_mismatch_wins_over_shortage():
    with pytest.raises(ValueError, match='different SKUs'):
        transfer(A, C, 9)
