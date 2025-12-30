"""
Module de gestion des tables de lookup pour le rating engine.

Ce module fournit des structures de données pour effectuer des recherches
rapides de valeurs basées sur des clés (lookups), avec support pour
les plages de valeurs et les correspondances exactes.
"""
import csv
from decimal import Decimal
from typing import Type, Any


class RangeTable:
    """
    Table de lookup basée sur des plages de valeurs.

    Permet de rechercher une valeur en fonction d'une plage numérique.
    Utile pour les facteurs dépendants de l'âge, du kilométrage, etc.

    Attributes:
        rows: Liste de dictionnaires {min, max, value}
        default: Valeur par défaut si aucune plage ne correspond

    Examples:
        >>> table = RangeTable([
        ...     {"min": 18, "max": 25, "value": Decimal("1.8")},
        ...     {"min": 26, "max": 65, "value": Decimal("1.0")},
        ... ])
        >>> table.lookup(22)
        Decimal('1.8')
        >>> table.lookup(40)
        Decimal('1.0')
    """

    def __init__(self, rows, default=None):
        """
        Initialise une table de plages.

        Args:
            rows: Liste de dict avec clés 'min', 'max', 'value'
            default: Valeur par défaut optionnelle
        """
        self.rows = rows
        self.default = default

    def lookup(self, value):
        """
        Recherche une valeur dans les plages définies.

        Args:
            value: Valeur numérique à rechercher

        Returns:
            Valeur correspondante (Decimal)

        Raises:
            KeyError: Si valeur hors de toutes les plages et pas de défaut
        """
        if value is None:
            if self.default is not None:
                return self.default
            raise KeyError("Missing value and no default defined")

        for r in self.rows:
            if r["min"] <= value <= r["max"]:
                return r["value"]

        raise KeyError(f"Value {value} outside all ranges")


def load_range_table(path: str, default=None):
    """
    Charge une table de plages depuis un fichier CSV.

    Le CSV doit contenir les colonnes: min, max, value

    Args:
        path: Chemin vers le fichier CSV
        default: Valeur par défaut optionnelle

    Returns:
        RangeTable initialisée

    Examples:
        >>> table = load_range_table("age_factors.csv")
    """
    rows = []
    with open(path) as f:
        reader = csv.DictReader(f)
        for r in reader:
            rows.append(
                {
                    "min": int(r["min"]),
                    "max": int(r["max"]),
                    "value": Decimal(str(r["value"])),
                }
            )
    return RangeTable(rows, default)


class ExactMatchTable:
    """
    Table de lookup basée sur des correspondances exactes.

    Permet de rechercher une valeur par clé exacte, avec support
    d'une valeur par défaut via la clé spéciale "__DEFAULT__".

    Attributes:
        mapping: Dictionnaire {clé -> valeur}
        key_type: Type de la clé (str, int, etc.)

    Examples:
        >>> table = ExactMatchTable({
        ...     "BMW": Decimal("1.2"),
        ...     "Audi": Decimal("1.1"),
        ...     "__DEFAULT__": Decimal("1.0"),
        ... })
        >>> table.lookup("BMW")
        Decimal('1.2')
        >>> table.lookup("Toyota")  # Utilise __DEFAULT__
        Decimal('1.0')
    """

    def __init__(
        self,
        mapping: dict,
        key_type: Type[Any] = str,
    ):
        """
        Initialise une table de correspondances exactes.

        Args:
            mapping: Dictionnaire {clé -> valeur}
            key_type: Type attendu pour les clés (défaut: str)
        """
        self.mapping = mapping
        self.key_type = key_type

    def lookup(self, key):
        """
        Recherche une valeur par clé exacte.

        Args:
            key: Clé à rechercher

        Returns:
            Valeur correspondante

        Raises:
            KeyError: Si clé introuvable et pas de __DEFAULT__
        """
        k = self.key_type(key)
        if k in self.mapping:
            return self.mapping[k]
        if "__DEFAULT__" in self.mapping:
            return self.mapping["__DEFAULT__"]
        raise KeyError(f"No matching row for {key}")


def load_exact_table(
    path: str,
    key_column: str = "key",
    value_column: str = "value",
    key_type: Type[Any] = str,
):
    """
    Charge une table de correspondances exactes depuis un fichier CSV.

    Args:
        path: Chemin vers le fichier CSV
        key_column: Nom de la colonne contenant les clés
        value_column: Nom de la colonne contenant les valeurs
        key_type: Type de conversion pour les clés (défaut: str)

    Returns:
        ExactMatchTable initialisée

    Examples:
        >>> table = load_exact_table("brands.csv", key_column="brand", value_column="factor")
        >>> # Avec clés entières
        >>> table = load_exact_table("zones.csv", key_column="zone_id", key_type=int)
    """
    mapping = {}
    with open(path) as f:
        reader = csv.DictReader(f)
        for row in reader:
            k = key_type(row[key_column])
            v = Decimal(str(row[value_column]))
            mapping[k] = v
    return ExactMatchTable(mapping, key_type=key_type)
