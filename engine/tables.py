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



class ExactMatchTable:
    def __init__(self, mapping):
        """
        mapping: dict of {key -> value}
        value can be numeric (Decimal) or anything
        """
        self.mapping = mapping

    def lookup(self, key):
        if key in self.mapping:
            return self.mapping[key]
        raise KeyError(f"No matching row for {key}")


def load_exact_table(path, key_column="key", value_column="value"):
    mapping = {}
    with open(path) as f:
        reader = csv.DictReader(f)
        for row in reader:
            k = row[key_column]
            v = Decimal(str(row[value_column]))  # convert to Decimal
            mapping[k] = v
    return ExactMatchTable(mapping)
