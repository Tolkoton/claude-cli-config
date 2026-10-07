"""The counter.

`python -m refproj.cli PRICES.json ORDER_ID PERCENT SKU:QTY[:REF]... [--refund=PIN]`
"""

import os
import sys
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path

from refproj.discounts import policy_for
from refproj.inventory import StockItem, reserve
from refproj.journal import JournalError, record_order
from refproj.orders import OrderError, PriceListError, load_price_list, parse_order_line
from refproj.pricing import apply_discount, total
from refproj.receipts import ReceiptError, write_receipt
from refproj.refunds import pin_matches, refund_amount, refund_note
from refproj.tax import vat_included

ON_HAND = 100
WHOLESALE_FROM = 12
WHOLESALE_PERCENT = 5
RECEIPTS = Path("receipts")
CLOSED_FLAG = "CLOSED"


@dataclass(frozen=True)
class Charge:
    total: Decimal
    vat: Decimal


def charge(
    prices: dict[str, Decimal], percent: int, raw_lines: list[str], wholesale: bool = False
) -> Charge:
    policy = policy_for(percent)
    amounts = []
    for raw in raw_lines:
        line = parse_order_line(raw)
        if line.sku not in prices:
            raise OrderError(f"unknown SKU {line.sku}")
        left = reserve(StockItem(line.sku, prices[line.sku], ON_HAND), line.quantity)
        if left.on_hand < 0:
            raise RuntimeError(f"stock of {line.sku} went negative: {left.on_hand}")
        amount = policy.apply(prices[line.sku]) * line.quantity
        if wholesale and line.quantity >= WHOLESALE_FROM:
            amount = apply_discount(amount, WHOLESALE_PERCENT)
        amounts.append(amount)
    return Charge(total(amounts), vat_included(amounts))


def refund(prices: dict[str, Decimal], percent: int, raw_lines: list[str], pin: str) -> list[str]:
    if not pin_matches(pin, os.environ.get("REFPROJ_MANAGER_PIN", "")):
        raise OrderError("a refund needs the manager's PIN")
    lines = [parse_order_line(raw) for raw in raw_lines]
    return [refund_note(line, refund_amount(prices, percent, line)) for line in lines]


def main(argv: list[str]) -> int:
    pins = [a.removeprefix("--refund=") for a in argv if a.startswith("--refund=")]
    args = [a for a in argv if not a.startswith("--refund=")]
    if len(args) < 4:
        print(__doc__, file=sys.stderr)
        return 2
    if (RECEIPTS / CLOSED_FLAG).exists():
        print("error: the till is closed by the operator", file=sys.stderr)
        return 1
    try:
        prices = load_price_list(Path(args[0]))
        if pins:
            print("\n".join(refund(prices, int(args[2]), args[3:], pins[0])))
            return 0
        charged = charge(prices, int(args[2]), args[3:])
        receipt = write_receipt(RECEIPTS, args[1], charged.total)
        record_order(RECEIPTS, args[1], charged.total, charged.vat)
        print(receipt)
    except (OrderError, PriceListError, ReceiptError, JournalError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
