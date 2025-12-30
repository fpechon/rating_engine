"""
Exemple d'utilisation des exports de traces et métadonnées.

Ce script montre comment:
- Extraire les métadonnées d'un tarif
- Exporter une trace d'évaluation en JSON/CSV
- Exporter des résultats de batch pricing
"""

from pathlib import Path

from engine.graph import TariffGraph
from engine.loader import TariffLoader
from engine.metadata import (
    TariffMetadata,
    export_batch_results,
    export_trace_to_csv,
    export_trace_to_json,
    load_metadata_from_file,
)
from engine.tables import load_exact_table, load_range_table


def example_trace_export():
    """Exemple d'export de trace d'évaluation."""
    print("=" * 80)
    print("Exemple: Export de trace d'évaluation")
    print("=" * 80)

    # Créer un tarif simple
    from decimal import Decimal

    from engine.nodes import AddNode, ConstantNode, InputNode, MultiplyNode

    base = ConstantNode("base_premium", Decimal("500"))
    age = InputNode("driver_age")
    age_factor = ConstantNode("age_factor", Decimal("1.2"))

    technical = MultiplyNode("technical_premium", [base, age_factor])
    fee = ConstantNode("fee", Decimal("25"))
    total = AddNode("total_premium", [technical, fee])

    nodes = {
        "base_premium": base,
        "driver_age": age,
        "age_factor": age_factor,
        "technical_premium": technical,
        "fee": fee,
        "total_premium": total,
    }

    graph = TariffGraph(nodes)

    # Évaluer avec trace
    context = {"driver_age": 30}
    trace = {}
    result = graph.evaluate("total_premium", context, trace=trace)

    print(f"\nRésultat: {result}")
    print(f"Nœuds évalués: {len(trace)}")

    # Créer des métadonnées
    metadata = TariffMetadata(
        product="EXAMPLE_TARIFF",
        version="2025_01",
        currency="EUR",
        effective_date="2025-01-01",
        author="Example Author",
        description="Simple example tariff for demonstration",
    )

    # Export JSON
    print("\n📄 Export JSON...")
    export_trace_to_json(
        trace, "trace_example.json", metadata=metadata, context=context, pretty=True
    )
    print("✓ Exporté: trace_example.json")

    # Export CSV
    print("\n📊 Export CSV...")
    export_trace_to_csv(trace, "trace_example.csv", context=context)
    print("✓ Exporté: trace_example.csv")


def example_batch_export():
    """Exemple d'export de résultats batch."""
    print("\n" + "=" * 80)
    print("Exemple: Export de batch pricing")
    print("=" * 80)

    # Créer un tarif simple
    from decimal import Decimal

    from engine.nodes import ConstantNode, InputNode, MultiplyNode

    base = ConstantNode("base", Decimal("100"))
    factor_input = InputNode("factor")
    result_node = MultiplyNode("result", [base, factor_input])

    nodes = {
        "base": base,
        "factor": factor_input,
        "result": result_node,
    }

    graph = TariffGraph(nodes)

    # Batch evaluation
    contexts = [
        {"factor": 1.0},
        {"factor": 1.5},
        {"factor": 2.0},
        {"factor": 0.8},
        {"factor": 1.2},
    ]

    print(f"\nÉvaluation de {len(contexts)} contextes...")
    results = graph.evaluate_batch("result", contexts)

    print(f"✓ {len(results)} résultats calculés")

    # Export
    print("\n📊 Export des résultats...")
    export_batch_results(results, contexts, "batch_results.csv")
    print("✓ Exporté: batch_results.csv")


def example_batch_with_errors():
    """Exemple d'export batch avec gestion d'erreurs."""
    print("\n" + "=" * 80)
    print("Exemple: Batch avec gestion d'erreurs")
    print("=" * 80)

    # Créer un tarif simple
    from decimal import Decimal

    from engine.nodes import ConstantNode, InputNode, MultiplyNode

    base = ConstantNode("base", Decimal("100"))
    factor_input = InputNode("factor")
    result_node = MultiplyNode("result", [base, factor_input])

    nodes = {
        "base": base,
        "factor": factor_input,
        "result": result_node,
    }

    graph = TariffGraph(nodes)

    # Contextes avec des erreurs volontaires (input manquant)
    contexts = [
        {"factor": 1.0},  # OK
        {},  # Erreur: factor manquant
        {"factor": 1.5},  # OK
        {},  # Erreur: factor manquant
        {"factor": 2.0},  # OK
    ]

    print(f"\nÉvaluation de {len(contexts)} contextes (avec collect_errors=True)...")
    results, errors = graph.evaluate_batch("result", contexts, collect_errors=True)

    # Compter les erreurs
    error_count = sum(1 for e in errors if e is not None)
    success_count = sum(1 for r in results if r is not None)

    print(f"✓ {success_count} succès, {error_count} erreurs")

    # Export
    print("\n📊 Export avec colonne d'erreurs...")
    export_batch_results(results, contexts, "batch_with_errors.csv", errors=errors)
    print("✓ Exporté: batch_with_errors.csv")

    # Afficher les lignes en erreur
    print("\nLignes en erreur:")
    for i, (result, error) in enumerate(zip(results, errors)):
        if error:
            print(f"  Ligne {i}: {contexts[i]} -> {type(error).__name__}: {error}")


def example_load_metadata():
    """Exemple de chargement de métadonnées depuis un tarif existant."""
    print("\n" + "=" * 80)
    print("Exemple: Chargement de métadonnées depuis tarif")
    print("=" * 80)

    tariff_path = Path("tariffs/motor_private/2024_09/tariff.yaml")

    if not tariff_path.exists():
        print(f"\n⚠️  Tarif introuvable: {tariff_path}")
        print("Cet exemple nécessite le tarif motor_private.")
        return

    print(f"\nChargement des métadonnées depuis: {tariff_path}")

    metadata = load_metadata_from_file(str(tariff_path))

    print(f"\nMétadonnées extraites:")
    print(f"  Product: {metadata.product}")
    print(f"  Version: {metadata.version}")
    print(f"  Currency: {metadata.currency}")

    if metadata.effective_date:
        print(f"  Effective Date: {metadata.effective_date}")
    if metadata.author:
        print(f"  Author: {metadata.author}")
    if metadata.description:
        print(f"  Description: {metadata.description}")

    # Convertir en dict
    print("\nDictionnaire complet:")
    meta_dict = metadata.to_dict()
    for key, value in meta_dict.items():
        print(f"  {key}: {value}")


if __name__ == "__main__":
    # Exécuter tous les exemples
    try:
        example_trace_export()
        example_batch_export()
        example_batch_with_errors()
        example_load_metadata()

        print("\n" + "=" * 80)
        print("✨ Tous les exemples ont été exécutés avec succès!")
        print("=" * 80)
        print("\nFichiers générés:")
        print("  - trace_example.json")
        print("  - trace_example.csv")
        print("  - batch_results.csv")
        print("  - batch_with_errors.csv")

    except Exception as e:
        print(f"\n❌ Erreur: {e}")
        import traceback

        traceback.print_exc()
