"""The day journal: one line per charged order, read by the operator at closing."""

import fcntl
import json
import time
from decimal import Decimal
from pathlib import Path

JOURNAL = "journal.jsonl"
ATTEMPTS = 3
PAUSE_S = 0.2


class JournalError(Exception):
    """The journal could not be written; the message says what to do."""


def _add_line(path: Path, order_id: str, total: Decimal, vat: Decimal) -> None:
    with path.open("a+", encoding="utf-8") as journal:
        fcntl.flock(journal, fcntl.LOCK_EX)
        journal.seek(0)
        if any(json.loads(line)["order_id"] == order_id for line in journal):
            return
        entry = {"order_id": order_id, "total": str(total), "vat": str(vat)}
        journal.write(json.dumps(entry) + "\n")


def record_order(receipts_dir: Path, order_id: str, total: Decimal, vat: Decimal) -> None:
    """Put the charged order into the day journal."""
    for attempt in range(1, ATTEMPTS + 1):
        try:
            _add_line(receipts_dir / JOURNAL, order_id, total, vat)
            return
        except OSError as exc:
            if attempt == ATTEMPTS:
                raise JournalError(f"cannot write the journal, repeat the order: {exc}") from exc
            time.sleep(PAUSE_S)
