# Rating Engine - Moteur de Tarification Déclaratif

Un moteur de tarification moderne pour l'assurance P&C (Property & Casualty), basé sur une architecture de graphes DAG avec des tarifs définis en YAML.

## 🎯 Caractéristiques principales

- **Déclaratif**: Tarifs définis en YAML, faciles à auditer et versionner
- **Déterministe**: Arithmétique Decimal pour des calculs reproductibles
- **Traçable**: Traçabilité complète de chaque calcul
- **Performant**: Recherche binaire O(log n), batch evaluation, profiling
- **Extensible**: Nouveaux types de nœuds, tables de lookup flexibles
- **Testé**: 218 tests, 86% coverage

## 🚀 Installation rapide

```bash
# Cloner le projet
git clone https://github.com/fpechon/rating_engine
cd rating_engine

# Installer avec uv (recommandé)
uv sync

# Ou avec pip classique
pip install -e .
```

Ensuite, utilisez `uv run` pour exécuter les commandes Python:
```bash
uv run python examples/visualize_tariff.py
uv run pytest
```

## 📖 Guide de démarrage - 5 minutes

### 1. Créer un tarif simple

Créez `my_tariff.yaml`:

```yaml
product: MY_PRODUCT
version: 2025_01
currency: EUR

nodes:
  # Inputs
  age:
    type: INPUT
    dtype: decimal

  # Constants
  base_premium:
    type: CONSTANT
    value: 100

  age_factor:
    type: CONSTANT
    value: 1.2

  # Calculations
  adjusted_premium:
    type: MULTIPLY
    inputs:
      - base_premium
      - age_factor

  fee:
    type: CONSTANT
    value: 10

  total:
    type: ADD
    inputs:
      - adjusted_premium
      - fee
```

### 2. Évaluer le tarif

```python
from engine.loader import TariffLoader
from engine.graph import TariffGraph

# Charger le tarif
loader = TariffLoader()
nodes = loader.load("my_tariff.yaml")
graph = TariffGraph(nodes)

# Évaluer pour un contexte donné
context = {"age": 30}
result = graph.evaluate("total", context)
print(f"Premium: {result}")  # Premium: 130
```

### 3. Avec des tables de lookup

Créez `age_factors.csv`:

```csv
min,max,value
18,25,1.8
26,65,1.0
66,99,1.3
```

Modifiez le tarif:

```yaml
nodes:
  age:
    type: INPUT
    dtype: decimal

  base_premium:
    type: CONSTANT
    value: 100

  age_factor:
    type: LOOKUP
    table: age_table
    key_node: age
    mode: range

  premium:
    type: MULTIPLY
    inputs: [base_premium, age_factor]
```

Chargez avec la table:

```python
from engine.tables import load_range_table

tables = {
    "age_table": load_range_table("age_factors.csv")
}

loader = TariffLoader(tables=tables)
nodes = loader.load("my_tariff.yaml")
graph = TariffGraph(nodes)

# Jeune conducteur (22 ans)
print(graph.evaluate("premium", {"age": 22}))  # 180.0 (100 * 1.8)

# Conducteur senior (70 ans)
print(graph.evaluate("premium", {"age": 70}))  # 130.0 (100 * 1.3)
```

## 📚 Documentation complète

- **[Guide utilisateur](docs/user_guide.md)** - Documentation détaillée
- **[Tutoriel](docs/tutorial.md)** - Créer votre premier tarif pas à pas
- **[Référence des nœuds](docs/nodes_reference.md)** - Tous les types de nœuds disponibles
- **[Guide de performance](docs/performance_guide.md)** - Optimisations et benchmarks
- **[Nouveaux nœuds](docs/new_nodes_guide.md)** - Switch, Coalesce, Min, Max, Abs

## 🔧 Types de nœuds disponibles

### Nœuds de base
- **INPUT**: Variable d'entrée
- **CONSTANT**: Valeur fixe
- **ADD**: Addition de valeurs
- **MULTIPLY**: Multiplication
- **LOOKUP**: Recherche dans une table
- **IF**: Condition simple
- **ROUND**: Arrondi

### Nœuds avancés
- **SWITCH**: Multi-branches (switch/case)
- **COALESCE**: Première valeur non-nulle
- **MIN/MAX**: Minimum/Maximum
- **ABS**: Valeur absolue

Voir [Référence complète](docs/nodes_reference.md) pour tous les détails.

## 🎨 Visualisation interactive

```bash
# Générer une visualisation HTML interactive
uv run python examples/visualize_tariff.py

# Ouvrir motor_tariff_evaluated.html dans un navigateur
```

![Exemple de visualisation](docs/images/viz_example.png)

## ⚡ Batch Pricing

Pour évaluer des milliers de contextes en une seule fois:

```python
import pandas as pd

# Créer un DataFrame avec vos données
df = pd.DataFrame({
    "age": [22, 45, 67],
    "brand": ["BMW", "Toyota", "Audi"]
})

# Batch evaluation
contexts = df.to_dict('records')
results = graph.evaluate_batch("total_premium", contexts)

df["premium"] = results
print(df)
```

Performance: ~15,000-20,000 évaluations/seconde sur un CPU moderne.

## 🧪 Tests et qualité

```bash
# Lancer tous les tests
uv run pytest

# Avec coverage
uv run pytest --cov=engine --cov-report=html

# Tests rapides (sans coverage)
uv run pytest -q
```

Actuellement: **218 tests** avec **86.20% coverage**.

## 🔍 Profiling et debugging

### Activer le profiling

```python
from engine.profiler import PerformanceProfiler

profiler = PerformanceProfiler()

# Passer le profiler à evaluate
result = graph.evaluate("total_premium", context, profiler=profiler)

# Afficher le rapport
profiler.print_report(top_n=10)
```

### Obtenir une trace complète

```python
trace = {}
result = graph.evaluate("total_premium", context, trace=trace)

# Inspecter tous les nœuds évalués
for node_name, info in trace.items():
    print(f"{node_name}: {info['value']} ({info['type']})")
```

## 📊 Exemple réel: Tarif Auto

Le projet inclut un tarif d'assurance automobile complet:

```python
from pathlib import Path
from engine.loader import TariffLoader
from engine.tables import load_range_table, load_exact_table
from engine.graph import TariffGraph

# Charger les tables
tables_dir = Path("tariffs/motor_private/2024_09/tables")
tables = {
    "driver_age_factor": load_range_table(str(tables_dir / "driver_age_factor.csv")),
    "vehicle_brand_category": load_exact_table(
        str(tables_dir / "vehicle_brand_category.csv"),
        key_column="key",
        value_column="value",
    ),
    "zoning": load_exact_table(
        str(tables_dir / "zoning.csv"),
        key_column="neighbourhood_id",
        value_column="zone",
        key_type=int,
    ),
    # ... autres tables
}

# Charger le tarif
loader = TariffLoader(tables=tables)
nodes = loader.load("tariffs/motor_private/2024_09/tariff.yaml")
graph = TariffGraph(nodes)

# Calculer une prime
context = {
    "driver_age": 35,
    "brand": "BMW",
    "density": 1200,
    "neighbourhood_id": "19582",
}

premium = graph.evaluate("total_premium", context)
print(f"Prime totale: {premium} EUR")  # 429.18 EUR
```

## 🛠️ Architecture

```
rating_engine/
├── engine/              # Core du moteur
│   ├── nodes.py        # Types de nœuds (INPUT, ADD, LOOKUP, etc.)
│   ├── graph.py        # Évaluation du graphe DAG
│   ├── loader.py       # Chargement depuis YAML
│   ├── tables.py       # Tables de lookup (range, exact)
│   ├── validation.py   # Gestion d'erreurs
│   └── profiler.py     # Profiling de performance
├── tools/              # Outils
│   ├── interactive_viz.py  # Visualisation HTML
│   └── visualize.py    # Visualisation Graphviz
├── examples/           # Exemples d'utilisation
├── tests/              # Tests (218 tests, 86% coverage)
├── tariffs/            # Définitions de tarifs
└── docs/               # Documentation
```

## 🤝 Contribution

```bash
# Installer les dépendances de dev
uv sync --dev

# Installer les pre-commit hooks
uv run pre-commit install

# Avant de committer
uv run pytest                    # Tests
uv run pytest --cov=engine      # Coverage
uv run black --check engine tools    # Formatting
uv run isort --check engine tools    # Import sorting
uv run flake8 engine tools           # Linting
```

## 📈 Performance

- **Recherche dans tables**: O(log n) avec binary search (700x speedup pour 20k lignes)
- **Batch evaluation**: 15,000-20,000 eval/s
- **Chargement tarif**: < 100ms pour tarifs moyens
- **Mémoire**: ~50MB pour tarif avec table 20k lignes

Voir [Guide de performance](docs/performance_guide.md) pour plus de détails.

## 📝 Versionnage des tarifs

Chaque tarif inclut des métadonnées de versionnage:

```yaml
product: MOTOR_PRIVATE
version: 2024_09
currency: EUR
metadata:
  effective_date: 2024-09-01
  author: Actuarial Team
  description: "Q3 2024 motor tariff update"
```

## 🔒 Sécurité

- Arithmétique Decimal pour éviter les erreurs de précision
- Validation stricte des inputs
- Gestion d'erreurs avec contexte complet
- Traçabilité complète pour audit

## 📄 Licence

[À définir]

## 📞 Support

- Issues: [GitHub Issues](lien-github)
- Documentation: [docs/](docs/)
- Exemples: [examples/](examples/)
