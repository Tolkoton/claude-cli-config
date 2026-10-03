"""Order exports: the report writes the lines in the format the clerk names."""

import json

from refproj.orders import OrderLine


class Exporter:
    """`run` builds the text; a subclass says what the header and a row look like."""

    def run(self, lines: list[OrderLine]) -> str:
        return "\n".join([self.header(), *(self.row(line) for line in lines)])

    def header(self) -> str:
        raise NotImplementedError

    def row(self, line: OrderLine) -> str:
        raise NotImplementedError


class TableExporter(Exporter):
    def header(self) -> str:
        return "sku | quantity"

    def row(self, line: OrderLine) -> str:
        return f"{line.sku} | {line.quantity}"


def export_table(lines: list[OrderLine]) -> str:
    return TableExporter().run(lines)


def export_csv(lines: list[OrderLine]) -> str:
    return "\n".join(f"{line.sku},{line.quantity}" for line in lines)


def export_json(lines: list[OrderLine]) -> str:
    return json.dumps([{"sku": line.sku, "quantity": line.quantity} for line in lines])


def export(fmt: str, lines: list[OrderLine]) -> str:
    writer = globals().get(f"export_{fmt}")
    if writer is None:
        raise ValueError(f"unknown export format {fmt!r}")
    return str(writer(lines))
