"""
Tests pour l'API REST FastAPI.

Tests pour tous les endpoints: health, metadata, evaluate, evaluate/batch.
"""

import pytest
from fastapi.testclient import TestClient

from api.main import _graph, _metadata, app, load_tariff_from_env


@pytest.fixture(scope="module")
def load_tariff():
    """Charge le tarif avant tous les tests."""
    import api.main as main_module

    main_module._graph, main_module._metadata = load_tariff_from_env()
    yield
    # Cleanup après les tests
    main_module._graph = None
    main_module._metadata = None


@pytest.fixture
def client(load_tariff):
    """Fixture pour créer un client de test FastAPI avec tarif chargé."""
    return TestClient(app)


class TestHealthEndpoint:
    """Tests pour l'endpoint /health."""

    def test_health_check_success(self, client):
        """Test que le health check retourne healthy quand le tarif est chargé."""
        response = client.get("/health")
        assert response.status_code == 200

        data = response.json()
        assert data["status"] == "healthy"
        assert data["tariff_loaded"] is True
        assert data["version"] == "0.1.0"
        assert data["tariff_info"] is not None
        assert data["tariff_info"]["product"] == "MOTOR_PRIVATE"
        assert data["tariff_info"]["version"] == 202409
        assert data["tariff_info"]["currency"] == "EUR"
        assert data["tariff_info"]["nodes_count"] == 15


class TestRootEndpoint:
    """Tests pour l'endpoint racine /."""

    def test_root_endpoint(self, client):
        """Test que l'endpoint racine retourne les infos de base."""
        response = client.get("/")
        assert response.status_code == 200

        data = response.json()
        assert data["message"] == "Rating Engine API"
        assert data["version"] == "0.1.0"
        assert data["docs"] == "/docs"
        assert data["health"] == "/health"


class TestMetadataEndpoint:
    """Tests pour l'endpoint /metadata."""

    def test_get_metadata(self, client):
        """Test que l'endpoint metadata retourne les métadonnées du tarif."""
        response = client.get("/metadata")
        assert response.status_code == 200

        data = response.json()
        assert data["product"] == "MOTOR_PRIVATE"
        assert data["version"] == 202409
        assert data["currency"] == "EUR"
        # Check that at least the core fields are present
        assert isinstance(data, dict)
        assert len(data) >= 3


class TestEvaluateEndpoint:
    """Tests pour l'endpoint POST /evaluate."""

    def test_evaluate_simple_context(self, client):
        """Test évaluation avec un contexte simple et valide."""
        request_data = {
            "context": {
                "driver_age": 35,
                "brand": "BMW",
                "density": 1200,
                "neighbourhood_id": 19582,
            },
            "target_node": "total_premium",
            "include_trace": False,
        }

        response = client.post("/evaluate", json=request_data)
        assert response.status_code == 200

        data = response.json()
        assert data["result"] == "429.18"
        assert data["target_node"] == "total_premium"
        assert data["context"] == request_data["context"]
        assert data["trace"] is None
        assert data["metadata"] is not None

    def test_evaluate_with_trace(self, client):
        """Test évaluation avec trace activée."""
        request_data = {
            "context": {
                "driver_age": 35,
                "brand": "BMW",
                "density": 1200,
                "neighbourhood_id": 19582,
            },
            "target_node": "total_premium",
            "include_trace": True,
        }

        response = client.post("/evaluate", json=request_data)
        assert response.status_code == 200

        data = response.json()
        assert data["result"] == "429.18"
        assert data["trace"] is not None
        assert "total_premium" in data["trace"]
        assert "value" in data["trace"]["total_premium"]

    def test_evaluate_missing_input(self, client):
        """Test évaluation avec une variable d'entrée manquante."""
        request_data = {
            "context": {"driver_age": 35, "brand": "BMW"},  # Manque density et neighbourhood_id
            "target_node": "total_premium",
            "include_trace": False,
        }

        response = client.post("/evaluate", json=request_data)
        assert response.status_code == 400
        # The error message contains information about the missing input
        assert "density" in response.json()["detail"]

    def test_evaluate_invalid_target_node(self, client):
        """Test évaluation avec un nœud cible invalide."""
        request_data = {
            "context": {
                "driver_age": 35,
                "brand": "BMW",
                "density": 1200,
                "neighbourhood_id": 19582,
            },
            "target_node": "nonexistent_node",
            "include_trace": False,
        }

        response = client.post("/evaluate", json=request_data)
        assert response.status_code == 400

    def test_evaluate_young_driver(self, client):
        """Test tarif pour jeune conducteur (22 ans)."""
        request_data = {
            "context": {
                "driver_age": 22,
                "brand": "Renault",
                "density": 800,
                "neighbourhood_id": 19582,
            },
            "target_node": "total_premium",
            "include_trace": False,
        }

        response = client.post("/evaluate", json=request_data)
        assert response.status_code == 200

        data = response.json()
        # Jeune conducteur = facteur plus élevé, donc prime plus chère
        result = float(data["result"])
        assert result > 300  # Should be higher than base

    def test_evaluate_senior_driver(self, client):
        """Test tarif pour conducteur senior (70 ans)."""
        request_data = {
            "context": {
                "driver_age": 70,
                "brand": "Toyota",
                "density": 1000,
                "neighbourhood_id": 19582,
            },
            "target_node": "total_premium",
            "include_trace": False,
        }

        response = client.post("/evaluate", json=request_data)
        assert response.status_code == 200

        data = response.json()
        result = float(data["result"])
        assert result > 0


class TestBatchEvaluateEndpoint:
    """Tests pour l'endpoint POST /evaluate/batch."""

    def test_batch_evaluate_success(self, client):
        """Test évaluation batch avec plusieurs contextes valides."""
        request_data = {
            "contexts": [
                {"driver_age": 22, "brand": "Renault", "density": 800, "neighbourhood_id": 19582},
                {"driver_age": 35, "brand": "BMW", "density": 1200, "neighbourhood_id": 19582},
                {"driver_age": 70, "brand": "Audi", "density": 1500, "neighbourhood_id": 19582},
            ],
            "target_node": "total_premium",
            "collect_errors": True,
        }

        response = client.post("/evaluate/batch", json=request_data)
        assert response.status_code == 200

        data = response.json()
        assert data["total_count"] == 3
        assert data["success_count"] == 3
        assert data["error_count"] == 0
        assert len(data["results"]) == 3

        # Vérifier que tous les résultats ont une valeur
        for result in data["results"]:
            assert result["result"] is not None
            assert result["error"] is None
            assert "row_index" in result
            assert "context" in result

    def test_batch_evaluate_with_errors(self, client):
        """Test évaluation batch avec des erreurs."""
        request_data = {
            "contexts": [
                {"driver_age": 35, "brand": "BMW", "density": 1200, "neighbourhood_id": 19582},
                {"driver_age": 35, "brand": "BMW"},  # Manque density et neighbourhood_id
                {"driver_age": 22, "brand": "Renault", "density": 800, "neighbourhood_id": 19582},
            ],
            "target_node": "total_premium",
            "collect_errors": True,
        }

        response = client.post("/evaluate/batch", json=request_data)
        assert response.status_code == 200

        data = response.json()
        assert data["total_count"] == 3
        assert data["success_count"] == 2
        assert data["error_count"] == 1

        # Vérifier que le résultat avec erreur a bien un message d'erreur
        results = data["results"]
        assert results[0]["result"] is not None
        assert results[0]["error"] is None
        assert results[1]["result"] is None
        assert results[1]["error"] is not None
        assert results[2]["result"] is not None
        assert results[2]["error"] is None

    def test_batch_evaluate_empty_contexts(self, client):
        """Test évaluation batch avec liste vide de contextes."""
        request_data = {
            "contexts": [],
            "target_node": "total_premium",
            "collect_errors": True,
        }

        response = client.post("/evaluate/batch", json=request_data)
        assert response.status_code == 422  # Validation error (min_length=1)

    def test_batch_evaluate_single_context(self, client):
        """Test évaluation batch avec un seul contexte."""
        request_data = {
            "contexts": [
                {"driver_age": 35, "brand": "BMW", "density": 1200, "neighbourhood_id": 19582}
            ],
            "target_node": "total_premium",
            "collect_errors": False,
        }

        response = client.post("/evaluate/batch", json=request_data)
        assert response.status_code == 200

        data = response.json()
        assert data["total_count"] == 1
        assert data["success_count"] == 1
        assert data["error_count"] == 0


class TestAPIDocumentation:
    """Tests pour la documentation OpenAPI."""

    def test_openapi_json_available(self, client):
        """Test que le schéma OpenAPI est disponible."""
        response = client.get("/openapi.json")
        assert response.status_code == 200

        data = response.json()
        assert "openapi" in data
        assert "info" in data
        assert data["info"]["title"] == "Rating Engine API"
        assert data["info"]["version"] == "0.1.0"

    def test_docs_redirect(self, client):
        """Test que /docs est accessible."""
        response = client.get("/docs", follow_redirects=False)
        assert response.status_code in [200, 307]  # 200 si direct, 307 si redirect

    def test_redoc_redirect(self, client):
        """Test que /redoc est accessible."""
        response = client.get("/redoc", follow_redirects=False)
        assert response.status_code in [200, 307]


class TestErrorHandling:
    """Tests pour la gestion d'erreurs."""

    def test_invalid_json(self, client):
        """Test avec un JSON invalide."""
        response = client.post(
            "/evaluate", data="invalid json", headers={"Content-Type": "application/json"}
        )
        assert response.status_code == 422  # Unprocessable Entity

    def test_missing_required_field(self, client):
        """Test avec un champ requis manquant."""
        request_data = {
            "target_node": "total_premium",
            # Manque le champ 'context'
        }

        response = client.post("/evaluate", json=request_data)
        assert response.status_code == 422

    def test_invalid_data_type(self, client):
        """Test avec un type de données invalide."""
        request_data = {
            "context": "not a dict",  # Devrait être un dict
            "target_node": "total_premium",
        }

        response = client.post("/evaluate", json=request_data)
        assert response.status_code == 422


class TestCORS:
    """Tests pour la configuration CORS."""

    def test_cors_headers_present(self, client):
        """Test que les headers CORS sont présents."""
        response = client.options(
            "/evaluate",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "POST",
            },
        )

        # Vérifier que les headers CORS sont présents
        assert "access-control-allow-origin" in response.headers
