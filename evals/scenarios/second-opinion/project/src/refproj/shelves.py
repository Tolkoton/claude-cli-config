"""Shelves of the stock room."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Shelf:
    name: str
    free: int
    label_note: str = ""

    def __lt__(self, other: "Shelf") -> bool:
        return self.free < other.free


def emptiest(shelves: list[Shelf]) -> Shelf:
    return sorted(shelves)[-1]
