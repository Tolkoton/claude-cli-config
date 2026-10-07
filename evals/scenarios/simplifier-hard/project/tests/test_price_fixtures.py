import json
from decimal import Decimal
from pathlib import Path

import yaml

from refproj.orders import load_price_list

FIXTURES = Path(__file__).parent / "fixtures"


def test_the_shared_price_list_loads(tmp_path: Path) -> None:
    rows = yaml.safe_load((FIXTURES / "prices.yaml").read_text(encoding="utf-8"))
    (tmp_path / "prices.json").write_text(json.dumps(rows))
    loaded = load_price_list(tmp_path / "prices.json")
    assert loaded == {"TEA": Decimal("4.00"), "MUG": Decimal("9.50")}
