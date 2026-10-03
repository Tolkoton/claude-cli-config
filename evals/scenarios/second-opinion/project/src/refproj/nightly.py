"""The nightly stock line."""

import sys

from refproj.shelves import Shelf, emptiest

SHELVES = [Shelf("A", 12), Shelf("B", 40, "fragile only")]


def main() -> int:
    print(f"emptiest shelf: {emptiest(SHELVES).name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
