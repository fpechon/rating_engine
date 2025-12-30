# Guide des nouveaux types de nœuds (Phase 2)

Ce document décrit les nouveaux types de nœuds ajoutés au rating engine pour enrichir les capacités de calcul de tarifs.

## Vue d'ensemble

Les nouveaux nœuds ajoutés sont :

- **SwitchNode** : Branchement multiple (alternative aux IfNode imbriqués)
- **CoalesceNode** : Retourne la première valeur non-nulle
- **MinNode / MaxNode** : Comparaisons min/max sur plusieurs valeurs
- **AbsNode** : Valeur absolue

Ces nœuds permettent d'écrire des tarifs plus expressifs et plus maintenables.

---

## SwitchNode - Branchement multiple

### Description

Le `SwitchNode` permet de mapper une valeur d'entrée vers différents résultats en fonction de cas multiples. C'est l'équivalent d'un `switch/case` en programmation, beaucoup plus lisible que des `IfNode` imbriqués.

### Syntaxe YAML

```yaml
node_name:
  type: SWITCH
  var_node: nom_du_noeud_source
  cases:
    valeur1: resultat1
    valeur2: resultat2
    valeur3: resultat3
  default: valeur_par_defaut  # optionnel
```

### Paramètres

- `var_node` : Nom du nœud dont on teste la valeur
- `cases` : Dictionnaire {valeur_test → valeur_retour}
- `default` : Valeur par défaut si aucun cas ne correspond (optionnel)

### Comportement

1. Évalue le `var_node`
2. Cherche la valeur dans le dictionnaire `cases`
3. Si trouvée : retourne la valeur correspondante
4. Si non trouvée et `default` défini : retourne `default`
5. Si non trouvée et pas de `default` : lève une `KeyError`

### Exemples

#### Exemple 1 : Facteur par région

```yaml
nodes:
  # Input : région du conducteur
  region:
    type: INPUT
    dtype: str

  # Facteur dépendant de la région
  region_factor:
    type: SWITCH
    var_node: region
    cases:
      Paris: 1.5
      Lyon: 1.3
      Marseille: 1.2
      Bordeaux: 1.1
    default: 1.0  # Toutes les autres régions

  base_premium:
    type: CONSTANT
    value: 500

  premium:
    type: MULTIPLY
    inputs: [base_premium, region_factor]
```

**Résultats :**
- Si `region = "Paris"` → `premium = 750` (500 × 1.5)
- Si `region = "Bordeaux"` → `premium = 550` (500 × 1.1)
- Si `region = "Toulouse"` → `premium = 500` (500 × 1.0, utilise default)

#### Exemple 2 : Tarification par profil

```yaml
nodes:
  driver_profile:
    type: INPUT
    dtype: str

  profile_premium:
    type: SWITCH
    var_node: driver_profile
    cases:
      young_driver: 1200
      standard_driver: 800
      experienced_driver: 600
      senior_driver: 700
```

**Note :** Sans `default`, si le profil n'est pas reconnu, une erreur sera levée.

#### Exemple 3 : Switch avec clés numériques

```yaml
nodes:
  zone_id:
    type: INPUT

  zone_factor:
    type: SWITCH
    var_node: zone_id
    cases:
      1: 1.3
      2: 1.2
      3: 1.1
      4: 1.0
    default: 1.0
```

---

## CoalesceNode - Première valeur non-nulle

### Description

Le `CoalesceNode` évalue plusieurs nœuds dans l'ordre et retourne la première valeur non-nulle. Utile pour gérer des fallbacks en cascade ou des valeurs optionnelles avec défauts.

### Syntaxe YAML

```yaml
node_name:
  type: COALESCE
  inputs: [noeud1, noeud2, noeud3, ...]
```

### Paramètres

- `inputs` : Liste de noms de nœuds, évalués dans l'ordre

### Comportement

1. Évalue chaque nœud dans l'ordre de la liste
2. Retourne la première valeur non-`None`
3. Si tous sont `None`, retourne `None`

### Exemples

#### Exemple 1 : Discount avec fallback

```yaml
nodes:
  # Discount optionnel fourni par l'utilisateur
  customer_discount:
    type: INPUT

  # Discount par défaut
  default_discount:
    type: CONSTANT
    value: 0

  # Utilise customer_discount si fourni, sinon 0
  final_discount:
    type: COALESCE
    inputs: [customer_discount, default_discount]

  base_premium:
    type: CONSTANT
    value: 1000

  discounted_premium:
    type: MULTIPLY
    inputs: [base_premium, final_discount]
```

**Résultats :**
- Si `customer_discount` est fourni (ex: 0.9) → `discounted_premium = 900`
- Si `customer_discount` est absent ou `None` → utilise 0 → `discounted_premium = 0`

#### Exemple 2 : Cascade de priorités

```yaml
nodes:
  special_rate:
    type: INPUT  # Taux spécial négocié

  loyalty_rate:
    type: INPUT  # Taux fidélité

  standard_rate:
    type: CONSTANT
    value: 1.0

  # Ordre de priorité : spécial > loyalty > standard
  final_rate:
    type: COALESCE
    inputs: [special_rate, loyalty_rate, standard_rate]
```

**Résultats :**
- Si `special_rate = 0.7` (fourni) → `final_rate = 0.7`
- Si `special_rate = None` et `loyalty_rate = 0.85` → `final_rate = 0.85`
- Si les deux sont `None` → `final_rate = 1.0`

---

## MinNode / MaxNode - Comparaisons

### Description

`MinNode` et `MaxNode` retournent respectivement le minimum ou le maximum parmi plusieurs valeurs.

### Syntaxe YAML

```yaml
# Minimum
min_node:
  type: MIN
  inputs: [noeud1, noeud2, noeud3, ...]

# Maximum
max_node:
  type: MAX
  inputs: [noeud1, noeud2, noeud3, ...]
```

### Paramètres

- `inputs` : Liste de noms de nœuds à comparer

### Comportement

- Évalue tous les nœuds d'entrée
- Ignore les valeurs `None`
- Retourne `None` si tous les inputs sont `None`
- Sinon retourne le min/max des valeurs non-nulles

### Exemples

#### Exemple 1 : Prime minimale garantie

```yaml
nodes:
  calculated_premium:
    type: MULTIPLY
    inputs: [base, factor1, factor2]

  minimum_premium:
    type: CONSTANT
    value: 300

  # La prime ne peut pas être inférieure à 300
  final_premium:
    type: MAX
    inputs: [calculated_premium, minimum_premium]
```

**Résultat :**
- Si `calculated_premium = 250` → `final_premium = 300` (applique le minimum)
- Si `calculated_premium = 450` → `final_premium = 450`

#### Exemple 2 : Choix du meilleur prix

```yaml
nodes:
  price_option1:
    type: CONSTANT
    value: 550

  price_option2:
    type: CONSTANT
    value: 480

  price_option3:
    type: CONSTANT
    value: 520

  # Prend le prix le plus bas
  best_price:
    type: MIN
    inputs: [price_option1, price_option2, price_option3]
```

**Résultat :** `best_price = 480`

#### Exemple 3 : Franchise maximale

```yaml
nodes:
  base_deductible:
    type: CONSTANT
    value: 500

  risk_deductible:
    type: MULTIPLY
    inputs: [risk_factor, base_deductible]

  # La franchise est au moins 500, mais peut être plus élevée selon le risque
  final_deductible:
    type: MAX
    inputs: [base_deductible, risk_deductible]
```

#### Exemple 4 : Gestion des valeurs None

```yaml
nodes:
  optional_fee1:
    type: INPUT  # Peut être None

  optional_fee2:
    type: INPUT  # Peut être None

  base_fee:
    type: CONSTANT
    value: 25

  # Prend le max, mais ignore les None
  final_fee:
    type: MAX
    inputs: [optional_fee1, optional_fee2, base_fee]
```

**Résultats :**
- Si `optional_fee1 = 30`, `optional_fee2 = None` → `final_fee = 30`
- Si les deux sont `None` → `final_fee = 25` (base_fee)

---

## AbsNode - Valeur absolue

### Description

`AbsNode` retourne la valeur absolue de son entrée (rend les nombres négatifs positifs).

### Syntaxe YAML

```yaml
node_name:
  type: ABS
  input: noeud_source
```

### Paramètres

- `input` : Nom du nœud dont on veut la valeur absolue

### Comportement

- Évalue le nœud d'entrée
- Si la valeur est `None`, retourne `None`
- Sinon retourne `|valeur|` (valeur absolue)

### Exemples

#### Exemple 1 : Ajustement en valeur absolue

```yaml
nodes:
  reference_premium:
    type: CONSTANT
    value: 500

  actual_premium:
    type: INPUT

  # Différence (peut être négative)
  difference:
    type: ADD
    inputs: [actual_premium, negative_reference]

  negative_reference:
    type: MULTIPLY
    inputs: [reference_premium, minus_one]

  minus_one:
    type: CONSTANT
    value: -1

  # Écart absolu
  absolute_difference:
    type: ABS
    input: difference
```

**Résultats :**
- Si `actual_premium = 450` → `difference = -50` → `absolute_difference = 50`
- Si `actual_premium = 600` → `difference = 100` → `absolute_difference = 100`

#### Exemple 2 : Pénalité pour écart

```yaml
nodes:
  target_ratio:
    type: CONSTANT
    value: 1.0

  actual_ratio:
    type: INPUT

  # Écart au ratio cible
  ratio_deviation:
    type: ADD
    inputs: [actual_ratio, negative_target]

  negative_target:
    type: MULTIPLY
    inputs: [target_ratio, minus_one]

  minus_one:
    type: CONSTANT
    value: -1

  # Écart absolu
  abs_deviation:
    type: ABS
    input: ratio_deviation

  # Pénalité = 10% par 0.1 d'écart
  penalty_factor:
    type: MULTIPLY
    inputs: [abs_deviation, penalty_rate]

  penalty_rate:
    type: CONSTANT
    value: 0.1
```

---

## Comparaison : SwitchNode vs IfNode imbriqués

### Avec IfNode (ancien style)

```yaml
nodes:
  region:
    type: INPUT
    dtype: str

  # Très verbeux et difficile à maintenir !
  region_factor:
    type: IF
    condition: "region == 'Paris'"
    then: 1.5
    else_node: check_lyon

  check_lyon:
    type: IF
    condition: "region == 'Lyon'"
    then: 1.3
    else_node: check_marseille

  check_marseille:
    type: IF
    condition: "region == 'Marseille'"
    then: 1.2
    else: 1.0
```

**Problèmes :**
- Très verbeux (3 nœuds pour 3 cas)
- Difficile à lire et maintenir
- Risque d'erreur lors de l'ajout de cas

### Avec SwitchNode (nouveau style)

```yaml
nodes:
  region:
    type: INPUT
    dtype: str

  # Clair et concis !
  region_factor:
    type: SWITCH
    var_node: region
    cases:
      Paris: 1.5
      Lyon: 1.3
      Marseille: 1.2
    default: 1.0
```

**Avantages :**
- Un seul nœud
- Très lisible
- Facile d'ajouter/modifier des cas
- Pas de risque d'oubli de cas

---

## Cas d'usage avancés

### Exemple complet : Tarification multi-critères

```yaml
nodes:
  # Inputs
  region:
    type: INPUT
    dtype: str

  driver_age:
    type: INPUT

  vehicle_value:
    type: INPUT

  optional_discount:
    type: INPUT  # Peut être None

  # Base premium
  base_premium:
    type: CONSTANT
    value: 500

  # Facteur région (SWITCH)
  region_factor:
    type: SWITCH
    var_node: region
    cases:
      Paris: 1.5
      Lyon: 1.3
      Marseille: 1.2
    default: 1.0

  # Facteur âge (lookup range comme avant)
  age_factor:
    type: LOOKUP
    table: age_table
    key_node: driver_age

  # Prime calculée
  calculated_premium:
    type: MULTIPLY
    inputs: [base_premium, region_factor, age_factor]

  # Prime minimum garantie (MAX)
  minimum_premium:
    type: CONSTANT
    value: 300

  premium_with_minimum:
    type: MAX
    inputs: [calculated_premium, minimum_premium]

  # Discount avec fallback (COALESCE)
  default_discount:
    type: CONSTANT
    value: 1.0  # Pas de discount par défaut

  final_discount:
    type: COALESCE
    inputs: [optional_discount, default_discount]

  # Prime finale
  final_premium:
    type: MULTIPLY
    inputs: [premium_with_minimum, final_discount]

  # Arrondi à 2 décimales
  rounded_premium:
    type: ROUND
    input: final_premium
    decimals: 2
    mode: HALF_UP
```

### Exemple : Calcul de marge avec tolérance

```yaml
nodes:
  target_margin:
    type: CONSTANT
    value: 0.20  # 20% de marge cible

  actual_margin:
    type: INPUT

  # Écart à la cible
  margin_difference:
    type: ADD
    inputs: [actual_margin, negative_target]

  negative_target:
    type: MULTIPLY
    inputs: [target_margin, minus_one]

  minus_one:
    type: CONSTANT
    value: -1

  # Écart absolu
  abs_margin_difference:
    type: ABS
    input: margin_difference

  # Tolérance acceptable
  margin_tolerance:
    type: CONSTANT
    value: 0.05  # 5%

  # Pénalité si hors tolérance
  excess_deviation:
    type: ADD
    inputs: [abs_margin_difference, negative_tolerance]

  negative_tolerance:
    type: MULTIPLY
    inputs: [margin_tolerance, minus_one]

  # Pénalité uniquement si positif (dépasse la tolérance)
  penalty_base:
    type: MAX
    inputs: [excess_deviation, zero]

  zero:
    type: CONSTANT
    value: 0
```

---

## Bonnes pratiques

### Quand utiliser SwitchNode

✅ **À utiliser quand :**
- Vous avez 3+ cas à gérer
- Les cas sont des valeurs exactes (strings, nombres)
- Vous voulez une valeur par défaut simple

❌ **Ne PAS utiliser quand :**
- Vous avez seulement 2 cas → utilisez `IfNode`
- Vous avez besoin de conditions complexes (`age > 25 AND region == 'Paris'`)
- Les cas sont des ranges → utilisez `LookupNode` avec `RangeTable`

### Quand utiliser CoalesceNode

✅ **À utiliser quand :**
- Vous avez des inputs optionnels avec des fallbacks
- Vous voulez gérer des priorités en cascade
- Vous avez plusieurs sources possibles pour une même valeur

### Quand utiliser MinNode / MaxNode

✅ **À utiliser quand :**
- Vous voulez appliquer un plancher/plafond
- Vous devez choisir entre plusieurs options de prix
- Vous gérez des limites (franchises, garanties)

### Quand utiliser AbsNode

✅ **À utiliser quand :**
- Vous calculez des écarts ou des différences
- La direction du changement n'a pas d'importance
- Vous avez besoin de mesurer une distance/magnitude

---

## Migration depuis l'ancien style

Si vous avez des tarifs existants avec des `IfNode` imbriqués, voici comment migrer :

### Avant

```yaml
is_paris:
  type: IF
  condition: "region == 'Paris'"
  then: 1.5
  else_node: is_lyon

is_lyon:
  type: IF
  condition: "region == 'Lyon'"
  then: 1.3
  else: 1.0
```

### Après

```yaml
region_factor:
  type: SWITCH
  var_node: region
  cases:
    Paris: 1.5
    Lyon: 1.3
  default: 1.0
```

**Avantages :**
- 1 nœud au lieu de 2+
- Plus facile à modifier
- Performance identique (ou meilleure)

---

## Limitations et notes

### SwitchNode

- Les clés du dictionnaire `cases` doivent être exactes (pas de patterns)
- Pour des ranges de valeurs, utilisez plutôt `LookupNode` avec `RangeTable`
- Les valeurs sont automatiquement converties en `Decimal`

### CoalesceNode

- Évalue tous les nœuds dans l'ordre, même si le premier est non-null
- Pour éviter des évaluations inutiles, mettez les sources les plus probables en premier

### MinNode / MaxNode

- Ignorent les valeurs `None` (comportement pratique)
- Si vous voulez traiter `None` comme 0, utilisez `CoalesceNode` d'abord :

```yaml
safe_value:
  type: COALESCE
  inputs: [maybe_null_value, zero]

max_value:
  type: MAX
  inputs: [safe_value, other_value]
```

### AbsNode

- Ne gère que les valeurs numériques
- Préserve la précision décimale

---

## Support et questions

Pour toute question ou suggestion d'amélioration :
- Consultez les tests dans `tests/test_new_nodes.py`
- Lisez les exemples dans `tests/test_loader_new_nodes.py`
- Référez-vous à la documentation des nœuds dans `engine/nodes.py`
