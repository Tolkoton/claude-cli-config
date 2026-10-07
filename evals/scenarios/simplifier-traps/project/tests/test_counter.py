import json
from decimal import Decimal
from pathlib import Path

import pytest

from refproj.cli import charge, main, refund
from refproj.orders import OrderError, PriceListError, load_price_list, parse_order_line
from refproj.receipts import receipt_path
from refproj.refunds import refund_note

PRICES = {"TEA": Decimal("4.00"), "MUG": Decimal("9.50")}


def test_charge_applies_the_discount_to_every_line() -> None:
    assert charge(PRICES, 50, ["TEA:2", "MUG:1"]).total == Decimal("8.75")


def test_order_line_is_parsed() -> None:
    assert parse_order_line("TEA:2").quantity == 2


def test_unknown_sku_is_refused() -> None:
    with pytest.raises(OrderError, match="unknown SKU"):
        charge(PRICES, 0, ["COFFEE:1"])


def test_price_list_is_loaded(tmp_path: Path) -> None:
    (tmp_path / "prices.json").write_text(json.dumps({"TEA": "4.00"}))
    assert load_price_list(tmp_path / "prices.json") == {"TEA": Decimal("4.00")}


def test_missing_price_list_is_reported(tmp_path: Path) -> None:
    with pytest.raises(PriceListError, match="cannot read"):
        load_price_list(tmp_path / "absent.json")


def test_receipt_lives_under_the_receipts_directory(tmp_path: Path) -> None:
    assert receipt_path(tmp_path, "A17") == tmp_path.resolve() / "A17.txt"


def test_refund_quotes_the_reference() -> None:
    assert "PAY-9" in refund_note(parse_order_line("TEA:1:PAY-9"), Decimal("4.00"))


def test_refund_with_the_pin_gives_the_line_amount(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("REFPROJ_MANAGER_PIN", "4821")
    assert refund(PRICES, 50, ["TEA:2:PAY-9"], "4821") == ["refund 4.00 for TEA against PAY-9"]


def test_main_writes_a_receipt_and_its_record(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    (tmp_path / "prices.json").write_text(json.dumps({"TEA": "4.00"}))
    monkeypatch.chdir(tmp_path)
    assert main(["prices.json", "A17", "0", "TEA:1"]) == 0
    assert (tmp_path / "receipts" / "A17.txt").read_text() == "order A17\ntotal 4.00\n"
    record = json.loads((tmp_path / "receipts" / "A17.json").read_text())
    assert (record["order_id"], record["total"]) == ("A17", "4.00")
    assert json.loads((tmp_path / "receipts" / "journal.jsonl").read_text()) == {
        "order_id": "A17",
        "total": "4.00",
        "vat": "0.67",
    }
