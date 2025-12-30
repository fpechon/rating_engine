# Tutoriel - Créer votre premier tarif

Ce tutoriel vous guide pas à pas dans la création d'un tarif d'assurance automobile simple mais complet.

## Objectif

Créer un tarif automobile qui calcule une prime basée sur:
- L'âge du conducteur
- La marque du véhicule
- La densité de population

## Étape 1: Setup du projet

Créez un nouveau répertoire pour votre tarif:

```bash
mkdir my_motor_tariff
cd my_motor_tariff
```

Structure finale:
```
my_motor_tariff/
├── tariff.yaml
└── tables/
    ├── age_factors.csv
    └── brand_factors.csv
```

## Étape 2: Créer les tables de facteurs

### Table des facteurs d'âge

Créez `tables/age_factors.csv`:

```csv
min,max,value
18,25,1.8
26,35,1.2
36,55,1.0
56,99,1.3
```

**Logique**:
- Jeunes conducteurs (18-25): +80% (risque élevé)
- Conducteurs moyens (36-55): facteur de base 1.0
- Seniors (56+): +30% (statistiques montrent plus d'accidents)

### Table des facteurs de marque

Créez `tables/brand_factors.csv`:

```csv
brand,factor
BMW,1.15
Mercedes,1.20
Audi,1.12
Toyota,0.95
Honda,0.93
Ford,1.00
Volkswagen,1.05
Peugeot,0.98
Renault,0.97
```

**Logique**:
- Marques premium (BMW, Mercedes): facteur plus élevé (voitures chères à réparer)
- Marques économiques (Toyota, Honda): facteur réduit

## Étape 3: Créer le tarif YAML

Créez `tariff.yaml`:

```yaml
product: MOTOR_INSURANCE
version: 2025_01
currency: EUR

metadata:
  effective_date: 2025-01-01
  author: "Votre Nom"
  description: "Mon premier tarif auto"

nodes:
  # ========================================
  # INPUTS - Variables fournies par l'utilisateur
  # ========================================

  driver_age:
    type: INPUT
    dtype: decimal

  brand:
    type: INPUT
    dtype: str

  density:
    type: INPUT
    dtype: decimal

  # ========================================
  # CONSTANTS - Valeurs fixes
  # ========================================

  base_premium:
    type: CONSTANT
    value: 500

  admin_fee:
    type: CONSTANT
    value: 25

  # ========================================
  # FACTORS - Facteurs de tarification
  # ========================================

  age_factor:
    type: LOOKUP
    table: age_table
    key_node: driver_age
    mode: range

  brand_factor:
    type: LOOKUP
    table: brand_table
    key_node: brand
    mode: exact

  # Facteur de densité: +20% si densité > 1000 (zone urbaine)
  density_factor:
    type: IF
    condition: density > 1000
    then: 1.20
    else: 1.00

  # ========================================
  # CALCULATIONS - Calculs intermédiaires
  # ========================================

  # Prime technique = base * tous les facteurs
  technical_premium:
    type: MULTIPLY
    inputs:
      - base_premium
      - age_factor
      - brand_factor
      - density_factor

  # Prime brute = technique + frais
  raw_total:
    type: ADD
    inputs:
      - technical_premium
      - admin_fee

  # ========================================
  # RESULT - Résultat final
  # ========================================

  total_premium:
    type: ROUND
    input: raw_total
    decimals: 2
    mode: HALF_UP
```

## Étape 4: Charger et tester le tarif

Créez un script `test_tariff.py`:

```python
from pathlib import Path
from engine.loader import TariffLoader
from engine.tables import load_range_table, load_exact_table
from engine.graph import TariffGraph

# Charger les tables
tables = {
    "age_table": load_range_table("tables/age_factors.csv"),
    "brand_table": load_exact_table(
        "tables/brand_factors.csv",
        key_column="brand",
        value_column="factor"
    )
}

# Charger le tarif
loader = TariffLoader(tables=tables)
nodes = loader.load("tariff.yaml")
graph = TariffGraph(nodes)

# Test 1: Jeune conducteur, BMW, zone urbaine
print("=== Test 1: Jeune conducteur ===")
context1 = {
    "driver_age": 22,
    "brand": "BMW",
    "density": 1500  # Urbain
}
premium1 = graph.evaluate("total_premium", context1)
print(f"Contexte: {context1}")
print(f"Prime: {premium1} EUR")
print()

# Test 2: Conducteur expérimenté, Toyota, zone rurale
print("=== Test 2: Conducteur expérimenté ===")
context2 = {
    "driver_age": 45,
    "brand": "Toyota",
    "density": 500  # Rural
}
premium2 = graph.evaluate("total_premium", context2)
print(f"Contexte: {context2}")
print(f"Prime: {premium2} EUR")
print()

# Test 3: Senior, Mercedes, zone urbaine
print("=== Test 3: Senior ===")
context3 = {
    "driver_age": 67,
    "brand": "Mercedes",
    "density": 2000  # Urbain dense
}
premium3 = graph.evaluate("total_premium", context3)
print(f"Contexte: {context3}")
print(f"Prime: {premium3} EUR")
```

Exécutez:

```bash
python test_tariff.py
```

Output attendu:
```
=== Test 1: Jeune conducteur ===
Contexte: {'driver_age': 22, 'brand': 'BMW', 'density': 1500}
Prime: 1267.00 EUR

=== Test 2: Conducteur expérimenté ===
Contexte: {'driver_age': 45, 'brand': 'Toyota', 'density': 500}
Prime: 500.00 EUR

=== Test 3: Senior ===
Contexte: {'driver_age': 67, 'brand': 'Mercedes', 'density': 2000}
Prime: 1011.00 EUR
```

## Étape 5: Comprendre les calculs

Analysons le Test 1 en détail:

```python
trace = {}
premium = graph.evaluate("total_premium", context1, trace=trace)

for node_name, info in trace.items():
    print(f"{node_name:20s}: {info['value']}")
```

Output:
```
driver_age          : 22
brand               : BMW
density             : 1500
base_premium        : 500
admin_fee           : 25
age_factor          : 1.8      # Lookup: 22 ans -> 1.8
brand_factor        : 1.15     # Lookup: BMW -> 1.15
density_factor      : 1.20     # IF: 1500 > 1000 -> 1.20
technical_premium   : 1242.00  # 500 * 1.8 * 1.15 * 1.20
raw_total           : 1267.00  # 1242.00 + 25
total_premium       : 1267.00  # Arrondi à 2 décimales
```

## Étape 6: Visualiser le tarif

```python
from tools.interactive_viz import generate_interactive_viz

# Générer une visualisation
generate_interactive_viz(
    graph,
    output_path="my_tariff.html",
    trace=trace,
    context=context1,
    title=f"My Motor Tariff (premium = {premium})"
)

print("Ouvrir my_tariff.html dans un navigateur!")
```

La visualisation montre:
- Les nœuds colorés par type
- Les flèches de dépendances
- Les valeurs évaluées pour ce contexte
- Cliquez sur un nœud pour voir les détails

## Étape 7: Batch pricing

Pour calculer plusieurs primes en une fois:

```python
import pandas as pd

# Créer un portefeuille de clients
portfolio = pd.DataFrame({
    "driver_age": [22, 35, 45, 55, 67],
    "brand": ["BMW", "Toyota", "Ford", "Audi", "Mercedes"],
    "density": [1500, 500, 800, 1200, 2000]
})

# Calculer les primes
contexts = portfolio.to_dict('records')
premiums = graph.evaluate_batch("total_premium", contexts)

portfolio["premium"] = premiums
print(portfolio)
```

Output:
```
   driver_age      brand  density   premium
0          22        BMW     1500   1267.00
1          35     Toyota      500    595.00
2          45       Ford      800    525.00
3          55       Audi     1200    560.00
4          67   Mercedes     2000   1011.00
```

## Étape 8: Améliorer le tarif

### 8.1 Ajouter un plafond

Limiter la prime maximale à 2000 EUR:

```yaml
nodes:
  # ... (nœuds existants)

  # Plafond de prime
  max_premium:
    type: CONSTANT
    value: 2000

  # Prime finale avec plafond
  total_premium_capped:
    type: MIN
    inputs:
      - raw_total
      - max_premium

  # Arrondir
  total_premium:
    type: ROUND
    input: total_premium_capped
    decimals: 2
    mode: HALF_UP
```

### 8.2 Ajouter un discount multi-véhicules

```yaml
nodes:
  # Input supplémentaire
  num_vehicles:
    type: INPUT
    dtype: decimal

  # Discount: 10% si 2+ véhicules
  multi_vehicle_discount:
    type: IF
    condition: num_vehicles >= 2
    then: 0.90
    else: 1.00

  # Appliquer le discount
  technical_premium:
    type: MULTIPLY
    inputs:
      - base_premium
      - age_factor
      - brand_factor
      - density_factor
      - multi_vehicle_discount  # Nouveau!
```

### 8.3 Ajouter une catégorie de véhicule

Au lieu d'un facteur direct par marque, utiliser des catégories:

**tables/brand_categories.csv**:
```csv
brand,category
BMW,premium
Mercedes,premium
Audi,premium
Toyota,economy
Honda,economy
Ford,standard
```

**tables/category_factors.csv**:
```csv
category,factor
premium,1.20
standard,1.00
economy,0.90
```

**Modifiez le tarif**:
```yaml
nodes:
  # Lookup 1: Brand -> Category
  vehicle_category:
    type: LOOKUP
    table: brand_category_table
    key_node: brand
    mode: exact

  # Lookup 2: Category -> Factor
  brand_factor:
    type: LOOKUP
    table: category_factor_table
    key_node: vehicle_category
    mode: exact
```

### 8.4 Utiliser SWITCH pour plus de clarté

Remplacer les IF imbriqués par un SWITCH:

```yaml
nodes:
  # Catégorie de risque basée sur l'âge
  risk_category:
    type: SWITCH
    var_node: age_group
    cases:
      "young": 1.8
      "medium": 1.0
      "senior": 1.3
    default: 1.0

  # Déterminer le groupe d'âge
  age_group:
    type: SWITCH
    var_node: driver_age
    cases:
      # On pourrait utiliser des ranges ici si implémenté
    default: "medium"
```

Ou mieux, garder le LOOKUP pour l'âge qui supporte nativement les ranges.

## Étape 9: Tests automatisés

Créez `test_my_tariff.py`:

```python
import pytest
from engine.loader import TariffLoader
from engine.tables import load_range_table, load_exact_table
from engine.graph import TariffGraph
from decimal import Decimal

@pytest.fixture
def graph():
    """Setup du graphe pour les tests."""
    tables = {
        "age_table": load_range_table("tables/age_factors.csv"),
        "brand_table": load_exact_table(
            "tables/brand_factors.csv",
            key_column="brand",
            value_column="factor"
        )
    }
    loader = TariffLoader(tables=tables)
    nodes = loader.load("tariff.yaml")
    return TariffGraph(nodes)

def test_young_driver_pays_more(graph):
    """Jeunes conducteurs paient plus que les conducteurs expérimentés."""
    young = {"driver_age": 22, "brand": "Toyota", "density": 500}
    experienced = {"driver_age": 45, "brand": "Toyota", "density": 500}

    premium_young = graph.evaluate("total_premium", young)
    premium_experienced = graph.evaluate("total_premium", experienced)

    assert premium_young > premium_experienced

def test_premium_brands_cost_more(graph):
    """Marques premium coûtent plus cher."""
    bmw = {"driver_age": 35, "brand": "BMW", "density": 500}
    toyota = {"driver_age": 35, "brand": "Toyota", "density": 500}

    premium_bmw = graph.evaluate("total_premium", bmw)
    premium_toyota = graph.evaluate("total_premium", toyota)

    assert premium_bmw > premium_toyota

def test_urban_costs_more(graph):
    """Zone urbaine coûte plus cher."""
    urban = {"driver_age": 35, "brand": "Toyota", "density": 1500}
    rural = {"driver_age": 35, "brand": "Toyota", "density": 500}

    premium_urban = graph.evaluate("total_premium", urban)
    premium_rural = graph.evaluate("total_premium", rural)

    assert premium_urban > premium_rural

def test_exact_premium_calculation(graph):
    """Test de régression: prime exacte pour un cas connu."""
    context = {"driver_age": 45, "brand": "Toyota", "density": 500}
    premium = graph.evaluate("total_premium", context)

    # 500 (base) * 1.0 (age) * 0.95 (brand) * 1.0 (density) + 25 (fee)
    expected = Decimal("500.00")
    assert premium == expected

def test_all_brands_covered(graph):
    """Vérifier que toutes les marques sont dans la table."""
    brands = ["BMW", "Mercedes", "Audi", "Toyota", "Honda", "Ford"]
    context_base = {"driver_age": 35, "density": 500}

    for brand in brands:
        context = {**context_base, "brand": brand}
        premium = graph.evaluate("total_premium", context)
        assert premium > 0  # Doit calculer une prime
```

Exécutez:
```bash
pytest test_my_tariff.py -v
```

## Étape 10: Documentation

Créez `README.md` pour votre tarif:

```markdown
# My Motor Tariff - v2025_01

## Description

Tarif d'assurance automobile basé sur:
- Âge du conducteur (18-99 ans)
- Marque du véhicule
- Densité de population (zone urbaine/rurale)

## Structure

- `tariff.yaml`: Définition du tarif
- `tables/age_factors.csv`: Facteurs par tranche d'âge
- `tables/brand_factors.csv`: Facteurs par marque

## Formule

```
Technical Premium = Base Premium × Age Factor × Brand Factor × Density Factor
Total Premium = Technical Premium + Admin Fee
```

Où:
- Base Premium = 500 EUR
- Admin Fee = 25 EUR
- Age Factor: 1.0 à 1.8 selon l'âge
- Brand Factor: 0.93 à 1.20 selon la marque
- Density Factor: 1.0 (rural) ou 1.2 (urbain > 1000 hab/km²)

## Exemples

| Âge | Marque | Densité | Prime |
|-----|--------|---------|-------|
| 22  | BMW    | 1500    | 1267  |
| 45  | Toyota | 500     | 500   |
| 67  | Mercedes | 2000  | 1011  |

## Tests

```bash
pytest test_my_tariff.py
```

## Changelog

### v2025_01 (2025-01-01)
- Version initiale
```

## Conclusion

Félicitations! Vous avez créé un tarif automobile complet avec:

✅ Inputs multiples (âge, marque, densité)
✅ Tables de lookup (range et exact)
✅ Conditions (IF pour densité)
✅ Calculs intermédiaires clairs
✅ Arrondi final
✅ Tests automatisés
✅ Documentation

## Prochaines étapes

- Ajouter plus de facteurs (kilométrage, historique sinistres)
- Implémenter des garanties multiples
- Ajouter des franchises et plafonds
- Utiliser SWITCH pour des logiques plus complexes
- Intégrer avec une base de données pour les tables
- Déployer en production avec l'API REST

## Ressources

- [Guide utilisateur](user_guide.md)
- [Référence des nœuds](nodes_reference.md)
- [Guide de performance](performance_guide.md)
- [Exemples avancés](../examples/)
