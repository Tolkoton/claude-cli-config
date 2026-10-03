"""How an order's discount is applied."""

from abc import ABC, abstractmethod
from decimal import Decimal

from refproj.pricing import apply_discount


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


def policy_for(percent: int) -> DiscountPolicy:
    return PercentDiscount(percent)
