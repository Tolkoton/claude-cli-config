"""Receipt files: one per order id, all under one directory."""

from decimal import Decimal
from pathlib import Path


def receipt_path(receipts_dir: Path, order_id: str) -> Path:
    """Where the receipt of `order_id` lives. The id is typed by the clerk."""
    base = receipts_dir.resolve()
    target = (base / f"{order_id}.txt").resolve()
    if not target.is_relative_to(base):
        raise ValueError(f"order id {order_id!r} would leave the receipts directory")
    return target


def write_receipt(receipts_dir: Path, order_id: str, amount: Decimal) -> Path:
    target = receipt_path(receipts_dir, order_id)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(f"order {order_id}\ntotal {amount}\n", encoding="utf-8")
    return target
