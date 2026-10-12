#!/usr/bin/env python3
"""The arithmetic of task numbers (board 401): a number is its class x 100 + its place in the class.

A class is one digit, 1...9 (0 is what was there before classes and is never given). When a class
has used c01...c99 it goes on in the identifier + 10: 799 -> 1701 -> ... -> 1799 -> 2701. So the
last digit of `number // 100` is the class of every number, and a number never walks into another
class. The place 00 is never given; the old 600, 700, 800, 900 stay what they are.

This module only counts. It opens no file and reads no task: the caller hands it the numbers the
board holds. Which class a task belongs to, the table of classes, the order of the queue and the
renumbering after a merge are not here.
"""

from __future__ import annotations

from collections.abc import Iterable

UNCLASSED, OWN, OPEN_ITEMS, RULES, GATES = 1, 4, 7, 8, 9  # nobody gave a class; the runner's own; the three kinds of question


def class_of(number: int) -> int:
    """The class a number belongs to, 0...9: the last digit of its hundreds."""
    return number // 100 % 10


def next_number(taken: Iterable[int], klass: int) -> int:
    """The number after the largest one of `klass` in `taken`; the first of the class when there is none.
    A gap under the largest is not filled: the number of a task that is gone may still be named somewhere."""
    if klass not in range(1, 10):
        raise ValueError(f"no task is numbered in class {klass}: the classes are 1...9")
    largest = max((n for n in taken if class_of(n) == klass), default=klass * 100)
    return largest + 1 if largest % 100 < 99 else (largest // 100 + 10) * 100 + 1
