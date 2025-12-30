"""
Tests d'intégration end-to-end pour le rating engine.
Ces tests vérifient que tous les composants fonctionnent correctement ensemble.
"""

import csv
import tempfile
from decimal import Decimal
from pathlib import Path

import pytest

from engine.graph import TariffGraph
from engine.loader import TariffLoader
from engine.tables import load_exact_table, load_range_table


class TestEndToEndIntegration:
    """Tests end-to-end complets du rating engine."""

    @pytest.fixture
    def sample_tariff_yaml(self):
        """Crée un fichier tarif YAML simple pour les tests."""
        yaml_content = """
product: TEST_MOTOR
version: 2024_01
currency: EUR

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
  driver_factor:
    type: LOOKUP
    table: age_factor_table
    key_node: driver_age
  brand_factor:
    type: LOOKUP
    table: brand_factor_table
    key_node: brand
  density_factor:
    type: IF
    condition: density > 1000
    then: 1.2
    else: 1.0
  technical_premium:
    type: MULTIPLY
    inputs: [base_premium, driver_factor, brand_factor, density_factor]
  fee:
    type: CONSTANT
    value: 25
  raw_total:
    type: ADD
    inputs: [technical_premium, fee]
  total_premium:
    type: ROUND
    input: raw_total
    decimals: 2
    mode: HALF_UP
"""
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".yaml") as f:
            f.write(yaml_content)
            return f.name

    @pytest.fixture
    def age_factor_table_csv(self):
        """Crée une table CSV d'âge pour les tests."""
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".csv") as f:
            writer = csv.DictWriter(f, fieldnames=["min", "max", "value"])
            writer.writeheader()
            writer.writerow({"min": "18", "max": "25", "value": "1.8"})
            writer.writerow({"min": "26", "max": "65", "value": "1.0"})
            writer.writerow({"min": "66", "max": "99", "value": "1.3"})
            return f.name

    @pytest.fixture
    def brand_factor_table_csv(self):
        """Crée une table CSV de marques pour les tests."""
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".csv") as f:
            writer = csv.DictWriter(f, fieldnames=["key", "value"])
            writer.writeheader()
            writer.writerow({"key": "BMW", "value": "1.2"})
            writer.writerow({"key": "Audi", "value": "1.1"})
            writer.writerow({"key": "Toyota", "value": "0.9"})
            writer.writerow({"key": "__DEFAULT__", "value": "1.0"})
            return f.name

    @pytest.fixture
    def tables(self, age_factor_table_csv, brand_factor_table_csv):
        """Charge les tables pour les tests."""
        return {
            "age_factor_table": load_range_table(age_factor_table_csv),
            "brand_factor_table": load_exact_table(brand_factor_table_csv),
        }

    @pytest.fixture
    def cleanup(self, sample_tariff_yaml, age_factor_table_csv, brand_factor_table_csv):
        """Nettoie les fichiers temporaires après les tests."""
        yield
        Path(sample_tariff_yaml).unlink(missing_ok=True)
        Path(age_factor_table_csv).unlink(missing_ok=True)
        Path(brand_factor_table_csv).unlink(missing_ok=True)

    def test_full_pipeline_young_driver_premium_brand(self, sample_tariff_yaml, tables, cleanup):
        """Test complet: jeune conducteur, marque premium, haute densité."""
        loader = TariffLoader(tables=tables)
        nodes = loader.load(sample_tariff_yaml)
        graph = TariffGraph(nodes)

        context = {
            "driver_age": 22,
            "brand": "BMW",
            "density": 1500,
        }

        result = graph.evaluate("total_premium", context)

        # Calcul attendu:
        # base = 500
        # driver_factor = 1.8 (age 22 -> range 18-25)
        # brand_factor = 1.2 (BMW)
        # density_factor = 1.2 (density 1500 > 1000)
        # technical_premium = 500 * 1.8 * 1.2 * 1.2 = 1296
        # raw_total = 1296 + 25 = 1321
        # total_premium = 1321.00
        assert result == Decimal("1321.00")

    def test_full_pipeline_middle_aged_driver_economy_brand(
        self, sample_tariff_yaml, tables, cleanup
    ):
        """Test complet: conducteur d'âge moyen, marque économique, basse densité."""
        loader = TariffLoader(tables=tables)
        nodes = loader.load(sample_tariff_yaml)
        graph = TariffGraph(nodes)

        context = {
            "driver_age": 40,
            "brand": "Toyota",
            "density": 500,
        }

        result = graph.evaluate("total_premium", context)

        # Calcul attendu:
        # base = 500
        # driver_factor = 1.0 (age 40 -> range 26-65)
        # brand_factor = 0.9 (Toyota)
        # density_factor = 1.0 (density 500 <= 1000)
        # technical_premium = 500 * 1.0 * 0.9 * 1.0 = 450
        # raw_total = 450 + 25 = 475
        # total_premium = 475.00
        assert result == Decimal("475.00")

    def test_full_pipeline_senior_driver(self, sample_tariff_yaml, tables, cleanup):
        """Test complet: conducteur senior, marque par défaut."""
        loader = TariffLoader(tables=tables)
        nodes = loader.load(sample_tariff_yaml)
        graph = TariffGraph(nodes)

        context = {
            "driver_age": 70,
            "brand": "Mercedes",  # Not in table, uses default
            "density": 2000,
        }

        result = graph.evaluate("total_premium", context)

        # Calcul attendu:
        # base = 500
        # driver_factor = 1.3 (age 70 -> range 66-99)
        # brand_factor = 1.0 (Mercedes not in table, uses __DEFAULT__)
        # density_factor = 1.2 (density 2000 > 1000)
        # technical_premium = 500 * 1.3 * 1.0 * 1.2 = 780
        # raw_total = 780 + 25 = 805
        # total_premium = 805.00
        assert result == Decimal("805.00")

    def test_full_pipeline_with_trace(self, sample_tariff_yaml, tables, cleanup):
        """Test complet avec traçabilité complète."""
        loader = TariffLoader(tables=tables)
        nodes = loader.load(sample_tariff_yaml)
        graph = TariffGraph(nodes)

        context = {
            "driver_age": 30,
            "brand": "Audi",
            "density": 800,
        }

        trace = {}
        result = graph.evaluate("total_premium", context, trace=trace)

        # Vérifie que tous les nœuds sont dans la trace
        expected_nodes = [
            "driver_age",
            "brand",
            "density",
            "base_premium",
            "driver_factor",
            "brand_factor",
            "density_factor",
            "technical_premium",
            "fee",
            "raw_total",
            "total_premium",
        ]
        for node_name in expected_nodes:
            assert node_name in trace
            assert "value" in trace[node_name]
            assert "type" in trace[node_name]

        # Vérifie quelques valeurs clés
        assert trace["driver_age"]["value"] == Decimal("30")
        assert trace["brand"]["value"] == "Audi"
        assert trace["base_premium"]["value"] == Decimal("500")
        assert trace["driver_factor"]["value"] == Decimal("1.0")
        assert trace["brand_factor"]["value"] == Decimal("1.1")
        assert trace["density_factor"]["value"] == Decimal("1.0")
        assert trace["fee"]["value"] == Decimal("25")
        # Calcul: 500 * 1.0 * 1.1 * 1.0 + 25 = 550 + 25 = 575.00
        assert trace["total_premium"]["value"] == Decimal("575.00")

    def test_multiple_evaluations_with_different_contexts(
        self, sample_tariff_yaml, tables, cleanup
    ):
        """Test plusieurs évaluations avec différents contextes."""
        loader = TariffLoader(tables=tables)
        nodes = loader.load(sample_tariff_yaml)
        graph = TariffGraph(nodes)

        # Évaluation 1
        context1 = {"driver_age": 22, "brand": "BMW", "density": 1500}
        result1 = graph.evaluate("total_premium", context1)
        assert result1 == Decimal("1321.00")

        # Évaluation 2 (différente)
        context2 = {"driver_age": 40, "brand": "Toyota", "density": 500}
        result2 = graph.evaluate("total_premium", context2)
        assert result2 == Decimal("475.00")

        # Évaluation 3 (retour au contexte 1)
        result3 = graph.evaluate("total_premium", context1)
        assert result3 == Decimal("1321.00")

    def test_evaluation_intermediate_nodes(self, sample_tariff_yaml, tables, cleanup):
        """Test l'évaluation de nœuds intermédiaires."""
        loader = TariffLoader(tables=tables)
        nodes = loader.load(sample_tariff_yaml)
        graph = TariffGraph(nodes)

        context = {"driver_age": 30, "brand": "Audi", "density": 800}

        # Évalue uniquement la prime technique (sans frais)
        technical_premium = graph.evaluate("technical_premium", context)
        # 500 * 1.0 * 1.1 * 1.0 = 550
        assert technical_premium == Decimal("550")

        # Évalue le facteur de densité uniquement
        density_factor = graph.evaluate("density_factor", context)
        assert density_factor == Decimal("1.0")

    def test_boundary_conditions(self, sample_tariff_yaml, tables, cleanup):
        """Test les conditions limites."""
        loader = TariffLoader(tables=tables)
        nodes = loader.load(sample_tariff_yaml)
        graph = TariffGraph(nodes)

        # Âge limite inférieur (18 ans)
        context1 = {"driver_age": 18, "brand": "Toyota", "density": 500}
        result1 = graph.evaluate("total_premium", context1)
        # 500 * 1.8 * 0.9 * 1.0 + 25 = 835.00
        assert result1 == Decimal("835.00")

        # Âge limite supérieur (99 ans)
        context2 = {"driver_age": 99, "brand": "Toyota", "density": 500}
        result2 = graph.evaluate("total_premium", context2)
        # 500 * 1.3 * 0.9 * 1.0 + 25 = 610.00
        assert result2 == Decimal("610.00")

        # Densité exactement à la limite (1000)
        context3 = {"driver_age": 30, "brand": "Toyota", "density": 1000}
        result3 = graph.evaluate("total_premium", context3)
        # 500 * 1.0 * 0.9 * 1.0 + 25 = 475.00 (density_factor = 1.0)
        assert result3 == Decimal("475.00")

        # Densité juste au-dessus de la limite (1001)
        context4 = {"driver_age": 30, "brand": "Toyota", "density": 1001}
        result4 = graph.evaluate("total_premium", context4)
        # 500 * 1.0 * 0.9 * 1.2 + 25 = 565.00 (density_factor = 1.2)
        assert result4 == Decimal("565.00")

    def test_error_handling_missing_input(self, sample_tariff_yaml, tables, cleanup):
        """Test la gestion d'erreur pour input manquant."""
        from engine.validation import EvaluationError

        loader = TariffLoader(tables=tables)
        nodes = loader.load(sample_tariff_yaml)
        graph = TariffGraph(nodes)

        # Contexte incomplet (manque 'brand')
        context = {"driver_age": 30, "density": 800}

        with pytest.raises(EvaluationError, match="Missing input variable: brand"):
            graph.evaluate("total_premium", context)

    def test_error_handling_age_out_of_range(self, sample_tariff_yaml, tables, cleanup):
        """Test la gestion d'erreur pour âge hors plage."""
        from engine.validation import EvaluationError

        loader = TariffLoader(tables=tables)
        nodes = loader.load(sample_tariff_yaml)
        graph = TariffGraph(nodes)

        # Âge hors plage (17 ans, en dessous de 18)
        context = {"driver_age": 17, "brand": "BMW", "density": 500}

        with pytest.raises(EvaluationError, match="Value 17 outside all ranges"):
            graph.evaluate("total_premium", context)

    def test_decimal_precision_preserved(self, sample_tariff_yaml, tables, cleanup):
        """Test que la précision décimale est préservée."""
        loader = TariffLoader(tables=tables)
        nodes = loader.load(sample_tariff_yaml)
        graph = TariffGraph(nodes)

        context = {"driver_age": 30, "brand": "Audi", "density": 800}
        result = graph.evaluate("total_premium", context)

        # Vérifie que le résultat est un Decimal
        assert isinstance(result, Decimal)

        # Vérifie l'arrondi à 2 décimales
        assert result == result.quantize(Decimal("0.01"))

    def test_load_and_evaluate_without_modifications(self, sample_tariff_yaml, tables, cleanup):
        """Test que charger et évaluer plusieurs fois donne les mêmes résultats."""
        loader1 = TariffLoader(tables=tables)
        nodes1 = loader1.load(sample_tariff_yaml)
        graph1 = TariffGraph(nodes1)

        loader2 = TariffLoader(tables=tables)
        nodes2 = loader2.load(sample_tariff_yaml)
        graph2 = TariffGraph(nodes2)

        context = {"driver_age": 30, "brand": "BMW", "density": 1200}

        result1 = graph1.evaluate("total_premium", context)
        result2 = graph2.evaluate("total_premium", context)

        # Les deux graphes devraient donner le même résultat
        assert result1 == result2
