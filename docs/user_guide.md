# Guide Utilisateur - Rating Engine

Guide complet pour utiliser le moteur de tarification.

## Table des matières

1. [Introduction](#introduction)
2. [Installation](#installation)
3. [Concepts fondamentaux](#concepts-fondamentaux)
4. [Créer un tarif](#créer-un-tarif)
5. [Types de nœuds](#types-de-nœuds)
6. [Tables de lookup](#tables-de-lookup)
7. [Évaluation](#évaluation)
8. [Debugging et traçabilité](#debugging-et-traçabilité)
9. [Performance](#performance)
10. [Bonnes pratiques](#bonnes-pratiques)

---

## Introduction

Le Rating Engine est un moteur de tarification déclaratif basé sur des graphes DAG (Directed Acyclic Graph). Il permet de définir des règles de tarification complexes de manière lisible et maintenable.

### Pourquoi déclaratif?

- **Lisibilité**: Les tarifs sont définis en YAML, compréhensibles par les actuaires
- **Versionnable**: Git peut tracker les changements de tarifs
- **Auditable**: Chaque calcul est traçable
- **Testable**: Facile de tester différents scénarios

### Architecture en un coup d'œil

```
Tarif YAML + Tables CSV
        ↓
    Loader
        ↓
    Graphe de nœuds
        ↓
    Évaluation (contexte)
        ↓
    Résultat (Decimal)
```

---

## Installation

### Prérequis

- Python 3.11+
- uv (recommandé) ou pip

### Installation avec uv

```bash
git clone <repo>
cd rating_engine
uv venv
source .venv/bin/activate
uv pip install -e .
```

### Installation avec pip

```bash
pip install -e .
```

### Vérifier l'installation

```python
from engine.loader import TariffLoader
from engine.graph import TariffGraph
print("Installation OK!")
```

---

## Concepts fondamentaux

### 1. Nœuds (Nodes)

Un **nœud** est une unité de calcul. Exemples:
- Une constante: `100`
- Une variable d'entrée: `age`
- Un calcul: `base_premium * age_factor`

### 2. Graphe (Graph)

Un **graphe** est un ensemble de nœuds connectés par des dépendances.

```yaml
nodes:
  base: {type: CONSTANT, value: 100}
  factor: {type: CONSTANT, value: 1.2}
  result: {type: MULTIPLY, inputs: [base, factor]}
```

Graphe résultant:
```
base (100) ─┐
            ├─> result (120)
factor (1.2)┘
```

### 3. Contexte (Context)

Le **contexte** fournit les valeurs des inputs:

```python
context = {
    "age": 30,
    "brand": "BMW",
    "density": 1200
}
```

### 4. Évaluation (Evaluation)

L'**évaluation** parcourt le graphe et calcule les valeurs:

```python
result = graph.evaluate("total_premium", context)
```

---

## Créer un tarif

### Structure d'un tarif YAML

```yaml
# Métadonnées
product: PRODUCT_NAME
version: 2025_01
currency: EUR

# Optionnel: métadonnées enrichies
metadata:
  effective_date: 2025-01-01
  author: John Doe
  description: "Description du tarif"

# Définition des nœuds
nodes:
  node_name:
    type: NODE_TYPE
    # Paramètres spécifiques au type
```

### Exemple minimal

```yaml
product: SIMPLE_TARIFF
version: 1.0
currency: EUR

nodes:
  premium:
    type: CONSTANT
    value: 100
```

### Exemple avec inputs

```yaml
product: AGE_BASED
version: 1.0
currency: EUR

nodes:
  age:
    type: INPUT
    dtype: decimal

  base_premium:
    type: CONSTANT
    value: 100

  young_driver_surcharge:
    type: IF
    condition: age < 26
    then: 50
    else: 0

  total_premium:
    type: ADD
    inputs:
      - base_premium
      - young_driver_surcharge
```

### Exemple avec table de lookup

```yaml
product: MOTOR_INSURANCE
version: 1.0
currency: EUR

nodes:
  driver_age:
    type: INPUT
    dtype: decimal

  base_premium:
    type: CONSTANT
    value: 500

  age_factor:
    type: LOOKUP
    table: age_table
    key_node: driver_age
    mode: range

  premium:
    type: MULTIPLY
    inputs: [base_premium, age_factor]

  premium_rounded:
    type: ROUND
    input: premium
    decimals: 2
    mode: HALF_UP
```

---

## Types de nœuds

Voir [Référence des nœuds](nodes_reference.md) pour la documentation complète.

### Nœuds de base

| Type | Description | Exemple |
|------|-------------|---------|
| **INPUT** | Variable d'entrée | `age`, `brand` |
| **CONSTANT** | Valeur fixe | `100`, `1.5` |
| **ADD** | Addition | `a + b + c` |
| **MULTIPLY** | Multiplication | `a * b * c` |
| **LOOKUP** | Recherche table | Table de facteurs |
| **IF** | Condition | `if age < 25 then X else Y` |
| **ROUND** | Arrondi | Arrondir à 2 décimales |

### Nœuds avancés

| Type | Description | Exemple |
|------|-------------|---------|
| **SWITCH** | Multi-branches | Switch sur catégorie |
| **COALESCE** | Première valeur non-nulle | Valeur par défaut |
| **MIN** | Minimum | `min(a, b, c)` |
| **MAX** | Maximum | `max(a, b, c)` |
| **ABS** | Valeur absolue | `abs(x)` |

---

## Tables de lookup

### Types de tables

#### 1. RangeTable (Plages de valeurs)

Pour des lookups sur des intervalles continus (âge, kilométrage, etc.).

**Fichier CSV** (`age_factors.csv`):
```csv
min,max,value
18,25,1.8
26,65,1.0
66,99,1.3
```

**Utilisation**:
```python
from engine.tables import load_range_table

table = load_range_table("age_factors.csv")
print(table.lookup(22))  # 1.8
print(table.lookup(45))  # 1.0
print(table.lookup(70))  # 1.3
```

**Dans un tarif**:
```yaml
nodes:
  age_factor:
    type: LOOKUP
    table: age_table
    key_node: driver_age
    mode: range
```

#### 2. ExactMatchTable (Correspondance exacte)

Pour des lookups sur des valeurs discrètes (marque, zone, etc.).

**Fichier CSV** (`brand_factors.csv`):
```csv
key,value
BMW,1.2
Audi,1.15
Toyota,0.95
```

**Utilisation**:
```python
from engine.tables import load_exact_table

table = load_exact_table(
    "brand_factors.csv",
    key_column="key",
    value_column="value"
)
print(table.lookup("BMW"))  # 1.2
```

**Dans un tarif**:
```yaml
nodes:
  brand_factor:
    type: LOOKUP
    table: brand_table
    key_node: brand
    mode: exact
```

### Valeurs par défaut

```python
# RangeTable avec défaut
table = load_range_table("ages.csv", default=Decimal("1.0"))

# ExactMatchTable avec défaut
table = load_exact_table(
    "brands.csv",
    key_column="key",
    value_column="value",
    default=Decimal("1.0")
)
```

### Types de clés personnalisés

Par défaut, les clés sont des strings. Pour des clés entières:

```python
table = load_exact_table(
    "zones.csv",
    key_column="zone_id",
    value_column="factor",
    key_type=int
)
```

---

## Évaluation

### Évaluation simple

```python
from engine.loader import TariffLoader
from engine.graph import TariffGraph

# Charger
loader = TariffLoader(tables=tables)
nodes = loader.load("tariff.yaml")
graph = TariffGraph(nodes)

# Évaluer
context = {"age": 30, "brand": "BMW"}
result = graph.evaluate("total_premium", context)
print(f"Premium: {result}")
```

### Évaluation batch

Pour traiter plusieurs contextes en une fois:

```python
contexts = [
    {"age": 22, "brand": "BMW"},
    {"age": 45, "brand": "Toyota"},
    {"age": 67, "brand": "Audi"},
]

results = graph.evaluate_batch("total_premium", contexts)
# results = [Decimal('180.0'), Decimal('95.0'), Decimal('130.0')]
```

### Gestion d'erreurs en batch

```python
results, errors = graph.evaluate_batch(
    "total_premium",
    contexts,
    collect_errors=True
)

# Traiter les erreurs
for i, (result, error) in enumerate(zip(results, errors)):
    if error:
        print(f"Ligne {i}: Erreur - {error}")
    else:
        print(f"Ligne {i}: {result}")
```

### Avec pandas DataFrame

```python
import pandas as pd

df = pd.DataFrame({
    "age": [22, 45, 67],
    "brand": ["BMW", "Toyota", "Audi"]
})

contexts = df.to_dict('records')
results = graph.evaluate_batch("total_premium", contexts)

df["premium"] = results
print(df)
```

---

## Debugging et traçabilité

### Obtenir une trace complète

```python
trace = {}
result = graph.evaluate("total_premium", context, trace=trace)

# trace contient tous les nœuds évalués
for node_name, info in trace.items():
    print(f"{node_name}:")
    print(f"  Valeur: {info['value']}")
    print(f"  Type: {info['type']}")
    print(f"  Chemin: {' -> '.join(info['path'])}")
```

### Gestion d'erreurs enrichie

Le moteur fournit des erreurs détaillées avec contexte:

```python
from engine.validation import EvaluationError

try:
    result = graph.evaluate("total_premium", context)
except EvaluationError as e:
    print(f"Erreur sur le nœud: {e.node_name}")
    print(f"Chemin: {' -> '.join(e.node_path)}")
    print(f"Contexte: {e.context}")
    print(f"Erreur originale: {e.original_error}")
```

### Profiling de performance

```python
from engine.profiler import PerformanceProfiler

profiler = PerformanceProfiler()
result = graph.evaluate("total_premium", context, profiler=profiler)

# Afficher le rapport
profiler.print_report(top_n=10)
```

Output:
```
Performance Report:
==================
Total time: 0.123s (123.45ms)
Total calls: 1234
Cache hit rate: 85.3%

Top 10 slowest nodes:
 1. technical_premium: 45.2ms (123 calls, 0.37ms avg, cache hit: 80.0%)
 2. age_factor: 32.1ms (456 calls, 0.07ms avg, cache hit: 90.0%)
...
```

### Visualisation interactive

```python
from tools.interactive_viz import generate_interactive_viz

# Sans évaluation (structure uniquement)
generate_interactive_viz(
    graph,
    output_path="tariff_structure.html",
    title="My Tariff Structure"
)

# Avec évaluation (affiche les valeurs)
trace = {}
result = graph.evaluate("total_premium", context, trace=trace)

generate_interactive_viz(
    graph,
    output_path="tariff_evaluated.html",
    trace=trace,
    context=context,
    title=f"Evaluated Tariff (premium = {result})"
)
```

Ouvrez le fichier HTML dans un navigateur pour explorer le graphe interactivement.

---

## Performance

### Optimisations automatiques

Le moteur optimise automatiquement:
- **Cache**: Chaque nœud n'est évalué qu'une fois par contexte
- **Binary search**: O(log n) pour les RangeTables
- **Lazy evaluation**: Seuls les nœuds nécessaires sont évalués

### Benchmarks

Sur un CPU moderne (Intel i7):
- **Évaluation simple**: ~50-100 µs
- **Batch 10,000 contextes**: ~0.5-1s (15,000-20,000 eval/s)
- **Lookup dans table 20k lignes**: ~14 comparaisons (vs 10,000 en linéaire)

### Conseils de performance

#### 1. Utilisez batch evaluation

```python
# ❌ Lent: boucle Python
results = [graph.evaluate("premium", ctx) for ctx in contexts]

# ✅ Rapide: batch evaluation
results = graph.evaluate_batch("premium", contexts)
```

#### 2. Pré-chargez les tables

```python
# ❌ Chargement à chaque fois
for tariff_file in tariff_files:
    tables = load_all_tables()  # Lent!
    loader = TariffLoader(tables=tables)
    # ...

# ✅ Chargement une seule fois
tables = load_all_tables()
for tariff_file in tariff_files:
    loader = TariffLoader(tables=tables)
    # ...
```

#### 3. Désactivez le profiling en production

```python
# Profiling a un petit overhead (~5-10%)
profiler = PerformanceProfiler(enabled=False)
```

Voir [Guide de performance](performance_guide.md) pour plus de détails.

---

## Bonnes pratiques

### 1. Nommage des nœuds

```yaml
# ✅ Bon: noms descriptifs
nodes:
  base_premium:
    type: CONSTANT
    value: 500

  driver_age_factor:
    type: LOOKUP
    table: age_table
    key_node: driver_age

  technical_premium:
    type: MULTIPLY
    inputs: [base_premium, driver_age_factor]

# ❌ Mauvais: noms cryptiques
nodes:
  bp: {type: CONSTANT, value: 500}
  daf: {type: LOOKUP, table: age_table, key_node: age}
  tp: {type: MULTIPLY, inputs: [bp, daf]}
```

### 2. Organisation des nœuds

Groupez logiquement les nœuds:

```yaml
nodes:
  # === INPUTS ===
  driver_age: {type: INPUT, dtype: decimal}
  brand: {type: INPUT, dtype: str}

  # === CONSTANTS ===
  base_premium: {type: CONSTANT, value: 500}
  fee: {type: CONSTANT, value: 25}

  # === FACTORS ===
  age_factor: {type: LOOKUP, table: age_table, key_node: driver_age}
  brand_factor: {type: LOOKUP, table: brand_table, key_node: brand}

  # === CALCULATIONS ===
  technical_premium: {type: MULTIPLY, inputs: [base_premium, age_factor, brand_factor]}

  # === RESULT ===
  total_premium: {type: ADD, inputs: [technical_premium, fee]}
```

### 3. Validation des inputs

Utilisez des conditions pour valider:

```yaml
nodes:
  age: {type: INPUT, dtype: decimal}

  age_valid:
    type: IF
    condition: age >= 18
    then: age
    else: null  # Forcera une erreur

  age_factor:
    type: LOOKUP
    table: age_table
    key_node: age_valid
```

### 4. Commentaires dans le YAML

```yaml
nodes:
  # Surcharge jeune conducteur: +80% pour les moins de 26 ans
  young_driver_factor:
    type: IF
    condition: driver_age < 26
    then: 1.8
    else: 1.0
```

### 5. Versionnage des tarifs

```yaml
product: MOTOR_PRIVATE
version: 2025_01  # Format: YYYY_MM ou YYYY_QN
currency: EUR

metadata:
  effective_date: 2025-01-01
  author: Actuarial Team
  description: |
    Q1 2025 tariff update:
    - Updated age factors based on claims data
    - New brand categories
  changelog:
    - version: 2024_Q4
      changes: "Initial version"
```

### 6. Tests

Créez des tests pour vos tarifs:

```python
def test_young_driver_premium():
    """Test que les jeunes conducteurs paient plus."""
    context_young = {"age": 22, "brand": "BMW"}
    context_old = {"age": 45, "brand": "BMW"}

    premium_young = graph.evaluate("total_premium", context_young)
    premium_old = graph.evaluate("total_premium", context_old)

    assert premium_young > premium_old
```

### 7. Documentation

Documentez vos choix dans `README` du tarif:

```
tariffs/motor_private/2024_09/
├── README.md          # Documentation du tarif
├── tariff.yaml
└── tables/
    ├── age_factors.csv
    └── ...
```

---

## Troubleshooting

### Erreur: "Node not found"

```
KeyError: Node 'xyz' not found in graph
```

**Solution**: Vérifiez que le nœud est bien défini dans le YAML:
```yaml
nodes:
  xyz:  # Nom doit correspondre exactement
    type: CONSTANT
    value: 100
```

### Erreur: "Missing input variable"

```
EvaluationError: Missing input variable 'age'
```

**Solution**: Fournissez toutes les variables INPUT dans le contexte:
```python
context = {
    "age": 30,  # Ne pas oublier!
    "brand": "BMW"
}
```

### Erreur: "Value outside all ranges"

```
KeyError: Value 17 outside all ranges
```

**Solution**:
1. Vérifiez que votre table couvre toutes les valeurs possibles
2. Ou ajoutez un `default`:
```python
table = load_range_table("ages.csv", default=Decimal("1.0"))
```

### Performance dégradée

**Symptômes**: Évaluation lente, mémoire élevée

**Solutions**:
1. Utilisez le profiler pour identifier les nœuds lents
2. Vérifiez la taille de vos tables
3. Utilisez batch evaluation au lieu de boucles Python
4. Désactivez le profiling en production

---

## Prochaines étapes

- Lire le [Tutoriel](tutorial.md) pour un exemple pas à pas
- Explorer la [Référence des nœuds](nodes_reference.md)
- Consulter le [Guide de performance](performance_guide.md)
- Voir les exemples dans `examples/`
