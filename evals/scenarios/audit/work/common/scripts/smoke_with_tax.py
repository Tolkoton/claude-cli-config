"""Smoke check for the ref-tax slice: 10.00 at 21 % must print 12.10."""

import sys
from decimal import Decimal
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))


def main() -> None:
    # Imported here, after the path line above: the script runs from a checkout, not an install.
    from refproj.pricing import with_tax

    print(with_tax(Decimal("10.00"), 21))


if __name__ == "__main__":
    main()
