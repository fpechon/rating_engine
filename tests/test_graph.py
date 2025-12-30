"""
Tests unitaires pour TariffGraph et l'évaluation du graphe.
"""
import pytest
from decimal import Decimal
from engine.graph import TariffGraph
from engine.nodes import (
    ConstantNode,
    InputNode,
    AddNode,
    MultiplyNode,
    IfNode,
    LookupNode,
    RoundNode,
)
from engine.tables import RangeTable, ExactMatchTable


class TestTariffGraph:
    """Tests pour TariffGraph."""

    def test_initialization(self):
        nodes = {
            "constant": ConstantNode("constant", Decimal("100")),
        }
        graph = TariffGraph(nodes)
        assert graph.nodes == nodes

    def test_evaluate_simple_constant(self):
        nodes = {
            "result": ConstantNode("result", Decimal("42")),
        }
        graph = TariffGraph(nodes)
        result = graph.evaluate("result", {})
        assert result == Decimal("42")

    def test_evaluate_input_node(self):
        nodes = {
            "age": InputNode("age"),
        }
        graph = TariffGraph(nodes)
        context = {"age": 30}
        result = graph.evaluate("age", context)
        assert result == Decimal("30")

    def test_evaluate_with_dependencies(self):
        a = ConstantNode("a", Decimal("10"))
        b = ConstantNode("b", Decimal("20"))
        sum_node = AddNode("sum", [a, b])
        nodes = {"a": a, "b": b, "sum": sum_node}
        graph = TariffGraph(nodes)
        result = graph.evaluate("sum", {})
        assert result == Decimal("30")

    def test_evaluate_complex_graph(self):
        # Graph: base * factor + fee
        base = ConstantNode("base", Decimal("500"))
        factor = ConstantNode("factor", Decimal("1.2"))
        fee = ConstantNode("fee", Decimal("25"))
        premium = MultiplyNode("premium", [base, factor])
        total = AddNode("total", [premium, fee])
        nodes = {"base": base, "factor": factor, "fee": fee, "premium": premium, "total": total}
        graph = TariffGraph(nodes)
        result = graph.evaluate("total", {})
        # 500 * 1.2 + 25 = 625
        assert result == Decimal("625")

    def test_evaluate_with_input_and_calculation(self):
        age = InputNode("age")
        base = ConstantNode("base", Decimal("100"))
        age_factor = ConstantNode("age_factor", Decimal("1.5"))
        premium = MultiplyNode("premium", [base, age_factor])
        nodes = {"age": age, "base": base, "age_factor": age_factor, "premium": premium}
        graph = TariffGraph(nodes)
        context = {"age": 25}
        result = graph.evaluate("premium", context)
        assert result == Decimal("150")

    def test_evaluate_with_lookup(self):
        table = RangeTable([
            {"min": 18, "max": 25, "value": Decimal("1.8")},
            {"min": 26, "max": 65, "value": Decimal("1.0")},
        ])
        age = InputNode("age")
        age_factor = LookupNode("age_factor", table, age)
        base = ConstantNode("base", Decimal("500"))
        premium = MultiplyNode("premium", [base, age_factor])
        nodes = {"age": age, "age_factor": age_factor, "base": base, "premium": premium}
        graph = TariffGraph(nodes)

        # Young driver (age 22)
        result = graph.evaluate("premium", {"age": 22})
        assert result == Decimal("900")  # 500 * 1.8

        # Older driver (age 40)
        result = graph.evaluate("premium", {"age": 40})
        assert result == Decimal("500")  # 500 * 1.0

    def test_evaluate_with_conditional(self):
        density = InputNode("density")
        density_factor = IfNode("density_factor", density, ">", 1000, Decimal("1.2"), Decimal("1.0"))
        base = ConstantNode("base", Decimal("500"))
        premium = MultiplyNode("premium", [base, density_factor])
        nodes = {"density": density, "density_factor": density_factor, "base": base, "premium": premium}
        graph = TariffGraph(nodes)

        # High density
        result = graph.evaluate("premium", {"density": 1500})
        assert result == Decimal("600")  # 500 * 1.2

        # Low density
        result = graph.evaluate("premium", {"density": 500})
        assert result == Decimal("500")  # 500 * 1.0

    def test_evaluate_with_rounding(self):
        base = ConstantNode("base", Decimal("123.456"))
        rounded = RoundNode("rounded", base, 2, "HALF_UP")
        nodes = {"base": base, "rounded": rounded}
        graph = TariffGraph(nodes)
        result = graph.evaluate("rounded", {})
        assert result == Decimal("123.46")

    def test_evaluate_caching(self):
        # Create a graph where a node is used multiple times
        value = ConstantNode("value", Decimal("10"))
        sum1 = AddNode("sum1", [value, value])
        sum2 = AddNode("sum2", [sum1, value])
        nodes = {"value": value, "sum1": sum1, "sum2": sum2}
        graph = TariffGraph(nodes)
        result = graph.evaluate("sum2", {})
        # (10 + 10) + 10 = 30
        assert result == Decimal("30")

    def test_evaluate_with_trace(self):
        a = ConstantNode("a", Decimal("10"))
        b = ConstantNode("b", Decimal("20"))
        sum_node = AddNode("sum", [a, b])
        nodes = {"a": a, "b": b, "sum": sum_node}
        graph = TariffGraph(nodes)
        trace = {}
        result = graph.evaluate("sum", {}, trace=trace)

        # Check that trace was populated
        assert "a" in trace
        assert "b" in trace
        assert "sum" in trace
        assert trace["a"]["value"] == Decimal("10")
        assert trace["b"]["value"] == Decimal("20")
        assert trace["sum"]["value"] == Decimal("30")
        assert trace["a"]["type"] == "ConstantNode"
        assert trace["sum"]["type"] == "AddNode"

    def test_evaluate_trace_returns_trace_not_value(self):
        nodes = {
            "result": ConstantNode("result", Decimal("42")),
        }
        graph = TariffGraph(nodes)
        trace = {}
        result = graph.evaluate("result", {}, trace=trace)
        # When trace is provided, result should be the trace dict
        assert result is trace
        assert trace["result"]["value"] == Decimal("42")

    def test_evaluate_deep_dependency_chain(self):
        # Create a chain: a -> b -> c -> d -> e
        a = ConstantNode("a", Decimal("1"))
        _1 = ConstantNode("_1", Decimal("1"))
        _2 = ConstantNode("_2", Decimal("1"))
        _3 = ConstantNode("_3", Decimal("1"))
        _4 = ConstantNode("_4", Decimal("1"))
        b = AddNode("b", [a, _1])
        c = AddNode("c", [b, _2])
        d = AddNode("d", [c, _3])
        e = AddNode("e", [d, _4])
        nodes = {"a": a, "b": b, "c": c, "d": d, "e": e, "_1": _1, "_2": _2, "_3": _3, "_4": _4}
        graph = TariffGraph(nodes)
        result = graph.evaluate("e", {})
        # 1 + 1 + 1 + 1 + 1 = 5
        assert result == Decimal("5")

    def test_evaluate_multiple_paths_to_node(self):
        # Diamond dependency: a -> b -> d, a -> c -> d
        a = ConstantNode("a", Decimal("10"))
        _1 = ConstantNode("_1", Decimal("5"))
        _2 = ConstantNode("_2", Decimal("3"))
        b = AddNode("b", [a, _1])
        c = AddNode("c", [a, _2])
        d = AddNode("d", [b, c])
        nodes = {"a": a, "b": b, "c": c, "d": d, "_1": _1, "_2": _2}
        graph = TariffGraph(nodes)
        result = graph.evaluate("d", {})
        # b = 10 + 5 = 15, c = 10 + 3 = 13, d = 15 + 13 = 28
        assert result == Decimal("28")

    def test_evaluate_with_none_propagation(self):
        nullable = InputNode("nullable")
        constant = ConstantNode("constant", Decimal("10"))
        sum_node = AddNode("sum", [nullable, constant])
        nodes = {"nullable": nullable, "constant": constant, "sum": sum_node}
        graph = TariffGraph(nodes)
        result = graph.evaluate("sum", {"nullable": None})
        assert result is None

    def test_evaluate_realistic_motor_insurance(self):
        """Test simulating a realistic motor insurance calculation."""
        # Tables
        age_table = RangeTable([
            {"min": 18, "max": 25, "value": Decimal("1.8")},
            {"min": 26, "max": 65, "value": Decimal("1.0")},
            {"min": 66, "max": 99, "value": Decimal("1.3")},
        ])
        brand_table = ExactMatchTable({
            "BMW": Decimal("1.2"),
            "Audi": Decimal("1.1"),
            "__DEFAULT__": Decimal("1.0"),
        })

        # Nodes
        driver_age = InputNode("driver_age")
        brand = InputNode("brand", dtype=str)
        density = InputNode("density")
        base_premium = ConstantNode("base_premium", Decimal("500"))
        fee = ConstantNode("fee", Decimal("25"))
        age_factor = LookupNode("age_factor", age_table, driver_age)
        brand_factor = LookupNode("brand_factor", brand_table, brand)
        density_factor = IfNode("density_factor", density, ">", 1000, Decimal("1.2"), Decimal("1.0"))
        technical_premium = MultiplyNode("technical_premium", [base_premium, age_factor, brand_factor, density_factor])
        raw_total = AddNode("raw_total", [technical_premium, fee])
        total_premium = RoundNode("total_premium", raw_total, 2, "HALF_UP")

        nodes = {
            "driver_age": driver_age,
            "brand": brand,
            "density": density,
            "base_premium": base_premium,
            "fee": fee,
            "age_factor": age_factor,
            "brand_factor": brand_factor,
            "density_factor": density_factor,
            "technical_premium": technical_premium,
            "raw_total": raw_total,
            "total_premium": total_premium,
        }

        graph = TariffGraph(nodes)

        # Test case 1: Young driver, BMW, high density
        context1 = {"driver_age": 22, "brand": "BMW", "density": 1500}
        result1 = graph.evaluate("total_premium", context1)
        # 500 * 1.8 * 1.2 * 1.2 + 25 = 1296 + 25 = 1321.00
        assert result1 == Decimal("1321.00")

        # Test case 2: Middle-aged driver, default brand, low density
        context2 = {"driver_age": 40, "brand": "Toyota", "density": 500}
        result2 = graph.evaluate("total_premium", context2)
        # 500 * 1.0 * 1.0 * 1.0 + 25 = 525.00
        assert result2 == Decimal("525.00")

        # Test case 3: Senior driver, Audi, high density
        context3 = {"driver_age": 70, "brand": "Audi", "density": 2000}
        result3 = graph.evaluate("total_premium", context3)
        # 500 * 1.3 * 1.1 * 1.2 + 25 = 858 + 25 = 883.00
        assert result3 == Decimal("883.00")
