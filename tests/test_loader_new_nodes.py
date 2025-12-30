"""
Tests pour le chargement YAML des nouveaux nœuds (Phase 2).

Ce module teste l'intégration des nouveaux nœuds dans le TariffLoader.
"""

import pytest
import tempfile
import os
from decimal import Decimal
from engine.loader import TariffLoader
from engine.graph import TariffGraph


class TestLoaderSwitchNode:
    """Tests du loader pour SwitchNode."""

    def test_load_switch_node_with_default(self):
        """Test le chargement d'un SWITCH avec default."""
        yaml_content = """
nodes:
  region:
    type: INPUT
    dtype: str
  region_factor:
    type: SWITCH
    var_node: region
    cases:
      Paris: 1.5
      Lyon: 1.3
      Marseille: 1.2
    default: 1.0
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write(yaml_content)
            temp_path = f.name

        try:
            loader = TariffLoader()
            nodes = loader.load(temp_path)

            assert "region_factor" in nodes
            assert nodes["region_factor"].name == "region_factor"
            assert nodes["region_factor"].default == Decimal("1.0")
            assert len(nodes["region_factor"].cases) == 3
        finally:
            os.unlink(temp_path)

    def test_load_switch_node_without_default(self):
        """Test le chargement d'un SWITCH sans default."""
        yaml_content = """
nodes:
  status:
    type: INPUT
    dtype: str
  status_factor:
    type: SWITCH
    var_node: status
    cases:
      active: 1.0
      inactive: 0.0
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write(yaml_content)
            temp_path = f.name

        try:
            loader = TariffLoader()
            nodes = loader.load(temp_path)

            assert "status_factor" in nodes
            assert nodes["status_factor"].default is None
        finally:
            os.unlink(temp_path)

    def test_validate_switch_missing_var_node(self):
        """Test la validation échoue si var_node manque."""
        yaml_content = """
nodes:
  region_factor:
    type: SWITCH
    cases:
      Paris: 1.5
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write(yaml_content)
            temp_path = f.name

        try:
            loader = TariffLoader()
            with pytest.raises(ValueError, match="missing 'var_node'"):
                loader.load(temp_path)
        finally:
            os.unlink(temp_path)

    def test_validate_switch_missing_cases(self):
        """Test la validation échoue si cases manque."""
        yaml_content = """
nodes:
  region:
    type: INPUT
    dtype: str
  region_factor:
    type: SWITCH
    var_node: region
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write(yaml_content)
            temp_path = f.name

        try:
            loader = TariffLoader()
            with pytest.raises(ValueError, match="missing 'cases'"):
                loader.load(temp_path)
        finally:
            os.unlink(temp_path)

    def test_validate_switch_empty_cases(self):
        """Test la validation échoue si cases est vide."""
        yaml_content = """
nodes:
  region:
    type: INPUT
    dtype: str
  region_factor:
    type: SWITCH
    var_node: region
    cases: {}
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write(yaml_content)
            temp_path = f.name

        try:
            loader = TariffLoader()
            with pytest.raises(ValueError, match="non-empty 'cases' dict"):
                loader.load(temp_path)
        finally:
            os.unlink(temp_path)


class TestLoaderCoalesceNode:
    """Tests du loader pour CoalesceNode."""

    def test_load_coalesce_node(self):
        """Test le chargement d'un COALESCE."""
        yaml_content = """
nodes:
  discount:
    type: INPUT
  default_discount:
    type: CONSTANT
    value: 0
  final_discount:
    type: COALESCE
    inputs: [discount, default_discount]
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write(yaml_content)
            temp_path = f.name

        try:
            loader = TariffLoader()
            nodes = loader.load(temp_path)

            assert "final_discount" in nodes
            assert len(nodes["final_discount"].inputs) == 2
        finally:
            os.unlink(temp_path)

    def test_validate_coalesce_missing_inputs(self):
        """Test la validation échoue si inputs manque."""
        yaml_content = """
nodes:
  final_discount:
    type: COALESCE
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write(yaml_content)
            temp_path = f.name

        try:
            loader = TariffLoader()
            with pytest.raises(ValueError, match="non-empty 'inputs' list"):
                loader.load(temp_path)
        finally:
            os.unlink(temp_path)

    def test_validate_coalesce_empty_inputs(self):
        """Test la validation échoue si inputs est vide."""
        yaml_content = """
nodes:
  final_discount:
    type: COALESCE
    inputs: []
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write(yaml_content)
            temp_path = f.name

        try:
            loader = TariffLoader()
            with pytest.raises(ValueError, match="non-empty 'inputs' list"):
                loader.load(temp_path)
        finally:
            os.unlink(temp_path)


class TestLoaderMinMaxNodes:
    """Tests du loader pour MinNode et MaxNode."""

    def test_load_min_node(self):
        """Test le chargement d'un MIN."""
        yaml_content = """
nodes:
  price1:
    type: CONSTANT
    value: 500
  price2:
    type: CONSTANT
    value: 450
  best_price:
    type: MIN
    inputs: [price1, price2]
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write(yaml_content)
            temp_path = f.name

        try:
            loader = TariffLoader()
            nodes = loader.load(temp_path)

            assert "best_price" in nodes
            assert len(nodes["best_price"].inputs) == 2
        finally:
            os.unlink(temp_path)

    def test_load_max_node(self):
        """Test le chargement d'un MAX."""
        yaml_content = """
nodes:
  deductible1:
    type: CONSTANT
    value: 100
  deductible2:
    type: CONSTANT
    value: 200
  final_deductible:
    type: MAX
    inputs: [deductible1, deductible2]
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write(yaml_content)
            temp_path = f.name

        try:
            loader = TariffLoader()
            nodes = loader.load(temp_path)

            assert "final_deductible" in nodes
            assert len(nodes["final_deductible"].inputs) == 2
        finally:
            os.unlink(temp_path)

    def test_validate_min_missing_inputs(self):
        """Test la validation échoue si inputs manque pour MIN."""
        yaml_content = """
nodes:
  best_price:
    type: MIN
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write(yaml_content)
            temp_path = f.name

        try:
            loader = TariffLoader()
            with pytest.raises(ValueError, match="non-empty 'inputs' list"):
                loader.load(temp_path)
        finally:
            os.unlink(temp_path)

    def test_validate_max_empty_inputs(self):
        """Test la validation échoue si inputs est vide pour MAX."""
        yaml_content = """
nodes:
  max_val:
    type: MAX
    inputs: []
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write(yaml_content)
            temp_path = f.name

        try:
            loader = TariffLoader()
            with pytest.raises(ValueError, match="non-empty 'inputs' list"):
                loader.load(temp_path)
        finally:
            os.unlink(temp_path)


class TestLoaderAbsNode:
    """Tests du loader pour AbsNode."""

    def test_load_abs_node(self):
        """Test le chargement d'un ABS."""
        yaml_content = """
nodes:
  diff:
    type: CONSTANT
    value: -50
  abs_diff:
    type: ABS
    input: diff
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write(yaml_content)
            temp_path = f.name

        try:
            loader = TariffLoader()
            nodes = loader.load(temp_path)

            assert "abs_diff" in nodes
            assert nodes["abs_diff"].input_node.name == "diff"
        finally:
            os.unlink(temp_path)

    def test_validate_abs_missing_input(self):
        """Test la validation échoue si input manque."""
        yaml_content = """
nodes:
  abs_diff:
    type: ABS
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write(yaml_content)
            temp_path = f.name

        try:
            loader = TariffLoader()
            with pytest.raises(ValueError, match="missing 'input'"):
                loader.load(temp_path)
        finally:
            os.unlink(temp_path)


class TestNewNodesIntegration:
    """Tests d'intégration des nouveaux nœuds dans un graphe complet."""

    def test_switch_node_in_graph(self):
        """Test l'utilisation d'un SWITCH dans un graphe complet."""
        yaml_content = """
nodes:
  region:
    type: INPUT
    dtype: str
  base_premium:
    type: CONSTANT
    value: 500
  region_factor:
    type: SWITCH
    var_node: region
    cases:
      Paris: 1.5
      Lyon: 1.3
    default: 1.0
  premium:
    type: MULTIPLY
    inputs: [base_premium, region_factor]
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write(yaml_content)
            temp_path = f.name

        try:
            loader = TariffLoader()
            nodes = loader.load(temp_path)
            graph = TariffGraph(nodes)

            # Test avec Paris
            result = graph.evaluate("premium", {"region": "Paris"})
            assert result == Decimal("750")  # 500 * 1.5

            # Test avec Lyon
            result = graph.evaluate("premium", {"region": "Lyon"})
            assert result == Decimal("650")  # 500 * 1.3

            # Test avec région inconnue (default)
            result = graph.evaluate("premium", {"region": "Marseille"})
            assert result == Decimal("500")  # 500 * 1.0
        finally:
            os.unlink(temp_path)

    def test_min_max_in_graph(self):
        """Test l'utilisation de MIN et MAX dans un graphe."""
        yaml_content = """
nodes:
  base1:
    type: CONSTANT
    value: 100
  base2:
    type: CONSTANT
    value: 150
  base3:
    type: CONSTANT
    value: 120
  min_premium:
    type: MIN
    inputs: [base1, base2, base3]
  max_premium:
    type: MAX
    inputs: [base1, base2, base3]
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write(yaml_content)
            temp_path = f.name

        try:
            loader = TariffLoader()
            nodes = loader.load(temp_path)
            graph = TariffGraph(nodes)

            min_result = graph.evaluate("min_premium", {})
            assert min_result == Decimal("100")

            max_result = graph.evaluate("max_premium", {})
            assert max_result == Decimal("150")
        finally:
            os.unlink(temp_path)

    def test_abs_in_graph(self):
        """Test l'utilisation d'ABS dans un graphe."""
        yaml_content = """
nodes:
  adjustment:
    type: INPUT
  abs_adjustment:
    type: ABS
    input: adjustment
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write(yaml_content)
            temp_path = f.name

        try:
            loader = TariffLoader()
            nodes = loader.load(temp_path)
            graph = TariffGraph(nodes)

            # Test avec valeur négative
            result = graph.evaluate("abs_adjustment", {"adjustment": -25})
            assert result == Decimal("25")

            # Test avec valeur positive
            result = graph.evaluate("abs_adjustment", {"adjustment": 30})
            assert result == Decimal("30")
        finally:
            os.unlink(temp_path)
