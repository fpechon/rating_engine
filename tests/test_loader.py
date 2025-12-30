"""
Tests unitaires pour TariffLoader et la validation/chargement des tarifs.
"""

import tempfile
from decimal import Decimal
from pathlib import Path

import pytest

from engine.loader import TariffLoader, parse_condition
from engine.nodes import (
    AddNode,
    ConstantNode,
    IfNode,
    InputNode,
    LookupNode,
    MultiplyNode,
    RoundNode,
)
from engine.tables import ExactMatchTable, RangeTable


class TestParseCondition:
    """Tests pour la fonction parse_condition."""

    def test_parse_greater_than(self):
        var, op, threshold = parse_condition("density > 1000")
        assert var == "density"
        assert op == ">"
        assert threshold == Decimal("1000")

    def test_parse_less_than(self):
        var, op, threshold = parse_condition("age < 25")
        assert var == "age"
        assert op == "<"
        assert threshold == Decimal("25")

    def test_parse_greater_than_or_equal(self):
        var, op, threshold = parse_condition("score >= 100")
        assert var == "score"
        assert op == ">="
        assert threshold == Decimal("100")

    def test_parse_less_than_or_equal(self):
        var, op, threshold = parse_condition("distance <= 5000")
        assert var == "distance"
        assert op == "<="
        assert threshold == Decimal("5000")

    def test_parse_with_spaces(self):
        var, op, threshold = parse_condition("  value  >  500  ")
        assert var == "value"
        assert op == ">"
        assert threshold == Decimal("500")

    def test_parse_decimal_threshold(self):
        var, op, threshold = parse_condition("price > 99.99")
        assert var == "price"
        assert op == ">"
        assert threshold == Decimal("99.99")

    def test_parse_invalid_condition_raises_error(self):
        with pytest.raises(ValueError, match="Invalid condition"):
            parse_condition("no_operator_here")

    def test_parse_operator_priority(self):
        # Should parse >= before >, <= before <
        var, op, threshold = parse_condition("x >= 10")
        assert op == ">="


class TestTariffLoaderValidation:
    """Tests pour la validation des tarifs par TariffLoader."""

    def test_validate_missing_nodes_raises_error(self):
        loader = TariffLoader()
        data = {}
        with pytest.raises(ValueError, match="Tariff YAML must contain 'nodes'"):
            loader.validate(data)

    def test_validate_node_missing_type_raises_error(self):
        loader = TariffLoader()
        data = {"nodes": {"node1": {}}}
        with pytest.raises(ValueError, match="Node 'node1' missing 'type'"):
            loader.validate(data)

    def test_validate_constant_missing_value_raises_error(self):
        loader = TariffLoader()
        data = {"nodes": {"constant1": {"type": "CONSTANT"}}}
        with pytest.raises(ValueError, match="CONSTANT node 'constant1' missing 'value'"):
            loader.validate(data)

    def test_validate_add_missing_inputs_raises_error(self):
        loader = TariffLoader()
        data = {"nodes": {"sum": {"type": "ADD"}}}
        with pytest.raises(ValueError, match="ADD node 'sum' must have non-empty 'inputs' list"):
            loader.validate(data)

    def test_validate_add_empty_inputs_raises_error(self):
        loader = TariffLoader()
        data = {"nodes": {"sum": {"type": "ADD", "inputs": []}}}
        with pytest.raises(ValueError, match="ADD node 'sum' must have non-empty 'inputs' list"):
            loader.validate(data)

    def test_validate_multiply_missing_inputs_raises_error(self):
        loader = TariffLoader()
        data = {"nodes": {"product": {"type": "MULTIPLY"}}}
        with pytest.raises(
            ValueError, match="MULTIPLY node 'product' must have non-empty 'inputs' list"
        ):
            loader.validate(data)

    def test_validate_lookup_missing_table_raises_error(self):
        loader = TariffLoader()
        data = {"nodes": {"lookup": {"type": "LOOKUP", "key_node": "age"}}}
        with pytest.raises(ValueError, match="LOOKUP node 'lookup' must have a 'table'"):
            loader.validate(data)

    def test_validate_lookup_unknown_table_raises_error(self):
        loader = TariffLoader()
        data = {
            "nodes": {
                "age": {"type": "INPUT"},
                "lookup": {"type": "LOOKUP", "table": "unknown_table", "key_node": "age"},
            }
        }
        with pytest.raises(
            ValueError, match="LOOKUP node 'lookup' references unknown table 'unknown_table'"
        ):
            loader.validate(data)

    def test_validate_lookup_missing_key_node_raises_error(self):
        loader = TariffLoader(tables={"age_table": RangeTable([])})
        data = {"nodes": {"lookup": {"type": "LOOKUP", "table": "age_table"}}}
        with pytest.raises(ValueError, match="LOOKUP node 'lookup' must define 'key_node'"):
            loader.validate(data)

    def test_validate_lookup_unknown_key_node_raises_error(self):
        loader = TariffLoader(tables={"age_table": RangeTable([])})
        data = {
            "nodes": {
                "lookup": {"type": "LOOKUP", "table": "age_table", "key_node": "unknown_node"},
            }
        }
        with pytest.raises(
            ValueError, match="LOOKUP node 'lookup' references unknown key_node 'unknown_node'"
        ):
            loader.validate(data)

    def test_validate_if_missing_condition_raises_error(self):
        loader = TariffLoader()
        data = {"nodes": {"if_node": {"type": "IF", "then": 1, "else": 0}}}
        with pytest.raises(ValueError, match="IF node 'if_node' missing 'condition'"):
            loader.validate(data)

    def test_validate_if_missing_then_raises_error(self):
        loader = TariffLoader()
        data = {
            "nodes": {
                "density": {"type": "INPUT"},
                "if_node": {"type": "IF", "condition": "density > 1000", "else": 0},
            }
        }
        with pytest.raises(ValueError, match="IF node 'if_node' missing 'then'"):
            loader.validate(data)

    def test_validate_if_missing_else_raises_error(self):
        loader = TariffLoader()
        data = {
            "nodes": {
                "density": {"type": "INPUT"},
                "if_node": {"type": "IF", "condition": "density > 1000", "then": 1},
            }
        }
        with pytest.raises(ValueError, match="IF node 'if_node' missing 'else'"):
            loader.validate(data)

    def test_validate_round_missing_input_raises_error(self):
        loader = TariffLoader()
        data = {"nodes": {"rounded": {"type": "ROUND"}}}
        with pytest.raises(ValueError, match="ROUND node 'rounded' missing 'input'"):
            loader.validate(data)

    def test_validate_round_invalid_mode_raises_error(self):
        loader = TariffLoader()
        data = {
            "nodes": {
                "value": {"type": "CONSTANT", "value": 100},
                "rounded": {"type": "ROUND", "input": "value", "mode": "INVALID_MODE"},
            }
        }
        with pytest.raises(
            ValueError, match="ROUND node 'rounded' has invalid mode 'INVALID_MODE'"
        ):
            loader.validate(data)

    def test_validate_input_with_extra_fields_raises_error(self):
        loader = TariffLoader()
        data = {"nodes": {"age": {"type": "INPUT", "extra_field": "should_not_be_here"}}}
        with pytest.raises(ValueError, match="INPUT node 'age' should not have extra fields"):
            loader.validate(data)

    def test_validate_unknown_node_type_raises_error(self):
        loader = TariffLoader()
        data = {"nodes": {"unknown": {"type": "UNKNOWN_TYPE"}}}
        with pytest.raises(ValueError, match="Unknown node type 'UNKNOWN_TYPE'"):
            loader.validate(data)

    def test_validate_valid_tariff_passes(self):
        loader = TariffLoader(tables={"age_table": RangeTable([])})
        data = {
            "nodes": {
                "age": {"type": "INPUT"},
                "base": {"type": "CONSTANT", "value": 500},
                "age_factor": {"type": "LOOKUP", "table": "age_table", "key_node": "age"},
                "premium": {"type": "MULTIPLY", "inputs": ["base", "age_factor"]},
            }
        }
        # Should not raise any error
        loader.validate(data)


class TestTariffLoaderLoad:
    """Tests pour le chargement des tarifs par TariffLoader."""

    def test_load_constant_node(self):
        yaml_content = """
nodes:
  base_premium:
    type: CONSTANT
    value: 500
"""
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".yaml") as f:
            f.write(yaml_content)
            temp_path = f.name

        try:
            loader = TariffLoader()
            nodes = loader.load(temp_path)
            assert "base_premium" in nodes
            assert isinstance(nodes["base_premium"], ConstantNode)
            assert nodes["base_premium"].value == Decimal("500")
        finally:
            Path(temp_path).unlink()

    def test_load_input_node_decimal(self):
        yaml_content = """
nodes:
  driver_age:
    type: INPUT
"""
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".yaml") as f:
            f.write(yaml_content)
            temp_path = f.name

        try:
            loader = TariffLoader()
            nodes = loader.load(temp_path)
            assert "driver_age" in nodes
            assert isinstance(nodes["driver_age"], InputNode)
            assert nodes["driver_age"].dtype is Decimal
        finally:
            Path(temp_path).unlink()

    def test_load_input_node_string(self):
        yaml_content = """
nodes:
  brand:
    type: INPUT
    dtype: str
"""
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".yaml") as f:
            f.write(yaml_content)
            temp_path = f.name

        try:
            loader = TariffLoader()
            nodes = loader.load(temp_path)
            assert "brand" in nodes
            assert isinstance(nodes["brand"], InputNode)
            assert nodes["brand"].dtype is str
        finally:
            Path(temp_path).unlink()

    def test_load_input_node_invalid_dtype_raises_error(self):
        yaml_content = """
nodes:
  value:
    type: INPUT
    dtype: invalid
"""
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".yaml") as f:
            f.write(yaml_content)
            temp_path = f.name

        try:
            loader = TariffLoader()
            with pytest.raises(ValueError, match="INPUT node 'value' has unknown dtype 'invalid'"):
                loader.load(temp_path)
        finally:
            Path(temp_path).unlink()

    def test_load_add_node(self):
        yaml_content = """
nodes:
  a:
    type: CONSTANT
    value: 10
  b:
    type: CONSTANT
    value: 20
  sum:
    type: ADD
    inputs: [a, b]
"""
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".yaml") as f:
            f.write(yaml_content)
            temp_path = f.name

        try:
            loader = TariffLoader()
            nodes = loader.load(temp_path)
            assert "sum" in nodes
            assert isinstance(nodes["sum"], AddNode)
            assert len(nodes["sum"].inputs) == 2
        finally:
            Path(temp_path).unlink()

    def test_load_multiply_node(self):
        yaml_content = """
nodes:
  base:
    type: CONSTANT
    value: 500
  factor:
    type: CONSTANT
    value: 1.2
  premium:
    type: MULTIPLY
    inputs: [base, factor]
"""
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".yaml") as f:
            f.write(yaml_content)
            temp_path = f.name

        try:
            loader = TariffLoader()
            nodes = loader.load(temp_path)
            assert "premium" in nodes
            assert isinstance(nodes["premium"], MultiplyNode)
            assert len(nodes["premium"].inputs) == 2
        finally:
            Path(temp_path).unlink()

    def test_load_lookup_node(self):
        yaml_content = """
nodes:
  age:
    type: INPUT
  age_factor:
    type: LOOKUP
    table: age_table
    key_node: age
"""
        table = RangeTable([{"min": 18, "max": 99, "value": Decimal("1.0")}])
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".yaml") as f:
            f.write(yaml_content)
            temp_path = f.name

        try:
            loader = TariffLoader(tables={"age_table": table})
            nodes = loader.load(temp_path)
            assert "age_factor" in nodes
            assert isinstance(nodes["age_factor"], LookupNode)
            assert nodes["age_factor"].table is table
        finally:
            Path(temp_path).unlink()

    def test_load_if_node(self):
        yaml_content = """
nodes:
  density:
    type: INPUT
  density_factor:
    type: IF
    condition: density > 1000
    then: 1.2
    else: 1.0
"""
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".yaml") as f:
            f.write(yaml_content)
            temp_path = f.name

        try:
            loader = TariffLoader()
            nodes = loader.load(temp_path)
            assert "density_factor" in nodes
            assert isinstance(nodes["density_factor"], IfNode)
            assert nodes["density_factor"].threshold == Decimal("1000")
            assert nodes["density_factor"].then_val == Decimal("1.2")
            assert nodes["density_factor"].else_val == Decimal("1.0")
        finally:
            Path(temp_path).unlink()

    def test_load_round_node(self):
        yaml_content = """
nodes:
  value:
    type: CONSTANT
    value: 123.456
  rounded:
    type: ROUND
    input: value
    decimals: 2
    mode: HALF_UP
"""
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".yaml") as f:
            f.write(yaml_content)
            temp_path = f.name

        try:
            loader = TariffLoader()
            nodes = loader.load(temp_path)
            assert "rounded" in nodes
            assert isinstance(nodes["rounded"], RoundNode)
            assert nodes["rounded"].decimals == 2
        finally:
            Path(temp_path).unlink()

    def test_load_round_node_default_parameters(self):
        yaml_content = """
nodes:
  value:
    type: CONSTANT
    value: 100
  rounded:
    type: ROUND
    input: value
"""
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".yaml") as f:
            f.write(yaml_content)
            temp_path = f.name

        try:
            loader = TariffLoader()
            nodes = loader.load(temp_path)
            assert nodes["rounded"].decimals == 2
        finally:
            Path(temp_path).unlink()

    def test_load_complex_tariff(self):
        yaml_content = """
nodes:
  driver_age:
    type: INPUT
  brand:
    type: INPUT
    dtype: str
  density:
    type: INPUT
  base_premium:
    type: CONSTANT
    value: 500
  fee:
    type: CONSTANT
    value: 25
  age_factor:
    type: LOOKUP
    table: age_table
    key_node: driver_age
  brand_factor:
    type: LOOKUP
    table: brand_table
    key_node: brand
  density_factor:
    type: IF
    condition: density > 1000
    then: 1.2
    else: 1.0
  technical_premium:
    type: MULTIPLY
    inputs: [base_premium, age_factor, brand_factor, density_factor]
  raw_total:
    type: ADD
    inputs: [technical_premium, fee]
  total_premium:
    type: ROUND
    input: raw_total
    decimals: 2
    mode: HALF_UP
"""
        age_table = RangeTable([{"min": 18, "max": 99, "value": Decimal("1.0")}])
        brand_table = ExactMatchTable({"BMW": Decimal("1.2")})

        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".yaml") as f:
            f.write(yaml_content)
            temp_path = f.name

        try:
            loader = TariffLoader(tables={"age_table": age_table, "brand_table": brand_table})
            nodes = loader.load(temp_path)

            # Verify all nodes were created
            assert len(nodes) == 11
            assert all(
                name in nodes
                for name in [
                    "driver_age",
                    "brand",
                    "density",
                    "base_premium",
                    "fee",
                    "age_factor",
                    "brand_factor",
                    "density_factor",
                    "technical_premium",
                    "raw_total",
                    "total_premium",
                ]
            )

            # Verify node types
            assert isinstance(nodes["driver_age"], InputNode)
            assert isinstance(nodes["brand"], InputNode)
            assert isinstance(nodes["base_premium"], ConstantNode)
            assert isinstance(nodes["age_factor"], LookupNode)
            assert isinstance(nodes["density_factor"], IfNode)
            assert isinstance(nodes["technical_premium"], MultiplyNode)
            assert isinstance(nodes["raw_total"], AddNode)
            assert isinstance(nodes["total_premium"], RoundNode)
        finally:
            Path(temp_path).unlink()
