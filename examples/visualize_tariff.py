"""
Exemple d'utilisation de la visualisation interactive.

Ce script montre comment générer une visualisation interactive d'un tarif,
avec ou sans évaluation.
"""

from pathlib import Path

from engine.graph import TariffGraph
from engine.loader import TariffLoader
from tools.interactive_viz import generate_interactive_viz


def visualize_motor_tariff():
    """Visualise le tarif motor_private avec évaluation."""

    # Chemin vers le tarif (relatif au répertoire du projet)
    project_root = Path(__file__).parent.parent
    tariff_path = project_root / "tariffs/motor_private/2024_09/tariff.yaml"

    # Charger le tarif (avec ses tables déclarées dans le YAML)
    print("📊 Chargement du tarif...")
    loader = TariffLoader()
    nodes, tables_loaded = loader.load_with_tables(str(tariff_path))
    graph = TariffGraph(nodes)

    print(f"✓ Tarif chargé: {len(nodes)} nœuds")
    print(f"✓ Tables: {', '.join(tables_loaded)}")

    # Génération 1: Visualisation simple (structure seulement)
    print("\n🎨 Génération de la visualisation simple...")
    generate_interactive_viz(
        graph,
        output_path="motor_tariff_structure.html",
        title="Motor Private Tariff - Structure",
    )

    # Génération 2: Visualisation avec évaluation
    print("\n🎨 Génération de la visualisation avec évaluation...")
    context = {
        "driver_age": 35,
        "brand": "BMW",
        "density": 1200,
        "neighbourhood_id": "19582",
    }

    trace = {}
    graph.evaluate("total_premium", context, trace=trace)
    result = trace["total_premium"]["value"]

    print(f"✓ Évaluation: total_premium = {result}")

    generate_interactive_viz(
        graph,
        output_path="motor_tariff_evaluated.html",
        trace=trace,
        context=context,
        title=f"Motor Private Tariff - Evaluated (premium = {result})",
    )

    print("\n✨ Visualisations générées:")
    print("  - motor_tariff_structure.html (structure)")
    print("  - motor_tariff_evaluated.html (avec valeurs)")
    print("\nOuvrez ces fichiers dans un navigateur pour explorer le graphe!")


def visualize_simple_example():
    """Crée et visualise un exemple simple."""
    from decimal import Decimal

    from engine.nodes import AddNode, ConstantNode, InputNode, MultiplyNode

    print("📊 Création d'un exemple simple...")

    # Créer un graphe simple
    base = ConstantNode("base_premium", Decimal("500"))
    age = InputNode("driver_age")
    age_factor = ConstantNode("age_factor", Decimal("1.2"))

    adjusted = MultiplyNode("adjusted_premium", [base, age_factor])
    fee = ConstantNode("fee", Decimal("25"))
    total = AddNode("total_premium", [adjusted, fee])

    nodes = {
        "base_premium": base,
        "driver_age": age,
        "age_factor": age_factor,
        "adjusted_premium": adjusted,
        "fee": fee,
        "total_premium": total,
    }

    graph = TariffGraph(nodes)

    # Évaluation
    context = {"driver_age": 30}
    trace = {}
    graph.evaluate("total_premium", context, trace=trace)
    result = trace["total_premium"]["value"]

    print(f"✓ Exemple créé: {len(nodes)} nœuds")
    print(f"✓ Évaluation: total_premium = {result}")

    # Visualisation
    print("\n🎨 Génération de la visualisation...")
    generate_interactive_viz(
        graph,
        output_path="simple_example.html",
        trace=trace,
        context=context,
        title=f"Simple Example (premium = {result})",
    )

    print("\n✨ Visualisation générée: simple_example.html")
    print("Ouvrez ce fichier dans un navigateur!")


if __name__ == "__main__":
    import sys

    print("=" * 80)
    print("Visualisation Interactive de Tarifs")
    print("=" * 80)

    if len(sys.argv) > 1 and sys.argv[1] == "simple":
        visualize_motor_tariff()
    else:
        try:
            visualize_motor_tariff()
        except FileNotFoundError as e:
            print(f"\n⚠️  Tarif motor_private introuvable.")
            print("Génération d'un exemple simple à la place...\n")
            visualize_simple_example()
