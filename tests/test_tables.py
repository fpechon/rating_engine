"""
Tests unitaires pour les tables de lookup (RangeTable et ExactMatchTable).
"""
import pytest
from decimal import Decimal
import tempfile
import csv
from pathlib import Path
from engine.tables import (
    RangeTable,
    ExactMatchTable,
    load_range_table,
    load_exact_table,
)


class TestRangeTable:
    """Tests pour RangeTable."""

    def test_initialization(self):
        rows = [{"min": 0, "max": 10, "value": Decimal("1.0")}]
        table = RangeTable(rows)
        assert table.rows == rows
        assert table.default is None

    def test_initialization_with_default(self):
        rows = [{"min": 0, "max": 10, "value": Decimal("1.0")}]
        default = Decimal("0.5")
        table = RangeTable(rows, default=default)
        assert table.default == default

    def test_lookup_in_range(self):
        rows = [
            {"min": 0, "max": 10, "value": Decimal("1.0")},
            {"min": 11, "max": 20, "value": Decimal("2.0")},
        ]
        table = RangeTable(rows)
        assert table.lookup(5) == Decimal("1.0")
        assert table.lookup(15) == Decimal("2.0")

    def test_lookup_at_boundaries(self):
        rows = [{"min": 18, "max": 25, "value": Decimal("1.5")}]
        table = RangeTable(rows)
        assert table.lookup(18) == Decimal("1.5")
        assert table.lookup(25) == Decimal("1.5")
        assert table.lookup(21) == Decimal("1.5")

    def test_lookup_multiple_ranges(self):
        rows = [
            {"min": 18, "max": 25, "value": Decimal("1.8")},
            {"min": 26, "max": 65, "value": Decimal("1.0")},
            {"min": 66, "max": 99, "value": Decimal("1.3")},
        ]
        table = RangeTable(rows)
        assert table.lookup(20) == Decimal("1.8")
        assert table.lookup(40) == Decimal("1.0")
        assert table.lookup(70) == Decimal("1.3")

    def test_lookup_outside_range_raises_error(self):
        rows = [{"min": 10, "max": 20, "value": Decimal("1.0")}]
        table = RangeTable(rows)
        with pytest.raises(KeyError, match="Value 5 outside all ranges"):
            table.lookup(5)
        with pytest.raises(KeyError, match="Value 25 outside all ranges"):
            table.lookup(25)

    def test_lookup_none_with_default(self):
        rows = [{"min": 0, "max": 10, "value": Decimal("1.0")}]
        table = RangeTable(rows, default=Decimal("0.5"))
        assert table.lookup(None) == Decimal("0.5")

    def test_lookup_none_without_default_raises_error(self):
        rows = [{"min": 0, "max": 10, "value": Decimal("1.0")}]
        table = RangeTable(rows)
        with pytest.raises(KeyError, match="Missing value and no default defined"):
            table.lookup(None)

    def test_lookup_decimal_value(self):
        rows = [{"min": 0, "max": 100, "value": Decimal("1.0")}]
        table = RangeTable(rows)
        assert table.lookup(Decimal("50.5")) == Decimal("1.0")


class TestExactMatchTable:
    """Tests pour ExactMatchTable."""

    def test_initialization(self):
        mapping = {"BMW": Decimal("1.2"), "Audi": Decimal("1.1")}
        table = ExactMatchTable(mapping)
        assert table.mapping == mapping
        assert table.key_type is str

    def test_initialization_with_key_type(self):
        mapping = {1: Decimal("10"), 2: Decimal("20")}
        table = ExactMatchTable(mapping, key_type=int)
        assert table.key_type is int

    def test_lookup_exact_match(self):
        mapping = {"BMW": Decimal("1.2"), "Audi": Decimal("1.1"), "Mercedes": Decimal("1.3")}
        table = ExactMatchTable(mapping)
        assert table.lookup("BMW") == Decimal("1.2")
        assert table.lookup("Audi") == Decimal("1.1")
        assert table.lookup("Mercedes") == Decimal("1.3")

    def test_lookup_with_default(self):
        mapping = {"BMW": Decimal("1.2"), "__DEFAULT__": Decimal("1.0")}
        table = ExactMatchTable(mapping)
        assert table.lookup("BMW") == Decimal("1.2")
        assert table.lookup("Unknown Brand") == Decimal("1.0")

    def test_lookup_missing_key_without_default_raises_error(self):
        mapping = {"BMW": Decimal("1.2")}
        table = ExactMatchTable(mapping)
        with pytest.raises(KeyError, match="No matching row for Unknown"):
            table.lookup("Unknown")

    def test_lookup_with_int_key_type(self):
        mapping = {1: Decimal("100"), 2: Decimal("200"), 3: Decimal("300")}
        table = ExactMatchTable(mapping, key_type=int)
        assert table.lookup(1) == Decimal("100")
        assert table.lookup("2") == Decimal("200")  # String converted to int

    def test_lookup_case_sensitive(self):
        mapping = {"bmw": Decimal("1.2"), "BMW": Decimal("1.5")}
        table = ExactMatchTable(mapping)
        assert table.lookup("bmw") == Decimal("1.2")
        assert table.lookup("BMW") == Decimal("1.5")


class TestLoadRangeTable:
    """Tests pour load_range_table."""

    def test_load_simple_range_table(self):
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.csv') as f:
            writer = csv.DictWriter(f, fieldnames=["min", "max", "value"])
            writer.writeheader()
            writer.writerow({"min": "18", "max": "25", "value": "1.8"})
            writer.writerow({"min": "26", "max": "65", "value": "1.0"})
            temp_path = f.name

        try:
            table = load_range_table(temp_path)
            assert isinstance(table, RangeTable)
            assert len(table.rows) == 2
            assert table.lookup(20) == Decimal("1.8")
            assert table.lookup(40) == Decimal("1.0")
        finally:
            Path(temp_path).unlink()

    def test_load_range_table_with_default(self):
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.csv') as f:
            writer = csv.DictWriter(f, fieldnames=["min", "max", "value"])
            writer.writeheader()
            writer.writerow({"min": "0", "max": "10", "value": "1.0"})
            temp_path = f.name

        try:
            table = load_range_table(temp_path, default=Decimal("0.5"))
            assert table.default == Decimal("0.5")
            assert table.lookup(None) == Decimal("0.5")
        finally:
            Path(temp_path).unlink()

    def test_load_range_table_decimal_precision(self):
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.csv') as f:
            writer = csv.DictWriter(f, fieldnames=["min", "max", "value"])
            writer.writeheader()
            writer.writerow({"min": "0", "max": "100", "value": "0.756900"})
            temp_path = f.name

        try:
            table = load_range_table(temp_path)
            result = table.lookup(50)
            assert result == Decimal("0.756900")
            assert isinstance(result, Decimal)
        finally:
            Path(temp_path).unlink()


class TestLoadExactTable:
    """Tests pour load_exact_table."""

    def test_load_simple_exact_table(self):
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.csv') as f:
            writer = csv.DictWriter(f, fieldnames=["key", "value"])
            writer.writeheader()
            writer.writerow({"key": "BMW", "value": "1.2"})
            writer.writerow({"key": "Audi", "value": "1.1"})
            temp_path = f.name

        try:
            table = load_exact_table(temp_path)
            assert isinstance(table, ExactMatchTable)
            assert table.lookup("BMW") == Decimal("1.2")
            assert table.lookup("Audi") == Decimal("1.1")
        finally:
            Path(temp_path).unlink()

    def test_load_exact_table_with_custom_columns(self):
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.csv') as f:
            writer = csv.DictWriter(f, fieldnames=["brand", "coef"])
            writer.writeheader()
            writer.writerow({"brand": "BMW", "coef": "1.5"})
            temp_path = f.name

        try:
            table = load_exact_table(temp_path, key_column="brand", value_column="coef")
            assert table.lookup("BMW") == Decimal("1.5")
        finally:
            Path(temp_path).unlink()

    def test_load_exact_table_with_int_key(self):
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.csv') as f:
            writer = csv.DictWriter(f, fieldnames=["zone_id", "coef"])
            writer.writeheader()
            writer.writerow({"zone_id": "1", "coef": "0.8"})
            writer.writerow({"zone_id": "2", "coef": "1.0"})
            temp_path = f.name

        try:
            table = load_exact_table(temp_path, key_column="zone_id", value_column="coef", key_type=int)
            assert table.lookup(1) == Decimal("0.8")
            assert table.lookup("2") == Decimal("1.0")
        finally:
            Path(temp_path).unlink()

    def test_load_exact_table_with_default(self):
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.csv') as f:
            writer = csv.DictWriter(f, fieldnames=["key", "value"])
            writer.writeheader()
            writer.writerow({"key": "BMW", "value": "1.2"})
            writer.writerow({"key": "__DEFAULT__", "value": "1.0"})
            temp_path = f.name

        try:
            table = load_exact_table(temp_path)
            assert table.lookup("BMW") == Decimal("1.2")
            assert table.lookup("Unknown") == Decimal("1.0")
        finally:
            Path(temp_path).unlink()

    def test_load_exact_table_decimal_precision(self):
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.csv') as f:
            writer = csv.DictWriter(f, fieldnames=["key", "value"])
            writer.writeheader()
            writer.writerow({"key": "premium", "value": "123.456789"})
            temp_path = f.name

        try:
            table = load_exact_table(temp_path)
            result = table.lookup("premium")
            assert result == Decimal("123.456789")
            assert isinstance(result, Decimal)
        finally:
            Path(temp_path).unlink()
