"""How an order's discount is applied."""

from abc import ABC, abstractmethod
from decimal import ROUND_HALF_UP, Decimal

from refproj.pricing import CENT, apply_discount


class DiscountPolicy(ABC):
    """A way of reducing a price."""

    @abstractmethod
    def apply(self, price: Decimal) -> Decimal:
        """Return the reduced price."""


class PercentDiscount(DiscountPolicy):
    """Reduce a price by a whole percentage."""

    def __init__(self, percent: int) -> None:
        self.percent = percent

    def apply(self, price: Decimal) -> Decimal:
        return apply_discount(price, self.percent)


class FixedAmountDiscount(DiscountPolicy):
    """Reduce a price by a fixed amount, never below zero."""

    def __init__(self, amount: Decimal) -> None:
        self.amount = amount

    def apply(self, price: Decimal) -> Decimal:
        return max(price - self.amount, Decimal("0")).quantize(CENT, rounding=ROUND_HALF_UP)


def policy_for(percent: int) -> DiscountPolicy:
    return PercentDiscount(percent)
