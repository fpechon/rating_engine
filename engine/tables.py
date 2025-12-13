import csv
from decimal import Decimal


class RangeTable:
    def __init__(self, rows):
        self.rows = rows

    def lookup(self, value):
        for r in self.rows:
            if r["min"] <= value <= r["max"]:
                return r["value"]
        raise KeyError(f"No matching row for {value}")


def load_range_table(path):
    rows = []
    with open(path) as f:
        reader = csv.DictReader(f)
        for r in reader:
            rows.append(
                {
                    "min": int(r["min"]),
                    "max": int(r["max"]),
                    "value": Decimal(str(r["value"])),
                }
            )
    return RangeTable(rows)
