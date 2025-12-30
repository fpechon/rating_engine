"""
Tests pour le module metadata (métadonnées et export).
"""

import pytest
import json
import csv
from pathlib import Path
from decimal import Decimal
from engine.metadata import (
    TariffMetadata,
    export_trace_to_json,
    export_trace_to_csv,
    export_batch_results,
    load_metadata_from_file,
)


class TestTariffMetadata:
    """Tests pour la classe TariffMetadata."""

    def test_init_minimal(self):
        """Test initialisation avec champs obligatoires uniquement."""
        metadata = TariffMetadata(
            product="MOTOR",
            version="2024_09",
            currency="EUR"
        )

        assert metadata.product == "MOTOR"
        assert metadata.version == "2024_09"
        assert metadata.currency == "EUR"
        assert metadata.effective_date is None
        assert metadata.author is None

    def test_init_complete(self):
        """Test initialisation avec tous les champs."""
        metadata = TariffMetadata(
            product="MOTOR",
            version="2024_09",
            currency="EUR",
            effective_date="2024-09-01",
            author="John Doe",
            description="Test tariff",
            changelog=[{"version": "2024_08", "changes": "Initial"}]
        )

        assert metadata.effective_date == "2024-09-01"
        assert metadata.author == "John Doe"
        assert metadata.description == "Test tariff"
        assert len(metadata.changelog) == 1

    def test_init_with_custom_fields(self):
        """Test avec métadonnées custom."""
        metadata = TariffMetadata(
            product="MOTOR",
            version="2024_09",
            currency="EUR",
            custom_field="custom_value",
            another_field=123
        )

        assert metadata.custom["custom_field"] == "custom_value"
        assert metadata.custom["another_field"] == 123

    def test_from_yaml_data_minimal(self):
        """Test création depuis YAML minimal."""
        data = {
            "product": "MOTOR",
            "version": "2024_09",
            "currency": "EUR",
            "nodes": {}
        }

        metadata = TariffMetadata.from_yaml_data(data)

        assert metadata.product == "MOTOR"
        assert metadata.version == "2024_09"
        assert metadata.currency == "EUR"

    def test_from_yaml_data_with_metadata(self):
        """Test création depuis YAML avec section metadata."""
        data = {
            "product": "MOTOR",
            "version": "2024_09",
            "currency": "EUR",
            "metadata": {
                "effective_date": "2024-09-01",
                "author": "John Doe",
                "description": "Test tariff"
            },
            "nodes": {}
        }

        metadata = TariffMetadata.from_yaml_data(data)

        assert metadata.effective_date == "2024-09-01"
        assert metadata.author == "John Doe"
        assert metadata.description == "Test tariff"

    def test_from_yaml_data_missing_product(self):
        """Test erreur si product manquant."""
        data = {"version": "2024_09", "currency": "EUR"}

        with pytest.raises(ValueError, match="must contain 'product'"):
            TariffMetadata.from_yaml_data(data)

    def test_from_yaml_data_missing_version(self):
        """Test erreur si version manquante."""
        data = {"product": "MOTOR", "currency": "EUR"}

        with pytest.raises(ValueError, match="must contain 'version'"):
            TariffMetadata.from_yaml_data(data)

    def test_from_yaml_data_missing_currency(self):
        """Test erreur si currency manquante."""
        data = {"product": "MOTOR", "version": "2024_09"}

        with pytest.raises(ValueError, match="must contain 'currency'"):
            TariffMetadata.from_yaml_data(data)

    def test_to_dict_minimal(self):
        """Test conversion en dict (minimal)."""
        metadata = TariffMetadata(
            product="MOTOR",
            version="2024_09",
            currency="EUR"
        )

        result = metadata.to_dict()

        assert result["product"] == "MOTOR"
        assert result["version"] == "2024_09"
        assert result["currency"] == "EUR"
        assert "effective_date" not in result

    def test_to_dict_complete(self):
        """Test conversion en dict (complet)."""
        metadata = TariffMetadata(
            product="MOTOR",
            version="2024_09",
            currency="EUR",
            effective_date="2024-09-01",
            author="John Doe"
        )

        result = metadata.to_dict()

        assert result["effective_date"] == "2024-09-01"
        assert result["author"] == "John Doe"


class TestExportTraceToJSON:
    """Tests pour export_trace_to_json."""

    def test_export_simple_trace(self, tmp_path):
        """Test export d'une trace simple."""
        trace = {
            "a": {"value": Decimal("100"), "type": "ConstantNode", "path": ["a"]},
            "b": {"value": Decimal("200"), "type": "ConstantNode", "path": ["b"]},
            "sum": {"value": Decimal("300"), "type": "AddNode", "path": ["sum"]},
        }

        output_file = tmp_path / "trace.json"
        export_trace_to_json(trace, str(output_file))

        # Vérifier que le fichier existe et est valide JSON
        assert output_file.exists()

        with open(output_file) as f:
            data = json.load(f)

        assert "timestamp" in data
        assert "trace" in data
        assert len(data["trace"]) == 3
        assert data["trace"]["a"]["value"] == 100.0
        assert data["trace"]["sum"]["value"] == 300.0

    def test_export_with_metadata(self, tmp_path):
        """Test export avec métadonnées."""
        trace = {"a": {"value": Decimal("100"), "type": "ConstantNode", "path": ["a"]}}
        metadata = TariffMetadata(
            product="MOTOR",
            version="2024_09",
            currency="EUR"
        )

        output_file = tmp_path / "trace.json"
        export_trace_to_json(trace, str(output_file), metadata=metadata)

        with open(output_file) as f:
            data = json.load(f)

        assert "metadata" in data
        assert data["metadata"]["product"] == "MOTOR"
        assert data["metadata"]["version"] == "2024_09"

    def test_export_with_context(self, tmp_path):
        """Test export avec contexte."""
        trace = {"a": {"value": Decimal("100"), "type": "ConstantNode", "path": ["a"]}}
        context = {"age": 30, "brand": "BMW"}

        output_file = tmp_path / "trace.json"
        export_trace_to_json(trace, str(output_file), context=context)

        with open(output_file) as f:
            data = json.load(f)

        assert "context" in data
        assert data["context"]["age"] == 30
        assert data["context"]["brand"] == "BMW"

    def test_export_not_pretty(self, tmp_path):
        """Test export compact (pas indenté)."""
        trace = {"a": {"value": Decimal("100"), "type": "ConstantNode", "path": ["a"]}}

        output_file = tmp_path / "trace.json"
        export_trace_to_json(trace, str(output_file), pretty=False)

        # Vérifier que c'est une seule ligne (pas indenté)
        with open(output_file) as f:
            content = f.read()
            assert "\n " not in content  # Pas d'indentation


class TestExportTraceToCSV:
    """Tests pour export_trace_to_csv."""

    def test_export_simple_trace(self, tmp_path):
        """Test export CSV d'une trace simple."""
        trace = {
            "a": {"value": Decimal("100"), "type": "ConstantNode", "path": ["a"]},
            "b": {"value": Decimal("200"), "type": "ConstantNode", "path": ["b"]},
            "sum": {"value": Decimal("300"), "type": "AddNode", "path": ["a", "sum"]},
        }

        output_file = tmp_path / "trace.csv"
        export_trace_to_csv(trace, str(output_file))

        # Vérifier le fichier CSV
        assert output_file.exists()

        with open(output_file, newline='') as f:
            reader = csv.DictReader(f)
            rows = list(reader)

        assert len(rows) == 3
        assert rows[0]["node_name"] == "a"
        assert rows[0]["value"] == "100"
        assert rows[2]["node_name"] == "sum"
        assert rows[2]["path"] == "a -> sum"

    def test_export_with_context(self, tmp_path):
        """Test export CSV avec contexte."""
        trace = {"a": {"value": Decimal("100"), "type": "ConstantNode", "path": ["a"]}}
        context = {"age": 30, "brand": "BMW"}

        output_file = tmp_path / "trace.csv"
        export_trace_to_csv(trace, str(output_file), context=context)

        with open(output_file, newline='') as f:
            reader = csv.DictReader(f)
            rows = list(reader)

        # Vérifier que les colonnes de contexte sont présentes
        assert "context_age" in rows[0]
        assert "context_brand" in rows[0]
        assert rows[0]["context_age"] == "30"
        assert rows[0]["context_brand"] == "BMW"


class TestExportBatchResults:
    """Tests pour export_batch_results."""

    def test_export_simple_batch(self, tmp_path):
        """Test export de résultats batch simples."""
        results = [Decimal("100"), Decimal("200"), Decimal("300")]
        contexts = [{"age": 20}, {"age": 40}, {"age": 60}]

        output_file = tmp_path / "batch.csv"
        export_batch_results(results, contexts, str(output_file))

        # Vérifier le fichier CSV
        with open(output_file, newline='') as f:
            reader = csv.DictReader(f)
            rows = list(reader)

        assert len(rows) == 3
        assert rows[0]["row_index"] == "0"
        assert rows[0]["result"] == "100"
        assert rows[0]["age"] == "20"
        assert rows[2]["result"] == "300"
        assert rows[2]["age"] == "60"

    def test_export_batch_with_errors(self, tmp_path):
        """Test export batch avec erreurs."""
        results = [Decimal("100"), None, Decimal("300")]
        contexts = [{"age": 20}, {"age": 40}, {"age": 60}]
        errors = [None, ValueError("Invalid age"), None]

        output_file = tmp_path / "batch.csv"
        export_batch_results(results, contexts, str(output_file), errors=errors)

        with open(output_file, newline='') as f:
            reader = csv.DictReader(f)
            rows = list(reader)

        assert rows[0]["error"] == ""
        assert "Invalid age" in rows[1]["error"]
        assert rows[1]["result"] == ""
        assert rows[2]["error"] == ""

    def test_export_batch_multiple_context_keys(self, tmp_path):
        """Test export batch avec plusieurs clés de contexte."""
        results = [Decimal("100"), Decimal("200")]
        contexts = [
            {"age": 20, "brand": "BMW", "density": 1000},
            {"age": 40, "brand": "Audi", "density": 500},
        ]

        output_file = tmp_path / "batch.csv"
        export_batch_results(results, contexts, str(output_file))

        with open(output_file, newline='') as f:
            reader = csv.DictReader(f)
            rows = list(reader)

        # Vérifier que toutes les colonnes sont présentes
        assert "age" in rows[0]
        assert "brand" in rows[0]
        assert "density" in rows[0]
        assert rows[0]["brand"] == "BMW"
        assert rows[1]["brand"] == "Audi"

    def test_export_batch_mismatched_lengths(self, tmp_path):
        """Test erreur si longueurs différentes."""
        results = [Decimal("100")]
        contexts = [{"age": 20}, {"age": 40}]  # Longueur différente

        output_file = tmp_path / "batch.csv"

        with pytest.raises(ValueError, match="same length"):
            export_batch_results(results, contexts, str(output_file))
