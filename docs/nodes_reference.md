# Référence des Nœuds - Rating Engine

Documentation complète de tous les types de nœuds disponibles.

## Table des matières

- [Nœuds de base](#nœuds-de-base)
  - [INPUT](#input)
  - [CONSTANT](#constant)
  - [ADD](#add)
  - [MULTIPLY](#multiply)
  - [LOOKUP](#lookup)
  - [IF](#if)
  - [ROUND](#round)
- [Nœuds avancés](#nœuds-avancés)
  - [SWITCH](#switch)
  - [COALESCE](#coalesce)
  - [MIN](#min)
  - [MAX](#max)
  - [ABS](#abs)

---

## Nœuds de base

### INPUT

**Description**: Variable d'entrée fournie dans le contexte d'évaluation.

**Paramètres**:
- `dtype` (obligatoire): Type de données (`decimal` ou `str`)

**YAML**:
```yaml
driver_age:
  type: INPUT
  dtype: decimal

brand:
  type: INPUT
  dtype: str
```

**Python**:
```python
from engine.nodes import InputNode

age_node = InputNode("driver_age", dtype="decimal")
brand_node = InputNode("brand", dtype="str")
```

**Évaluation**:
```python
context = {"driver_age": 30, "brand": "BMW"}
value = age_node.evaluate(context, {})  # Returns Decimal('30')
```

**Notes**:
- Les valeurs `decimal` sont automatiquement converties en `Decimal`
- Les valeurs `str` restent des strings
- Si la clé est absente du contexte, une erreur est levée
- Si la valeur est `None`, `None` est retourné

**Cas d'usage**: Tous les inputs utilisateur (âge, marque, etc.)

---

### CONSTANT

**Description**: Valeur fixe qui ne change jamais.

**Paramètres**:
- `value` (obligatoire): Valeur constante (nombre ou string)

**YAML**:
```yaml
base_premium:
  type: CONSTANT
  value: 500

currency:
  type: CONSTANT
  value: EUR
```

**Python**:
```python
from engine.nodes import ConstantNode
from decimal import Decimal

base = ConstantNode("base_premium", Decimal("500"))
```

**Évaluation**:
```python
value = base.evaluate(context, {})  # Returns Decimal('500')
```

**Notes**:
- Les valeurs numériques sont converties en `Decimal`
- Aucune dépendance (nœud leaf du graphe)
- Très performant (pas de calcul)

**Cas d'usage**: Prime de base, frais fixes, seuils, taux

---

### ADD

**Description**: Addition de plusieurs valeurs.

**Paramètres**:
- `inputs` (obligatoire): Liste des noms de nœuds à additionner

**YAML**:
```yaml
total:
  type: ADD
  inputs:
    - technical_premium
    - admin_fee
    - tax
```

**Python**:
```python
from engine.nodes import AddNode, ConstantNode
from decimal import Decimal

a = ConstantNode("a", Decimal("10"))
b = ConstantNode("b", Decimal("20"))
c = ConstantNode("c", Decimal("5"))
total = AddNode("total", [a, b, c])
```

**Évaluation**:
```python
# total = 10 + 20 + 5 = 35
value = total.evaluate(context, cache)  # Returns Decimal('35')
```

**Notes**:
- Accepte 1 input ou plus (minimum 1)
- Si un input est `None`, le résultat est `None`
- Opération associative: `(a + b) + c = a + (b + c)`

**Cas d'usage**: Somme de primes, total des frais, cumul de garanties

---

### MULTIPLY

**Description**: Multiplication de plusieurs valeurs.

**Paramètres**:
- `inputs` (obligatoire): Liste des noms de nœuds à multiplier

**YAML**:
```yaml
technical_premium:
  type: MULTIPLY
  inputs:
    - base_premium
    - age_factor
    - brand_factor
    - density_factor
```

**Python**:
```python
from engine.nodes import MultiplyNode, ConstantNode
from decimal import Decimal

base = ConstantNode("base", Decimal("100"))
factor1 = ConstantNode("f1", Decimal("1.2"))
factor2 = ConstantNode("f2", Decimal("0.95"))
result = MultiplyNode("result", [base, factor1, factor2])
```

**Évaluation**:
```python
# result = 100 * 1.2 * 0.95 = 114
value = result.evaluate(context, cache)  # Returns Decimal('114.0')
```

**Notes**:
- Accepte 1 input ou plus
- Si un input est `None`, le résultat est `None`
- Opération associative: `(a × b) × c = a × (b × c)`
- Précision Decimal préservée

**Cas d'usage**: Application de facteurs multiples, calcul de prime technique

---

### LOOKUP

**Description**: Recherche d'une valeur dans une table (range ou exact match).

**Paramètres**:
- `table` (obligatoire): Nom de la table (chargée avec le loader)
- `key_node` (obligatoire): Nom du nœud fournissant la clé
- `mode` (obligatoire): `"range"` ou `"exact"`

**YAML**:

```yaml
# Range lookup (âge dans plages)
age_factor:
  type: LOOKUP
  table: age_table
  key_node: driver_age
  mode: range

# Exact lookup (marque)
brand_factor:
  type: LOOKUP
  table: brand_table
  key_node: brand
  mode: exact
```

**Python**:
```python
from engine.nodes import LookupNode, InputNode
from engine.tables import RangeTable, ExactMatchTable
from decimal import Decimal

# Range table
age_table = RangeTable([
    {"min": 18, "max": 25, "value": Decimal("1.8")},
    {"min": 26, "max": 65, "value": Decimal("1.0")},
])

age_input = InputNode("driver_age")
age_factor = LookupNode("age_factor", age_table, age_input)

# Exact table
brand_table = ExactMatchTable({
    "BMW": Decimal("1.2"),
    "Toyota": Decimal("0.95"),
})

brand_input = InputNode("brand", dtype="str")
brand_factor = LookupNode("brand_factor", brand_table, brand_input)
```

**Évaluation**:
```python
context = {"driver_age": 22, "brand": "BMW"}
age_val = age_factor.evaluate(context, {})    # Decimal('1.8')
brand_val = brand_factor.evaluate(context, {})  # Decimal('1.2')
```

**Notes**:
- **Range mode**: Recherche binaire O(log n) pour performance
- **Exact mode**: Lookup O(1) dans un dictionnaire
- Si la clé n'est pas trouvée et qu'il n'y a pas de `default`, une erreur est levée
- Supporte les valeurs par défaut sur la table

**Cas d'usage**:
- Range: Facteurs d'âge, kilométrage, ancienneté
- Exact: Marques, zones, catégories

---

### IF

**Description**: Condition simple avec branche `then` et `else`.

**Paramètres**:
- `condition` (obligatoire): Expression de condition (ex: `"age > 25"`)
- `then` (obligatoire): Valeur si condition vraie
- `else` (obligatoire): Valeur si condition fausse

**Opérateurs supportés**: `>`, `<`, `>=`, `<=`

**YAML**:
```yaml
young_driver_surcharge:
  type: IF
  condition: driver_age < 26
  then: 50
  else: 0

urban_factor:
  type: IF
  condition: density >= 1000
  then: 1.20
  else: 1.00
```

**Python**:
```python
from engine.nodes import IfNode, InputNode
from decimal import Decimal

age = InputNode("driver_age")
surcharge = IfNode(
    "surcharge",
    age,
    ">",
    Decimal("65"),
    then_value=Decimal("100"),
    else_value=Decimal("0")
)
```

**Évaluation**:
```python
context = {"driver_age": 70}
value = surcharge.evaluate(context, {})  # Decimal('100')

context = {"driver_age": 45}
value = surcharge.evaluate(context, {})  # Decimal('0')
```

**Notes**:
- Évalue la condition sur la valeur du nœud référencé
- Les valeurs `then` et `else` peuvent être des nœuds ou des constantes
- Si la valeur testée est `None`, une erreur est levée

**Cas d'usage**: Surcharges conditionnelles, facteurs basés sur seuils

**Alternative**: Pour des conditions multiples, préférer [SWITCH](#switch)

---

### ROUND

**Description**: Arrondit une valeur à un nombre de décimales donné.

**Paramètres**:
- `input` (obligatoire): Nom du nœud à arrondir
- `decimals` (optionnel): Nombre de décimales (défaut: 2)
- `mode` (optionnel): Mode d'arrondi (défaut: `"HALF_UP"`)

**Modes d'arrondi**:
- `HALF_UP`: Arrondi classique (0.5 → 1)
- `HALF_EVEN`: Arrondi bancaire (0.5 → pair le plus proche)

**YAML**:
```yaml
total_premium:
  type: ROUND
  input: raw_premium
  decimals: 2
  mode: HALF_UP

percentage:
  type: ROUND
  input: raw_percentage
  decimals: 4
  mode: HALF_EVEN
```

**Python**:
```python
from engine.nodes import RoundNode, ConstantNode
from decimal import Decimal

raw = ConstantNode("raw", Decimal("123.456789"))
rounded = RoundNode("rounded", raw, decimals=2, mode="HALF_UP")
```

**Évaluation**:
```python
value = rounded.evaluate({}, {})  # Decimal('123.46')
```

**Notes**:
- Utilise `decimal.ROUND_HALF_UP` ou `decimal.ROUND_HALF_EVEN`
- Préserve le type `Decimal`
- Si l'input est `None`, retourne `None`

**Cas d'usage**: Arrondis finaux de primes, pourcentages

---

## Nœuds avancés

### SWITCH

**Description**: Branchement multiple (équivalent switch/case). Évalue une variable et retourne la valeur correspondante dans les cas définis.

**Paramètres**:
- `var_node` (obligatoire): Nom du nœud fournissant la variable à tester
- `cases` (obligatoire): Dictionnaire {valeur: résultat}
- `default` (optionnel): Valeur par défaut si aucun cas ne correspond

**YAML**:
```yaml
# Switch sur catégorie de véhicule
category_factor:
  type: SWITCH
  var_node: vehicle_category
  cases:
    "economy": 0.90
    "standard": 1.00
    "premium": 1.20
    "luxury": 1.50
  default: 1.00

# Switch sur zone géographique
zone_coefficient:
  type: SWITCH
  var_node: zone
  cases:
    1: 0.75
    2: 0.85
    3: 1.00
    4: 1.15
    5: 1.30
  default: 1.00
```

**Python**:
```python
from engine.nodes import SwitchNode, InputNode
from decimal import Decimal

category = InputNode("vehicle_category", dtype="str")
factor = SwitchNode(
    "category_factor",
    category,
    cases={
        "economy": Decimal("0.90"),
        "standard": Decimal("1.00"),
        "premium": Decimal("1.20"),
    },
    default=Decimal("1.00")
)
```

**Évaluation**:
```python
context = {"vehicle_category": "premium"}
value = factor.evaluate(context, {})  # Decimal('1.20')

context = {"vehicle_category": "unknown"}
value = factor.evaluate(context, {})  # Decimal('1.00') (default)
```

**Notes**:
- Plus lisible que des IF imbriqués pour 3+ cas
- Les clés peuvent être des strings ou des nombres
- Si aucun cas ne correspond et qu'il n'y a pas de `default`, retourne `None`
- Les valeurs peuvent être des constantes ou des noms de nœuds (pas encore implémenté)

**Cas d'usage**:
- Facteurs par catégorie
- Coefficients par zone
- Tarifs par produit

**Voir aussi**: [Guide des nouveaux nœuds](new_nodes_guide.md#switchnode)

---

### COALESCE

**Description**: Retourne la première valeur non-nulle parmi une liste d'inputs. Équivalent à `??` ou `COALESCE` en SQL.

**Paramètres**:
- `inputs` (obligatoire): Liste des noms de nœuds à tester

**YAML**:
```yaml
# Utiliser la marque spécifique, sinon la catégorie générique
effective_factor:
  type: COALESCE
  inputs:
    - specific_brand_factor
    - category_factor
    - default_factor

# Choisir la première valeur disponible
preferred_value:
  type: COALESCE
  inputs:
    - user_provided_value
    - calculated_value
    - fallback_constant
```

**Python**:
```python
from engine.nodes import CoalesceNode, InputNode, ConstantNode
from decimal import Decimal

input1 = InputNode("optional_value")
input2 = InputNode("backup_value")
default = ConstantNode("default", Decimal("100"))

result = CoalesceNode("result", [input1, input2, default])
```

**Évaluation**:
```python
# Cas 1: Premier input disponible
context = {"optional_value": 50, "backup_value": 75}
value = result.evaluate(context, {})  # Decimal('50')

# Cas 2: Premier input None, second disponible
context = {"optional_value": None, "backup_value": 75}
value = result.evaluate(context, {})  # Decimal('75')

# Cas 3: Tous None, utilise la constante
context = {"optional_value": None, "backup_value": None}
value = result.evaluate(context, {})  # Decimal('100')
```

**Notes**:
- Parcourt les inputs dans l'ordre jusqu'à trouver une valeur non-None
- Si tous les inputs sont None, retourne None
- Minimum 1 input requis
- Court-circuite: n'évalue que les nœuds nécessaires

**Cas d'usage**:
- Valeurs par défaut conditionnelles
- Fallback sur des données manquantes
- Priorité de sources de données

**Voir aussi**: [Guide des nouveaux nœuds](new_nodes_guide.md#coalescenode)

---

### MIN

**Description**: Retourne la valeur minimum parmi plusieurs inputs.

**Paramètres**:
- `inputs` (obligatoire): Liste des noms de nœuds à comparer

**YAML**:
```yaml
# Plafond de prime
final_premium:
  type: MIN
  inputs:
    - calculated_premium
    - max_allowed_premium

# Minimum de plusieurs facteurs
min_factor:
  type: MIN
  inputs:
    - age_factor
    - experience_factor
    - claims_factor
```

**Python**:
```python
from engine.nodes import MinNode, ConstantNode
from decimal import Decimal

a = ConstantNode("a", Decimal("100"))
b = ConstantNode("b", Decimal("75"))
c = ConstantNode("c", Decimal("120"))
minimum = MinNode("min", [a, b, c])
```

**Évaluation**:
```python
value = minimum.evaluate({}, {})  # Decimal('75')
```

**Notes**:
- Les valeurs None sont ignorées (sauf si toutes None)
- Minimum 2 inputs requis
- Si tous les inputs sont None, retourne None
- Fonctionne avec Decimal, int, float (convertis en Decimal)

**Cas d'usage**:
- Plafonds de prime
- Minimum de facteurs
- Bornes inférieures

**Voir aussi**: [Guide des nouveaux nœuds](new_nodes_guide.md#minnode)

---

### MAX

**Description**: Retourne la valeur maximum parmi plusieurs inputs.

**Paramètres**:
- `inputs` (obligatoire): Liste des noms de nœuds à comparer

**YAML**:
```yaml
# Plancher de prime
final_premium:
  type: MAX
  inputs:
    - calculated_premium
    - min_required_premium

# Maximum de plusieurs seuils
threshold:
  type: MAX
  inputs:
    - regulatory_minimum
    - company_minimum
    - product_minimum
```

**Python**:
```python
from engine.nodes import MaxNode, ConstantNode
from decimal import Decimal

a = ConstantNode("a", Decimal("100"))
b = ConstantNode("b", Decimal("75"))
c = ConstantNode("c", Decimal("120"))
maximum = MaxNode("max", [a, b, c])
```

**Évaluation**:
```python
value = maximum.evaluate({}, {})  # Decimal('120')
```

**Notes**:
- Les valeurs None sont ignorées (sauf si toutes None)
- Minimum 2 inputs requis
- Si tous les inputs sont None, retourne None
- Fonctionne avec Decimal, int, float (convertis en Decimal)

**Cas d'usage**:
- Planchers de prime
- Maximum de facteurs
- Bornes supérieures

**Voir aussi**: [Guide des nouveaux nœuds](new_nodes_guide.md#maxnode)

---

### ABS

**Description**: Retourne la valeur absolue d'un input.

**Paramètres**:
- `input` (obligatoire): Nom du nœud dont prendre la valeur absolue

**YAML**:
```yaml
# Valeur absolue d'un ajustement
adjustment_amount:
  type: ABS
  input: raw_adjustment

# Distance absolue
distance:
  type: ABS
  input: difference
```

**Python**:
```python
from engine.nodes import AbsNode, ConstantNode
from decimal import Decimal

negative = ConstantNode("neg", Decimal("-123.45"))
absolute = AbsNode("abs", negative)
```

**Évaluation**:
```python
value = absolute.evaluate({}, {})  # Decimal('123.45')
```

**Notes**:
- Fonctionne avec Decimal, int, float (convertis en Decimal)
- Si l'input est None, retourne None
- Préserve la précision Decimal

**Cas d'usage**:
- Valeurs absolues d'ajustements
- Distances ou écarts
- Montants sans signe

**Voir aussi**: [Guide des nouveaux nœuds](new_nodes_guide.md#absnode)

---

## Résumé rapide

| Nœud | Type | Inputs | Output | Usage |
|------|------|--------|--------|-------|
| INPUT | Basique | 0 | Variable | Variables d'entrée |
| CONSTANT | Basique | 0 | Fixe | Valeurs fixes |
| ADD | Basique | N | Somme | a + b + c + ... |
| MULTIPLY | Basique | N | Produit | a × b × c × ... |
| LOOKUP | Basique | 1 | Table | Facteurs tabulés |
| IF | Basique | 1 | Conditionnel | Si...alors...sinon |
| ROUND | Basique | 1 | Arrondi | Arrondir résultat |
| SWITCH | Avancé | 1 | Multi-cas | Switch/case |
| COALESCE | Avancé | N | Premier non-null | Valeur par défaut |
| MIN | Avancé | N | Minimum | min(a, b, c) |
| MAX | Avancé | N | Maximum | max(a, b, c) |
| ABS | Avancé | 1 | Valeur absolue | \|x\| |

## Pattern de conception

### Calcul de prime typique

```yaml
nodes:
  # 1. Inputs
  age: {type: INPUT, dtype: decimal}
  brand: {type: INPUT, dtype: str}

  # 2. Constants
  base_premium: {type: CONSTANT, value: 500}
  fee: {type: CONSTANT, value: 25}

  # 3. Factors
  age_factor: {type: LOOKUP, table: age_table, key_node: age, mode: range}
  brand_factor: {type: LOOKUP, table: brand_table, key_node: brand, mode: exact}

  # 4. Calculations
  technical_premium: {type: MULTIPLY, inputs: [base_premium, age_factor, brand_factor]}
  raw_total: {type: ADD, inputs: [technical_premium, fee]}

  # 5. Result
  total_premium: {type: ROUND, input: raw_total, decimals: 2, mode: HALF_UP}
```

### Avec plafonds et planchers

```yaml
nodes:
  # ... (calculs ci-dessus)

  min_premium: {type: CONSTANT, value: 100}
  max_premium: {type: CONSTANT, value: 5000}

  # Appliquer bornes
  capped_premium: {type: MIN, inputs: [raw_total, max_premium]}
  bounded_premium: {type: MAX, inputs: [capped_premium, min_premium]}

  # Arrondir
  total_premium: {type: ROUND, input: bounded_premium, decimals: 2}
```

### Avec valeurs par défaut

```yaml
nodes:
  # Essayer plusieurs sources
  effective_value:
    type: COALESCE
    inputs:
      - user_provided_value
      - calculated_value
      - default_constant

  # Utiliser dans calcul
  premium:
    type: MULTIPLY
    inputs: [base, effective_value]
```

---

## Prochaines fonctionnalités

Nœuds envisagés pour futures versions:
- **DateNode**: Calculs sur dates (différence, extraction année/mois)
- **StringNode**: Manipulation de strings (concat, format, substring)
- **ListNode**: Opérations sur listes (map, filter, sum)
- **RegexNode**: Pattern matching
- **ModuloNode**: Opération modulo
- **PowerNode**: Puissance
- **LogNode**: Logarithme

Proposez vos besoins via GitHub Issues!
