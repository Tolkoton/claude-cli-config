"""The counter: `python -m refproj.cli PRICES.json ORDER_ID PERCENT SKU:QTY[:REF]... [--refund]`."""

import sys
from decimal import Decimal
from pathlib import Path

from refproj.discounts import policy_for
from refproj.inventory import StockItem, reserve
from refproj.orders import OrderError, PriceListError, load_price_list, parse_order_line
from refproj.pricing import total
from refproj.receipts import write_receipt
from refproj.refunds import refund_note

ON_HAND = 100


def charge(prices: dict[str, Decimal], percent: int, raw_lines: list[str]) -> Decimal:
    policy = policy_for(percent)
    amounts = []
    for raw in raw_lines:
        line = parse_order_line(raw)
        if line.sku not in prices:
            raise OrderError(f"unknown SKU {line.sku}")
        reserve(StockItem(line.sku, prices[line.sku], ON_HAND), line.quantity)
        amounts.append(policy.apply(prices[line.sku]) * line.quantity)
    return total(amounts)


def main(argv: list[str]) -> int:
    refund = "--refund" in argv
    args = [a for a in argv if a != "--refund"]
    if len(args) < 4:
        print(__doc__, file=sys.stderr)
        return 2
    try:
        prices = load_price_list(Path(args[0]))
        amount = charge(prices, int(args[2]), args[3:])
        if refund:
            for raw in args[3:]:
                print(refund_note(parse_order_line(raw), amount))
            return 0
        print(write_receipt(Path("receipts"), args[1], amount))
    except (OrderError, PriceListError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
