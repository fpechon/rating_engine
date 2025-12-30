"""
Tests pour la méthode load_with_tables() du TariffLoader.

Ces tests vérifient que les tarifs peuvent être chargés automatiquement
avec leurs tables déclarées dans le YAML.
"""

from decimal import Decimal
from pathlib import Path

import pytest

from engine.graph import TariffGraph
from engine.loader import TariffLoader


class TestLoadWithTables:
    """Tests pour load_with_tables()."""

    @pytest.fixture
    def test_tariff_path(self):
        """Chemin vers le tarif de test."""
        return str(Path(__file__).parent / "fixtures" / "test_tariff_with_tables.yaml")

    def test_load_with_tables_success(self, test_tariff_path):
        """Test que load_with_tables() charge correctement un tarif."""
        loader = TariffLoader()
        nodes, tables_loaded = loader.load_with_tables(test_tariff_path)

        # Vérifier que les nœuds sont chargés
        assert len(nodes) == 6  # age, brand, base, age_factor, brand_factor, premium
        assert "age" in nodes
        assert "brand" in nodes
        assert "premium" in nodes

        # Vérifier que les tables sont chargées
        assert len(tables_loaded) == 2
        assert "age_factors (range)" in tables_loaded
        assert "brand_categories (exact)" in tables_loaded

        # Vérifier que les tables sont dans le loader
        assert "age_factors" in loader.tables
        assert "brand_categories" in loader.tables

    def test_load_with_tables_and_evaluate(self, test_tariff_path):
        """Test qu'on peut évaluer un tarif chargé avec load_with_tables()."""
        loader = TariffLoader()
        nodes, _ = loader.load_with_tables(test_tariff_path)
        graph = TariffGraph(nodes)

        # Évaluer pour un jeune conducteur avec BMW
        context = {"age": 22, "brand": "BMW"}
        result = graph.evaluate("premium", context)

        # 100 * 1.5 (age_factor) * 1.2 (brand_factor) = 180
        assert result == Decimal("180")

    def test_load_with_tables_senior_driver(self, test_tariff_path):
        """Test pour un conducteur senior."""
        loader = TariffLoader()
        nodes, _ = loader.load_with_tables(test_tariff_path)
        graph = TariffGraph(nodes)

        # Conducteur senior avec Toyota
        context = {"age": 70, "brand": "Toyota"}
        result = graph.evaluate("premium", context)

        # 100 * 1.3 (age_factor) * 1.0 (brand_factor) = 130
        assert result == Decimal("130")

    def test_load_with_tables_motor_tariff(self):
        """Test avec le tarif motor réel."""
        project_root = Path(__file__).parent.parent
        tariff_path = project_root / "tariffs/motor_private/2024_09/tariff.yaml"

        if not tariff_path.exists():
            pytest.skip("Motor tariff not found")

        loader = TariffLoader()
        nodes, tables_loaded = loader.load_with_tables(str(tariff_path))

        # Vérifier le chargement
        assert len(nodes) == 15
        assert len(tables_loaded) == 5

        # Vérifier qu'on peut évaluer
        graph = TariffGraph(nodes)
        context = {
            "driver_age": 35,
            "brand": "BMW",
            "density": 1200,
            "neighbourhood_id": "19582",
        }
        result = graph.evaluate("total_premium", context)
        assert result == Decimal("429.18")

    def test_load_with_tables_missing_table_file(self, tmp_path):
        """Test qu'une erreur est levée si un fichier table est manquant."""
        # Créer un tarif avec une table manquante
        tariff_path = tmp_path / "tariff.yaml"
        tariff_path.write_text(
            """
product: TEST
version: 1.0
currency: EUR

tables:
  missing_table:
    type: range
    source: missing.csv

nodes:
  age:
    type: INPUT
    dtype: decimal

  factor:
    type: LOOKUP
    table: missing_table
    key_node: age
    mode: range
"""
        )

        loader = TariffLoader()
        with pytest.raises(FileNotFoundError, match="Table file not found"):
            loader.load_with_tables(str(tariff_path))

    def test_load_with_tables_invalid_type(self, tmp_path):
        """Test qu'une erreur est levée si le type de table est invalide."""
        # Créer d'abord le fichier CSV
        csv_path = tmp_path / "test.csv"
        csv_path.write_text("key,value\ntest,1\n")

        tariff_path = tmp_path / "tariff.yaml"
        tariff_path.write_text(
            """
product: TEST
version: 1.0
currency: EUR

tables:
  bad_table:
    type: invalid_type
    source: test.csv

nodes:
  age:
    type: INPUT
    dtype: decimal
"""
        )

        loader = TariffLoader()
        with pytest.raises(ValueError, match="invalid type"):
            loader.load_with_tables(str(tariff_path))

    def test_load_with_tables_no_tables_section(self, tmp_path):
        """Test qu'on peut charger un tarif sans section tables."""
        # Créer un tarif simple sans tables
        tariff_path = tmp_path / "tariff.yaml"
        tariff_path.write_text(
            """
product: SIMPLE
version: 1.0
currency: EUR

nodes:
  age:
    type: INPUT
    dtype: decimal

  premium:
    type: CONSTANT
    value: 100
"""
        )

        loader = TariffLoader()
        nodes, tables_loaded = loader.load_with_tables(str(tariff_path))

        assert len(nodes) == 2
        assert len(tables_loaded) == 0
        assert len(loader.tables) == 0
