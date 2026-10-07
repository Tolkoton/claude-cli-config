"""Receipt files: one per order id, all under one directory."""

import json
from decimal import Decimal
from pathlib import Path

EXPORT_SCHEMA = 2
CURRENCY = "EUR"


class ReceiptError(Exception):
    """The receipt could not be written; the order must not be charged."""


def receipt_path(receipts_dir: Path, order_id: str) -> Path:
    """Where the receipt of `order_id` lives. The id is typed by the clerk."""
    base = receipts_dir.resolve()
    target = (base / f"{order_id}.txt").resolve()
    if not target.is_relative_to(base):
        raise ValueError(f"order id {order_id!r} would leave the receipts directory")
    return target


def export_record(order_id: str, amount: Decimal) -> dict[str, str | int]:
    """The JSON record written beside the receipt."""
    return {
        "schema": EXPORT_SCHEMA,
        "order_id": order_id,
        "total": str(amount),
        "currency": CURRENCY,
    }


def write_receipt(receipts_dir: Path, order_id: str, amount: Decimal) -> Path:
    target = receipt_path(receipts_dir, order_id)
    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(f"order {order_id}\ntotal {amount}\n", encoding="utf-8")
        record = json.dumps(export_record(order_id, amount))
        target.with_suffix(".json").write_text(record, encoding="utf-8")
    except OSError as exc:
        raise ReceiptError(f"cannot write the receipt {target}: {exc.strerror}") from exc
    return target
