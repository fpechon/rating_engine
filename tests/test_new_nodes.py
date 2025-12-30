"""
Tests pour les nouveaux types de nœuds (Phase 2).

Ce module teste les nœuds ajoutés dans la Phase 2:
- SwitchNode: Branchement multiple
- CoalesceNode: Première valeur non-nulle
- MinNode/MaxNode: Comparaisons min/max
- AbsNode: Valeur absolue
"""

import pytest
from decimal import Decimal
from engine.nodes import (
    ConstantNode,
    InputNode,
    SwitchNode,
    CoalesceNode,
    MinNode,
    MaxNode,
    AbsNode,
)


class TestSwitchNode:
    """Tests pour SwitchNode."""

    def test_init_valid(self):
        """Test l'initialisation d'un SwitchNode valide."""
        var_node = InputNode("region", dtype=str)
        cases = {"Paris": Decimal("1.5"), "Lyon": Decimal("1.3")}
        node = SwitchNode("region_factor", var_node, cases, default=Decimal("1.0"))

        assert node.name == "region_factor"
        assert node.var_node == var_node
        assert len(node.cases) == 2
        assert node.default == Decimal("1.0")

    def test_init_without_default(self):
        """Test l'initialisation sans valeur par défaut."""
        var_node = InputNode("status", dtype=str)
        cases = {"active": Decimal("1.0"), "inactive": Decimal("0.0")}
        node = SwitchNode("status_factor", var_node, cases)

        assert node.default is None

    def test_init_no_var_node(self):
        """Test que l'initialisation échoue sans var_node."""
        cases = {"A": Decimal("1")}
        with pytest.raises(ValueError, match="requires a var_node"):
            SwitchNode("test", None, cases)

    def test_init_empty_cases(self):
        """Test que l'initialisation échoue avec cases vide."""
        var_node = InputNode("x")
        with pytest.raises(ValueError, match="at least one case"):
            SwitchNode("test", var_node, {})

    def test_dependencies(self):
        """Test que les dépendances sont correctement retournées."""
        var_node = InputNode("region", dtype=str)
        cases = {"Paris": Decimal("1.5")}
        node = SwitchNode("region_factor", var_node, cases)

        deps = node.dependencies()
        assert deps == ["region"]

    def test_evaluate_matching_case_string(self):
        """Test l'évaluation avec un cas correspondant (clé string)."""
        var_node = InputNode("region", dtype=str)
        cases = {"Paris": Decimal("1.5"), "Lyon": Decimal("1.3")}
        node = SwitchNode("region_factor", var_node, cases, default=Decimal("1.0"))

        context = {"region": "Paris"}
        cache = {"region": "Paris"}
        result = node.evaluate(context, cache)

        assert result == Decimal("1.5")

    def test_evaluate_matching_case_numeric(self):
        """Test l'évaluation avec un cas correspondant (clé numérique)."""
        var_node = InputNode("zone")
        cases = {1: Decimal("1.2"), 2: Decimal("1.1"), 3: Decimal("1.0")}
        node = SwitchNode("zone_factor", var_node, cases)

        context = {"zone": 2}
        cache = {"zone": Decimal("2")}
        result = node.evaluate(context, cache)

        assert result == Decimal("1.1")

    def test_evaluate_default_case(self):
        """Test l'évaluation avec valeur par défaut."""
        var_node = InputNode("region", dtype=str)
        cases = {"Paris": Decimal("1.5"), "Lyon": Decimal("1.3")}
        node = SwitchNode("region_factor", var_node, cases, default=Decimal("1.0"))

        context = {"region": "Marseille"}
        cache = {"region": "Marseille"}
        result = node.evaluate(context, cache)

        assert result == Decimal("1.0")

    def test_evaluate_no_match_no_default(self):
        """Test l'évaluation sans correspondance et sans défaut."""
        var_node = InputNode("region", dtype=str)
        cases = {"Paris": Decimal("1.5"), "Lyon": Decimal("1.3")}
        node = SwitchNode("region_factor", var_node, cases)

        context = {"region": "Marseille"}
        cache = {"region": "Marseille"}

        with pytest.raises(KeyError, match="not found in cases"):
            node.evaluate(context, cache)


class TestCoalesceNode:
    """Tests pour CoalesceNode."""

    def test_init_valid(self):
        """Test l'initialisation d'un CoalesceNode valide."""
        a = InputNode("discount")
        b = ConstantNode("default", Decimal("0"))
        node = CoalesceNode("final_discount", [a, b])

        assert node.name == "final_discount"
        assert len(node.inputs) == 2

    def test_init_empty_inputs(self):
        """Test que l'initialisation échoue avec inputs vide."""
        with pytest.raises(ValueError, match="at least one input"):
            CoalesceNode("test", [])

    def test_dependencies(self):
        """Test que les dépendances sont correctement retournées."""
        a = InputNode("discount")
        b = ConstantNode("default", Decimal("0"))
        c = ConstantNode("fallback", Decimal("5"))
        node = CoalesceNode("final", [a, b, c])

        deps = node.dependencies()
        assert deps == ["discount", "default", "fallback"]

    def test_evaluate_first_non_null(self):
        """Test que la première valeur non-nulle est retournée."""
        a = ConstantNode("a", None)
        b = ConstantNode("b", Decimal("10"))
        c = ConstantNode("c", Decimal("20"))
        node = CoalesceNode("result", [a, b, c])

        context = {}
        cache = {"a": None, "b": Decimal("10"), "c": Decimal("20")}
        result = node.evaluate(context, cache)

        assert result == Decimal("10")

    def test_evaluate_all_null(self):
        """Test que None est retourné si toutes les valeurs sont None."""
        a = ConstantNode("a", None)
        b = ConstantNode("b", None)
        node = CoalesceNode("result", [a, b])

        context = {}
        cache = {"a": None, "b": None}
        result = node.evaluate(context, cache)

        assert result is None

    def test_evaluate_first_value_non_null(self):
        """Test que le premier input est retourné s'il n'est pas None."""
        a = ConstantNode("a", Decimal("5"))
        b = ConstantNode("b", Decimal("10"))
        node = CoalesceNode("result", [a, b])

        context = {}
        cache = {"a": Decimal("5"), "b": Decimal("10")}
        result = node.evaluate(context, cache)

        assert result == Decimal("5")


class TestMinNode:
    """Tests pour MinNode."""

    def test_init_valid(self):
        """Test l'initialisation d'un MinNode valide."""
        a = ConstantNode("a", Decimal("10"))
        b = ConstantNode("b", Decimal("20"))
        node = MinNode("min_val", [a, b])

        assert node.name == "min_val"
        assert len(node.inputs) == 2

    def test_init_empty_inputs(self):
        """Test que l'initialisation échoue avec inputs vide."""
        with pytest.raises(ValueError, match="at least one input"):
            MinNode("test", [])

    def test_dependencies(self):
        """Test que les dépendances sont correctement retournées."""
        a = ConstantNode("a", Decimal("10"))
        b = ConstantNode("b", Decimal("20"))
        c = ConstantNode("c", Decimal("15"))
        node = MinNode("min_val", [a, b, c])

        deps = node.dependencies()
        assert deps == ["a", "b", "c"]

    def test_evaluate_two_values(self):
        """Test l'évaluation avec deux valeurs."""
        a = ConstantNode("a", Decimal("10"))
        b = ConstantNode("b", Decimal("20"))
        node = MinNode("min_val", [a, b])

        context = {}
        cache = {"a": Decimal("10"), "b": Decimal("20")}
        result = node.evaluate(context, cache)

        assert result == Decimal("10")

    def test_evaluate_multiple_values(self):
        """Test l'évaluation avec plusieurs valeurs."""
        a = ConstantNode("a", Decimal("10"))
        b = ConstantNode("b", Decimal("5"))
        c = ConstantNode("c", Decimal("15"))
        node = MinNode("min_val", [a, b, c])

        context = {}
        cache = {"a": Decimal("10"), "b": Decimal("5"), "c": Decimal("15")}
        result = node.evaluate(context, cache)

        assert result == Decimal("5")

    def test_evaluate_with_none_values(self):
        """Test l'évaluation avec des valeurs None (ignorées)."""
        a = ConstantNode("a", None)
        b = ConstantNode("b", Decimal("20"))
        c = ConstantNode("c", Decimal("15"))
        node = MinNode("min_val", [a, b, c])

        context = {}
        cache = {"a": None, "b": Decimal("20"), "c": Decimal("15")}
        result = node.evaluate(context, cache)

        assert result == Decimal("15")

    def test_evaluate_all_none(self):
        """Test l'évaluation avec toutes les valeurs None."""
        a = ConstantNode("a", None)
        b = ConstantNode("b", None)
        node = MinNode("min_val", [a, b])

        context = {}
        cache = {"a": None, "b": None}
        result = node.evaluate(context, cache)

        assert result is None

    def test_evaluate_negative_values(self):
        """Test l'évaluation avec des valeurs négatives."""
        a = ConstantNode("a", Decimal("-10"))
        b = ConstantNode("b", Decimal("5"))
        c = ConstantNode("c", Decimal("-20"))
        node = MinNode("min_val", [a, b, c])

        context = {}
        cache = {"a": Decimal("-10"), "b": Decimal("5"), "c": Decimal("-20")}
        result = node.evaluate(context, cache)

        assert result == Decimal("-20")


class TestMaxNode:
    """Tests pour MaxNode."""

    def test_init_valid(self):
        """Test l'initialisation d'un MaxNode valide."""
        a = ConstantNode("a", Decimal("10"))
        b = ConstantNode("b", Decimal("20"))
        node = MaxNode("max_val", [a, b])

        assert node.name == "max_val"
        assert len(node.inputs) == 2

    def test_init_empty_inputs(self):
        """Test que l'initialisation échoue avec inputs vide."""
        with pytest.raises(ValueError, match="at least one input"):
            MaxNode("test", [])

    def test_dependencies(self):
        """Test que les dépendances sont correctement retournées."""
        a = ConstantNode("a", Decimal("10"))
        b = ConstantNode("b", Decimal("20"))
        c = ConstantNode("c", Decimal("15"))
        node = MaxNode("max_val", [a, b, c])

        deps = node.dependencies()
        assert deps == ["a", "b", "c"]

    def test_evaluate_two_values(self):
        """Test l'évaluation avec deux valeurs."""
        a = ConstantNode("a", Decimal("10"))
        b = ConstantNode("b", Decimal("20"))
        node = MaxNode("max_val", [a, b])

        context = {}
        cache = {"a": Decimal("10"), "b": Decimal("20")}
        result = node.evaluate(context, cache)

        assert result == Decimal("20")

    def test_evaluate_multiple_values(self):
        """Test l'évaluation avec plusieurs valeurs."""
        a = ConstantNode("a", Decimal("10"))
        b = ConstantNode("b", Decimal("25"))
        c = ConstantNode("c", Decimal("15"))
        node = MaxNode("max_val", [a, b, c])

        context = {}
        cache = {"a": Decimal("10"), "b": Decimal("25"), "c": Decimal("15")}
        result = node.evaluate(context, cache)

        assert result == Decimal("25")

    def test_evaluate_with_none_values(self):
        """Test l'évaluation avec des valeurs None (ignorées)."""
        a = ConstantNode("a", None)
        b = ConstantNode("b", Decimal("20"))
        c = ConstantNode("c", Decimal("15"))
        node = MaxNode("max_val", [a, b, c])

        context = {}
        cache = {"a": None, "b": Decimal("20"), "c": Decimal("15")}
        result = node.evaluate(context, cache)

        assert result == Decimal("20")

    def test_evaluate_all_none(self):
        """Test l'évaluation avec toutes les valeurs None."""
        a = ConstantNode("a", None)
        b = ConstantNode("b", None)
        node = MaxNode("max_val", [a, b])

        context = {}
        cache = {"a": None, "b": None}
        result = node.evaluate(context, cache)

        assert result is None

    def test_evaluate_negative_values(self):
        """Test l'évaluation avec des valeurs négatives."""
        a = ConstantNode("a", Decimal("-10"))
        b = ConstantNode("b", Decimal("5"))
        c = ConstantNode("c", Decimal("-20"))
        node = MaxNode("max_val", [a, b, c])

        context = {}
        cache = {"a": Decimal("-10"), "b": Decimal("5"), "c": Decimal("-20")}
        result = node.evaluate(context, cache)

        assert result == Decimal("5")


class TestAbsNode:
    """Tests pour AbsNode."""

    def test_init_valid(self):
        """Test l'initialisation d'un AbsNode valide."""
        input_node = ConstantNode("diff", Decimal("-50"))
        node = AbsNode("abs_diff", input_node)

        assert node.name == "abs_diff"
        assert node.input_node == input_node

    def test_init_no_input_node(self):
        """Test que l'initialisation échoue sans input_node."""
        with pytest.raises(ValueError, match="requires an input_node"):
            AbsNode("test", None)

    def test_dependencies(self):
        """Test que les dépendances sont correctement retournées."""
        input_node = ConstantNode("value", Decimal("-100"))
        node = AbsNode("abs_value", input_node)

        deps = node.dependencies()
        assert deps == ["value"]

    def test_evaluate_positive_value(self):
        """Test l'évaluation avec une valeur positive."""
        input_node = ConstantNode("value", Decimal("50"))
        node = AbsNode("abs_value", input_node)

        context = {}
        cache = {"value": Decimal("50")}
        result = node.evaluate(context, cache)

        assert result == Decimal("50")

    def test_evaluate_negative_value(self):
        """Test l'évaluation avec une valeur négative."""
        input_node = ConstantNode("value", Decimal("-50"))
        node = AbsNode("abs_value", input_node)

        context = {}
        cache = {"value": Decimal("-50")}
        result = node.evaluate(context, cache)

        assert result == Decimal("50")

    def test_evaluate_zero(self):
        """Test l'évaluation avec zéro."""
        input_node = ConstantNode("value", Decimal("0"))
        node = AbsNode("abs_value", input_node)

        context = {}
        cache = {"value": Decimal("0")}
        result = node.evaluate(context, cache)

        assert result == Decimal("0")

    def test_evaluate_none(self):
        """Test l'évaluation avec None."""
        input_node = ConstantNode("value", None)
        node = AbsNode("abs_value", input_node)

        context = {}
        cache = {"value": None}
        result = node.evaluate(context, cache)

        assert result is None

    def test_evaluate_decimal_precision(self):
        """Test que la précision décimale est préservée."""
        input_node = ConstantNode("value", Decimal("-123.456"))
        node = AbsNode("abs_value", input_node)

        context = {}
        cache = {"value": Decimal("-123.456")}
        result = node.evaluate(context, cache)

        assert result == Decimal("123.456")
