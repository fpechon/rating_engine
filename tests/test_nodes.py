"""
Tests unitaires pour tous les types de nœuds du rating engine.
"""

import operator
from decimal import ROUND_HALF_EVEN, ROUND_HALF_UP, Decimal

import pytest

from engine.nodes import (
    ONE,
    ZERO,
    AddNode,
    ConstantNode,
    IfNode,
    InputNode,
    LookupNode,
    MultiplyNode,
    Node,
    ReduceNode,
    RoundNode,
    to_decimal,
)
from engine.tables import ExactMatchTable, RangeTable


class TestToDecimal:
    """Tests pour la fonction to_decimal."""

    def test_none_preserved(self):
        assert to_decimal(None) is None

    def test_decimal_preserved(self):
        val = Decimal("123.45")
        assert to_decimal(val) is val

    def test_int_converted(self):
        assert to_decimal(42) == Decimal("42")

    def test_float_converted(self):
        assert to_decimal(3.14) == Decimal("3.14")

    def test_string_converted(self):
        assert to_decimal("99.99") == Decimal("99.99")


class TestConstantNode:
    """Tests pour ConstantNode."""

    def test_initialization(self):
        node = ConstantNode("base_premium", Decimal("500"))
        assert node.name == "base_premium"
        assert node.value == Decimal("500")

    def test_no_dependencies(self):
        node = ConstantNode("constant", Decimal("100"))
        assert node.dependencies() == []

    def test_evaluate_returns_value(self):
        node = ConstantNode("fee", Decimal("25"))
        result = node.evaluate({}, {})
        assert result == Decimal("25")

    def test_repr(self):
        node = ConstantNode("test", Decimal("10"))
        assert "ConstantNode" in repr(node)
        assert "test" in repr(node)


class TestInputNode:
    """Tests pour InputNode."""

    def test_initialization(self):
        node = InputNode("driver_age")
        assert node.name == "driver_age"
        assert node.dtype is Decimal

    def test_no_dependencies(self):
        node = InputNode("brand")
        assert node.dependencies() == []

    def test_evaluate_with_decimal(self):
        node = InputNode("age")
        context = {"age": 42}
        result = node.evaluate(context, {})
        assert result == Decimal("42")

    def test_evaluate_with_string(self):
        node = InputNode("brand", dtype=str)
        context = {"brand": "BMW"}
        result = node.evaluate(context, {})
        assert result == "BMW"

    def test_evaluate_missing_key_raises_error(self):
        node = InputNode("missing_var")
        with pytest.raises(KeyError, match="Missing input variable: missing_var"):
            node.evaluate({}, {})

    def test_evaluate_none_value_returns_none(self):
        node = InputNode("nullable")
        context = {"nullable": None}
        result = node.evaluate(context, {})
        assert result is None

    def test_evaluate_decimal_conversion(self):
        node = InputNode("price")
        context = {"price": "123.45"}
        result = node.evaluate(context, {})
        assert result == Decimal("123.45")
        assert isinstance(result, Decimal)


class TestLookupNode:
    """Tests pour LookupNode."""

    def test_initialization(self):
        key_node = InputNode("age")
        table = RangeTable([{"min": 18, "max": 25, "value": Decimal("1.5")}])
        node = LookupNode("age_factor", table, key_node)
        assert node.name == "age_factor"
        assert node.table is table
        assert node.key_node is key_node

    def test_initialization_without_key_node_raises_error(self):
        table = RangeTable([{"min": 0, "max": 100, "value": Decimal("1.0")}])
        with pytest.raises(ValueError, match="LookupNode requires a key_node"):
            LookupNode("lookup", table, None)

    def test_dependencies(self):
        key_node = InputNode("brand")
        table = ExactMatchTable({"BMW": Decimal("1.2")})
        node = LookupNode("brand_factor", table, key_node)
        assert node.dependencies() == ["brand"]

    def test_evaluate_with_range_table(self):
        key_node = InputNode("age")
        table = RangeTable(
            [
                {"min": 18, "max": 25, "value": Decimal("1.5")},
                {"min": 26, "max": 65, "value": Decimal("1.0")},
            ]
        )
        node = LookupNode("age_factor", table, key_node)

        context = {"age": 30}
        cache = {"age": Decimal("30")}
        result = node.evaluate(context, cache)
        assert result == Decimal("1.0")

    def test_evaluate_with_exact_table(self):
        key_node = InputNode("brand")
        table = ExactMatchTable({"BMW": Decimal("1.2"), "Audi": Decimal("1.1")})
        node = LookupNode("brand_factor", table, key_node)

        context = {"brand": "BMW"}
        cache = {"brand": "BMW"}
        result = node.evaluate(context, cache)
        assert result == Decimal("1.2")


class TestReduceNode:
    """Tests pour ReduceNode."""

    def test_initialization(self):
        inputs = [ConstantNode("a", Decimal("10")), ConstantNode("b", Decimal("20"))]
        node = ReduceNode("sum", inputs, operator.add, ZERO)
        assert node.name == "sum"
        assert node.inputs == inputs
        assert node.op is operator.add
        assert node.identity == ZERO

    def test_dependencies(self):
        inputs = [
            ConstantNode("x", Decimal("1")),
            ConstantNode("y", Decimal("2")),
            ConstantNode("z", Decimal("3")),
        ]
        node = ReduceNode("total", inputs, operator.add, ZERO)
        assert node.dependencies() == ["x", "y", "z"]

    def test_evaluate_addition(self):
        inputs = [ConstantNode("a", Decimal("10")), ConstantNode("b", Decimal("20"))]
        node = ReduceNode("sum", inputs, operator.add, ZERO)

        cache = {"a": Decimal("10"), "b": Decimal("20")}
        result = node.evaluate({}, cache)
        assert result == Decimal("30")

    def test_evaluate_multiplication(self):
        inputs = [ConstantNode("a", Decimal("2")), ConstantNode("b", Decimal("3"))]
        node = ReduceNode("product", inputs, operator.mul, ONE)

        cache = {"a": Decimal("2"), "b": Decimal("3")}
        result = node.evaluate({}, cache)
        assert result == Decimal("6")

    def test_evaluate_with_none_returns_none(self):
        inputs = [ConstantNode("a", Decimal("10")), ConstantNode("b", Decimal("20"))]
        node = ReduceNode("sum", inputs, operator.add, ZERO)

        cache = {"a": Decimal("10"), "b": None}
        result = node.evaluate({}, cache)
        assert result is None

    def test_evaluate_empty_inputs(self):
        node = ReduceNode("empty_sum", [], operator.add, ZERO)
        result = node.evaluate({}, {})
        assert result == ZERO


class TestAddNode:
    """Tests pour AddNode."""

    def test_initialization(self):
        inputs = [ConstantNode("a", Decimal("10")), ConstantNode("b", Decimal("20"))]
        node = AddNode("total", inputs)
        assert node.name == "total"
        assert node.inputs == inputs
        assert node.identity == ZERO

    def test_evaluate_sum(self):
        inputs = [
            ConstantNode("premium", Decimal("500")),
            ConstantNode("fee", Decimal("25")),
            ConstantNode("tax", Decimal("50")),
        ]
        node = AddNode("total_premium", inputs)

        cache = {"premium": Decimal("500"), "fee": Decimal("25"), "tax": Decimal("50")}
        result = node.evaluate({}, cache)
        assert result == Decimal("575")

    def test_evaluate_two_values(self):
        inputs = [ConstantNode("a", Decimal("100")), ConstantNode("b", Decimal("200"))]
        node = AddNode("sum", inputs)

        cache = {"a": Decimal("100"), "b": Decimal("200")}
        result = node.evaluate({}, cache)
        assert result == Decimal("300")


class TestMultiplyNode:
    """Tests pour MultiplyNode."""

    def test_initialization(self):
        inputs = [ConstantNode("a", Decimal("2")), ConstantNode("b", Decimal("3"))]
        node = MultiplyNode("product", inputs)
        assert node.name == "product"
        assert node.inputs == inputs
        assert node.identity == ONE

    def test_evaluate_product(self):
        inputs = [
            ConstantNode("base", Decimal("500")),
            ConstantNode("age_factor", Decimal("1.2")),
            ConstantNode("brand_factor", Decimal("0.9")),
        ]
        node = MultiplyNode("technical_premium", inputs)

        cache = {
            "base": Decimal("500"),
            "age_factor": Decimal("1.2"),
            "brand_factor": Decimal("0.9"),
        }
        result = node.evaluate({}, cache)
        assert result == Decimal("540")

    def test_evaluate_with_one(self):
        inputs = [ConstantNode("value", Decimal("42")), ConstantNode("one", ONE)]
        node = MultiplyNode("result", inputs)

        cache = {"value": Decimal("42"), "one": ONE}
        result = node.evaluate({}, cache)
        assert result == Decimal("42")


class TestIfNode:
    """Tests pour IfNode."""

    def test_initialization_with_string_operator(self):
        var_node = InputNode("density")
        node = IfNode("density_factor", var_node, ">", 1000, Decimal("1.2"), Decimal("1.0"))
        assert node.name == "density_factor"
        assert node.var_node is var_node
        assert node.threshold == Decimal("1000")
        assert node.then_val == Decimal("1.2")
        assert node.else_val == Decimal("1.0")

    def test_initialization_with_callable_operator(self):
        var_node = InputNode("age")
        node = IfNode("factor", var_node, operator.lt, 25, Decimal("1.5"), Decimal("1.0"))
        assert node.op is operator.lt

    def test_initialization_with_invalid_operator_raises_error(self):
        var_node = InputNode("value")
        with pytest.raises(ValueError, match="Unknown operator symbol"):
            IfNode("test", var_node, "invalid", 100, Decimal("1"), Decimal("2"))

    def test_dependencies(self):
        var_node = InputNode("age")
        node = IfNode("age_check", var_node, ">", 18, Decimal("1"), Decimal("0"))
        assert node.dependencies() == ["age"]

    def test_evaluate_condition_true_greater_than(self):
        var_node = InputNode("density")
        node = IfNode("density_factor", var_node, ">", 1000, Decimal("1.2"), Decimal("1.0"))

        context = {"density": 1500}
        cache = {"density": Decimal("1500")}
        result = node.evaluate(context, cache)
        assert result == Decimal("1.2")

    def test_evaluate_condition_false_greater_than(self):
        var_node = InputNode("density")
        node = IfNode("density_factor", var_node, ">", 1000, Decimal("1.2"), Decimal("1.0"))

        context = {"density": 500}
        cache = {"density": Decimal("500")}
        result = node.evaluate(context, cache)
        assert result == Decimal("1.0")

    def test_evaluate_condition_true_less_than(self):
        var_node = InputNode("age")
        node = IfNode("young_driver", var_node, "<", 25, Decimal("1.5"), Decimal("1.0"))

        cache = {"age": Decimal("22")}
        result = node.evaluate({}, cache)
        assert result == Decimal("1.5")

    def test_evaluate_condition_false_less_than(self):
        var_node = InputNode("age")
        node = IfNode("young_driver", var_node, "<", 25, Decimal("1.5"), Decimal("1.0"))

        cache = {"age": Decimal("30")}
        result = node.evaluate({}, cache)
        assert result == Decimal("1.0")

    def test_evaluate_greater_than_or_equal(self):
        var_node = InputNode("score")
        node = IfNode("bonus", var_node, ">=", 100, Decimal("10"), Decimal("0"))

        cache = {"score": Decimal("100")}
        result = node.evaluate({}, cache)
        assert result == Decimal("10")

    def test_evaluate_less_than_or_equal(self):
        var_node = InputNode("distance")
        node = IfNode("discount", var_node, "<=", 5000, Decimal("0.9"), Decimal("1.0"))

        cache = {"distance": Decimal("5000")}
        result = node.evaluate({}, cache)
        assert result == Decimal("0.9")

    def test_evaluate_with_none_raises_error(self):
        var_node = InputNode("value")
        node = IfNode("check", var_node, ">", 100, Decimal("1"), Decimal("0"))

        cache = {"value": None}
        with pytest.raises(ValueError, match="IF node .* got None"):
            node.evaluate({}, cache)


class TestRoundNode:
    """Tests pour RoundNode."""

    def test_initialization(self):
        input_node = ConstantNode("value", Decimal("123.456"))
        node = RoundNode("rounded", input_node, 2, "HALF_UP")
        assert node.name == "rounded"
        assert node.input_node is input_node
        assert node.decimals == 2
        assert node.rounding == ROUND_HALF_UP

    def test_dependencies(self):
        input_node = ConstantNode("premium", Decimal("500.555"))
        node = RoundNode("final_premium", input_node, 2, "HALF_UP")
        assert node.dependencies() == ["premium"]

    def test_evaluate_round_half_up_round_up(self):
        input_node = ConstantNode("value", Decimal("123.455"))
        node = RoundNode("rounded", input_node, 2, "HALF_UP")

        cache = {"value": Decimal("123.455")}
        result = node.evaluate({}, cache)
        assert result == Decimal("123.46")

    def test_evaluate_round_half_up_round_down(self):
        input_node = ConstantNode("value", Decimal("123.454"))
        node = RoundNode("rounded", input_node, 2, "HALF_UP")

        cache = {"value": Decimal("123.454")}
        result = node.evaluate({}, cache)
        assert result == Decimal("123.45")

    def test_evaluate_round_half_even(self):
        input_node = ConstantNode("value", Decimal("123.455"))
        node = RoundNode("rounded", input_node, 2, "HALF_EVEN")

        cache = {"value": Decimal("123.455")}
        result = node.evaluate({}, cache)
        # HALF_EVEN rounds to nearest even number (123.46)
        assert result == Decimal("123.46")

    def test_evaluate_round_half_even_to_even(self):
        input_node = ConstantNode("value", Decimal("123.445"))
        node = RoundNode("rounded", input_node, 2, "HALF_EVEN")

        cache = {"value": Decimal("123.445")}
        result = node.evaluate({}, cache)
        # HALF_EVEN rounds to nearest even number (123.44)
        assert result == Decimal("123.44")

    def test_evaluate_zero_decimals(self):
        input_node = ConstantNode("value", Decimal("123.7"))
        node = RoundNode("rounded", input_node, 0, "HALF_UP")

        cache = {"value": Decimal("123.7")}
        result = node.evaluate({}, cache)
        assert result == Decimal("124")

    def test_evaluate_with_none_returns_none(self):
        input_node = InputNode("nullable")
        node = RoundNode("rounded", input_node, 2, "HALF_UP")

        cache = {"nullable": None}
        result = node.evaluate({}, cache)
        assert result is None

    def test_evaluate_three_decimals(self):
        input_node = ConstantNode("value", Decimal("99.9999"))
        node = RoundNode("rounded", input_node, 3, "HALF_UP")

        cache = {"value": Decimal("99.9999")}
        result = node.evaluate({}, cache)
        assert result == Decimal("100.000")
