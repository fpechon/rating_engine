import csv
from decimal import Decimal
from typing import Type, Any


class RangeTable:
    def __init__(self, rows, default=None):
        self.rows = rows
        self.default = default

    def lookup(self, value):
        if value is None:
            if self.default is not None:
                return self.default
            raise KeyError("Missing value and no default defined")

        for r in self.rows:
            if r["min"] <= value <= r["max"]:
                return r["value"]

        raise KeyError(f"Value {value} outside all ranges")


def load_range_table(path: str, default=None):
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
    return RangeTable(rows, default)


class ExactMatchTable:
    def __init__(
        self,
        mapping: dict,
        key_type: Type[Any] = str,
    ):
        """
        mapping: dict of {key -> value}
        value can be numeric (Decimal) or anything
        """
        self.mapping = mapping
        self.key_type = key_type

    def lookup(self, key):
        k = self.key_type(key)
        if k in self.mapping:
            return self.mapping[k]
        if "__DEFAULT__" in self.mapping:
            return self.mapping["__DEFAULT__"]
        raise KeyError(f"No matching row for {key}")


def load_exact_table(
    path: str,
    key_column: str = "key",
    value_column: str = "value",
    key_type: Type[Any] = str,
):
    mapping = {}
    with open(path) as f:
        reader = csv.DictReader(f)
        for row in reader:
            k = key_type(row[key_column])
            v = Decimal(str(row[value_column]))
            mapping[k] = v
    return ExactMatchTable(mapping, key_type=key_type)
