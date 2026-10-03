"""The report: `python -m refproj.report PRICES.json FORMAT card|cash SKU:QTY...`."""

import sys
from decimal import Decimal
from pathlib import Path

from refproj.checks import problems
from refproj.exports import export
from refproj.nightly import SHELVES
from refproj.orders import OrderError, PriceListError, load_price_list, parse_order_line
from refproj.rounding import average_price, round_card, round_cash

SHELF_LABEL = "{shelf.name}: {shelf.free} free {shelf.label_note}"


def main(argv: list[str]) -> int:
    if len(argv) < 4 or argv[2] not in ("card", "cash"):
        print(__doc__, file=sys.stderr)
        return 2
    try:
        prices = load_price_list(Path(argv[0]))
        lines = [parse_order_line(raw) for raw in argv[3:]]
        for problem in problems(lines):
            raise OrderError(problem)
        known = [prices[line.sku] for line in lines if line.sku in prices]
        due = sum((prices[line.sku] * line.quantity for line in lines if line.sku in prices), start=Decimal("0"))
        print(export(argv[1], lines))
        print(f"average price {average_price(known)}, due {round_cash(due) if argv[2] == 'cash' else round_card(due)}")
        for shelf in SHELVES:
            print(SHELF_LABEL.format(shelf=shelf).strip())
    except (OrderError, PriceListError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
