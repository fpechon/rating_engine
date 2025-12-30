"""
Exemple d'utilisation du client API REST pour le Rating Engine.

Ce script démontre comment utiliser l'API pour:
1. Vérifier l'état de santé
2. Récupérer les métadonnées du tarif
3. Évaluer un tarif simple
4. Évaluer un tarif avec trace
5. Évaluer en batch
"""

import json

import httpx

# Configuration
API_BASE_URL = "http://localhost:8000"


def print_section(title: str):
    """Affiche un titre de section."""
    print("\n" + "=" * 80)
    print(f"  {title}")
    print("=" * 80)


def health_check():
    """Vérifie l'état de santé de l'API."""
    print_section("1. Health Check")

    response = httpx.get(f"{API_BASE_URL}/health")
    data = response.json()

    print(f"Status: {data['status']}")
    print(f"Version: {data['version']}")
    print(f"Tariff loaded: {data['tariff_loaded']}")

    if data["tariff_info"]:
        print(f"\nTariff Info:")
        print(f"  Product: {data['tariff_info']['product']}")
        print(f"  Version: {data['tariff_info']['version']}")
        print(f"  Currency: {data['tariff_info']['currency']}")
        print(f"  Nodes: {data['tariff_info']['nodes_count']}")


def get_metadata():
    """Récupère les métadonnées du tarif."""
    print_section("2. Metadata")

    response = httpx.get(f"{API_BASE_URL}/metadata")
    data = response.json()

    print(f"Product: {data['product']}")
    print(f"Version: {data['version']}")
    print(f"Currency: {data['currency']}")


def single_pricing():
    """Évalue un tarif pour un contexte simple."""
    print_section("3. Single Pricing")

    # Contexte d'exemple: conducteur de 35 ans avec une BMW
    context = {
        "driver_age": 35,
        "brand": "BMW",
        "density": 1200,
        "neighbourhood_id": 19582,
    }

    request_data = {
        "context": context,
        "target_node": "total_premium",
        "include_trace": False,
    }

    print(f"Context: {json.dumps(context, indent=2)}")

    response = httpx.post(f"{API_BASE_URL}/evaluate", json=request_data)
    data = response.json()

    print(f"\n✓ Result: {data['result']} EUR")


def single_pricing_with_trace():
    """Évalue un tarif avec trace complète."""
    print_section("4. Single Pricing with Trace")

    context = {
        "driver_age": 22,
        "brand": "Renault",
        "density": 800,
        "neighbourhood_id": 19582,
    }

    request_data = {
        "context": context,
        "target_node": "total_premium",
        "include_trace": True,
    }

    print(f"Context: {json.dumps(context, indent=2)}")

    response = httpx.post(f"{API_BASE_URL}/evaluate", json=request_data)
    data = response.json()

    print(f"\n✓ Result: {data['result']} EUR")

    # Afficher quelques nœuds intermédiaires
    print("\nIntermediate nodes (sample):")
    trace = data["trace"]
    for node_name in ["driver_age", "driver_age_factor", "base_premium", "total_premium"]:
        if node_name in trace:
            node_data = trace[node_name]
            print(f"  {node_name:20s}: {node_data['value']:>10s} ({node_data['type']})")


def batch_pricing():
    """Évalue plusieurs contextes en batch."""
    print_section("5. Batch Pricing")

    # Plusieurs contextes à évaluer
    contexts = [
        {
            "driver_age": 22,
            "brand": "Renault",
            "density": 800,
            "neighbourhood_id": 19582,
        },
        {
            "driver_age": 35,
            "brand": "BMW",
            "density": 1200,
            "neighbourhood_id": 19582,
        },
        {
            "driver_age": 70,
            "brand": "Audi",
            "density": 1500,
            "neighbourhood_id": 19582,
        },
    ]

    request_data = {
        "contexts": contexts,
        "target_node": "total_premium",
        "collect_errors": True,
    }

    print(f"Evaluating {len(contexts)} contexts...")

    response = httpx.post(f"{API_BASE_URL}/evaluate/batch", json=request_data)
    data = response.json()

    print(f"\n✓ Total: {data['total_count']}")
    print(f"  Success: {data['success_count']}")
    print(f"  Errors: {data['error_count']}")

    print("\nResults:")
    for result in data["results"]:
        if result["error"] is None:
            driver_age = result["context"]["driver_age"]
            brand = result["context"]["brand"]
            premium = result["result"]
            print(
                f"  Row {result['row_index']}: Age {driver_age}, {brand:10s} -> {premium:>10s} EUR"
            )
        else:
            print(f"  Row {result['row_index']}: ERROR - {result['error']}")


def batch_pricing_with_errors():
    """Évalue un batch avec des erreurs."""
    print_section("6. Batch Pricing with Errors")

    # Contextes avec une erreur intentionnelle (manque density)
    contexts = [
        {
            "driver_age": 35,
            "brand": "BMW",
            "density": 1200,
            "neighbourhood_id": 19582,
        },
        {
            "driver_age": 35,
            "brand": "BMW",
            # Manque density et neighbourhood_id -> erreur
        },
        {
            "driver_age": 22,
            "brand": "Renault",
            "density": 800,
            "neighbourhood_id": 19582,
        },
    ]

    request_data = {
        "contexts": contexts,
        "target_node": "total_premium",
        "collect_errors": True,
    }

    print(f"Evaluating {len(contexts)} contexts (with 1 intentional error)...")

    response = httpx.post(f"{API_BASE_URL}/evaluate/batch", json=request_data)
    data = response.json()

    print(f"\n✓ Total: {data['total_count']}")
    print(f"  Success: {data['success_count']}")
    print(f"  Errors: {data['error_count']}")

    print("\nResults:")
    for result in data["results"]:
        if result["error"] is None:
            driver_age = result["context"]["driver_age"]
            brand = result["context"]["brand"]
            premium = result["result"]
            print(
                f"  Row {result['row_index']}: Age {driver_age}, {brand:10s} -> {premium:>10s} EUR"
            )
        else:
            print(f"  Row {result['row_index']}: ERROR - {result['error'][:80]}...")


def main():
    """Exécute tous les exemples."""
    print("\n")
    print("█" * 80)
    print("  Rating Engine API - Client Example")
    print("█" * 80)

    try:
        # 1. Health check
        health_check()

        # 2. Metadata
        get_metadata()

        # 3. Single pricing
        single_pricing()

        # 4. Single pricing with trace
        single_pricing_with_trace()

        # 5. Batch pricing
        batch_pricing()

        # 6. Batch pricing with errors
        batch_pricing_with_errors()

        print("\n" + "=" * 80)
        print("  ✓ All examples completed successfully!")
        print("=" * 80 + "\n")

    except httpx.ConnectError:
        print("\n❌ Error: Cannot connect to API server.")
        print(f"   Make sure the server is running at {API_BASE_URL}")
        print("   Start it with: uvicorn api.main:app --reload")
    except Exception as e:
        print(f"\n❌ Error: {e}")


if __name__ == "__main__":
    main()
