"""Checks an order must pass before it is reported."""

from collections.abc import Callable

from refproj.orders import OrderLine

Check = Callable[[list[OrderLine]], str | None]
CHECKS: list[Check] = []
MAX_LINES = 50


def check(func: Check) -> Check:
    CHECKS.append(func)
    return func


@check
def no_duplicate_skus(lines: list[OrderLine]) -> str | None:
    skus = [line.sku for line in lines]
    return "the same SKU is on two lines" if len(set(skus)) != len(skus) else None


@check
def not_too_many_lines(lines: list[OrderLine]) -> str | None:
    return f"more than {MAX_LINES} lines" if len(lines) > MAX_LINES else None


def problems(lines: list[OrderLine]) -> list[str]:
    return [message for one in CHECKS if (message := one(lines)) is not None]
