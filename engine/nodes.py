"""
Module de définition des nœuds pour le graphe de tarification.

Ce module contient tous les types de nœuds utilisés pour construire
un graphe de calcul de prime d'assurance. Chaque nœud représente
une opération ou une valeur dans le calcul.
"""

import operator
from abc import ABC, abstractmethod
from decimal import ROUND_HALF_EVEN, ROUND_HALF_UP, Decimal
from typing import Callable, Optional, Union

# Opérateurs de comparaison supportés pour les conditions
OPS = {
    "<": operator.lt,
    "<=": operator.le,
    ">": operator.gt,
    ">=": operator.ge,
}

# Modes d'arrondi supportés
ROUNDING_MODES = {
    "HALF_UP": ROUND_HALF_UP,
    "HALF_EVEN": ROUND_HALF_EVEN,
}

# Constantes pour les opérations de réduction
ZERO = Decimal("0")
ONE = Decimal("1")


def to_decimal(value) -> Optional[Decimal]:
    """
    Convertit une valeur en Decimal de manière sécurisée.

    Args:
        value: Valeur à convertir (int, float, str, Decimal ou None)

    Returns:
        Decimal ou None si la valeur d'entrée est None

    Examples:
        >>> to_decimal(42)
        Decimal('42')
        >>> to_decimal("123.45")
        Decimal('123.45')
        >>> to_decimal(None)
        None
    """
    if value is None:
        return None
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


class Node(ABC):
    """
    Classe abstraite de base pour tous les nœuds du graphe de tarification.

    Un nœud représente une opération ou une valeur dans le calcul de la prime.
    Chaque nœud a un nom unique et peut dépendre d'autres nœuds.

    Attributes:
        name: Nom unique du nœud dans le graphe
    """

    def __init__(self, name: str):
        """
        Initialise un nœud.

        Args:
            name: Nom unique du nœud
        """
        self.name = name

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({self.name})"

    @abstractmethod
    def dependencies(self) -> list[str]:
        """
        Retourne la liste des noms de nœuds dont ce nœud dépend.

        Returns:
            Liste des noms de nœuds dépendants
        """
        pass

    @abstractmethod
    def evaluate(self, context: dict, cache: dict) -> Optional[Decimal]:
        """
        Évalue le nœud et retourne sa valeur.

        Args:
            context: Dictionnaire des valeurs d'input
            cache: Cache des valeurs déjà évaluées

        Returns:
            Valeur calculée ou None

        Raises:
            KeyError: Si une dépendance manque
            ValueError: Si une valeur est invalide
        """
        pass


class ConstantNode(Node):
    """
    Nœud représentant une constante.

    Attributes:
        value: Valeur constante (Decimal)

    Examples:
        >>> node = ConstantNode("base_premium", Decimal("500"))
        >>> node.evaluate({}, {})
        Decimal('500')
    """

    def __init__(self, name: str, value: Decimal):
        """
        Initialise un nœud constant.

        Args:
            name: Nom du nœud
            value: Valeur constante
        """
        super().__init__(name)
        self.value = value

    def dependencies(self):
        """Pas de dépendances pour une constante."""
        return []

    def evaluate(self, context, cache):
        """Retourne la valeur constante."""
        return self.value


class InputNode(Node):
    """
    Nœud feuille représentant une valeur fournie au moment de l'évaluation.

    Ce nœud extrait une valeur du contexte d'évaluation. Tous les autres
    nœuds doivent dépendre de nœuds, jamais directement du contexte.

    Attributes:
        dtype: Type de données attendu (Decimal, str, etc.)

    Examples:
        >>> node = InputNode("driver_age")
        >>> node.evaluate({"driver_age": 42}, {})
        Decimal('42')
    """

    def __init__(self, name: str, dtype=Decimal):
        """
        Initialise un nœud d'input.

        Args:
            name: Nom du nœud (doit correspondre à une clé du contexte)
            dtype: Type de données attendu (défaut: Decimal)
        """
        super().__init__(name)
        self.dtype = dtype

    def dependencies(self):
        """Pas de dépendances pour un input."""
        return []

    def evaluate(self, context, cache):
        """
        Extrait et convertit la valeur du contexte.

        Raises:
            KeyError: Si la variable n'est pas dans le contexte
        """
        if self.name not in context:
            raise KeyError(f"Missing input variable: {self.name}")
        value = context[self.name]
        if value is None:
            return None

        if self.dtype is Decimal:
            return to_decimal(value)
        return value


class LookupNode(Node):
    """
    Nœud effectuant une recherche dans une table.

    Attributes:
        table: Table de lookup (RangeTable ou ExactMatchTable)
        key_node: Nœud fournissant la clé de recherche

    Examples:
        >>> table = RangeTable([{"min": 18, "max": 25, "value": Decimal("1.8")}])
        >>> age_node = InputNode("age")
        >>> lookup = LookupNode("age_factor", table, age_node)
    """

    def __init__(self, name, table, key_node):
        """
        Initialise un nœud de lookup.

        Args:
            name: Nom du nœud
            table: Table de lookup
            key_node: Nœud fournissant la clé

        Raises:
            ValueError: Si key_node est None
        """
        super().__init__(name)
        self.table = table
        if key_node is None:
            raise ValueError("LookupNode requires a key_node")
        self.key_node = key_node

    def dependencies(self):
        """Dépend du nœud fournissant la clé."""
        return [self.key_node.name]

    def evaluate(self, context, cache):
        """Effectue la recherche dans la table."""
        value = cache[self.key_node.name]
        return self.table.lookup(value)


class ReduceNode(Node):
    """
    Nœud d'agrégation générique appliquant une opération binaire.

    Ce nœud applique une opération de réduction (comme addition ou
    multiplication) sur une liste de nœuds d'entrée.

    Attributes:
        inputs: Liste des nœuds d'entrée
        op: Opération binaire (callable)
        identity: Élément neutre pour l'opération

    Examples:
        >>> a = ConstantNode("a", Decimal("10"))
        >>> b = ConstantNode("b", Decimal("20"))
        >>> sum_node = ReduceNode("sum", [a, b], operator.add, ZERO)
    """

    def __init__(self, name: str, inputs: list[Node], op: Callable, identity: Decimal):
        """
        Initialise un nœud de réduction.

        Args:
            name: Nom du nœud
            inputs: Liste des nœuds d'entrée
            op: Opération binaire (ex: operator.add)
            identity: Élément neutre (ex: ZERO pour addition)
        """
        super().__init__(name)
        self.inputs = inputs
        self.op = op
        self.identity = identity

    def dependencies(self):
        """Dépend de tous les nœuds d'entrée."""
        return [n.name for n in self.inputs]

    def evaluate(self, context, cache):
        """
        Applique l'opération de réduction.

        Returns:
            None si un des inputs est None, sinon le résultat de la réduction
        """
        acc = self.identity
        for n in self.inputs:
            v = cache[n.name]
            if v is None:
                return None
            acc = self.op(acc, v)
        return acc


class AddNode(ReduceNode):
    """
    Nœud effectuant la somme de ses inputs.

    Examples:
        >>> premium = ConstantNode("premium", Decimal("500"))
        >>> fee = ConstantNode("fee", Decimal("25"))
        >>> total = AddNode("total", [premium, fee])
        >>> # Résultat: 525
    """

    def __init__(self, name: str, inputs: list[Node]):
        """
        Initialise un nœud d'addition.

        Args:
            name: Nom du nœud
            inputs: Liste des nœuds à additionner
        """
        super().__init__(name, inputs, op=operator.add, identity=ZERO)


class MultiplyNode(ReduceNode):
    """
    Nœud effectuant le produit de ses inputs.

    Examples:
        >>> base = ConstantNode("base", Decimal("500"))
        >>> factor = ConstantNode("factor", Decimal("1.2"))
        >>> premium = MultiplyNode("premium", [base, factor])
        >>> # Résultat: 600
    """

    def __init__(self, name: str, inputs: list[Node]):
        """
        Initialise un nœud de multiplication.

        Args:
            name: Nom du nœud
            inputs: Liste des nœuds à multiplier
        """
        super().__init__(name, inputs, op=operator.mul, identity=ONE)


class IfNode(Node):
    """
    Nœud conditionnel (if-then-else).

    Évalue une condition sur un nœud et retourne l'une des deux valeurs
    selon que la condition est vraie ou fausse.

    Attributes:
        var_node: Nœud sur lequel évaluer la condition
        op: Opérateur de comparaison
        threshold: Valeur seuil pour la comparaison
        then_val: Valeur si condition vraie
        else_val: Valeur si condition fausse

    Examples:
        >>> density = InputNode("density")
        >>> factor = IfNode("density_factor", density, ">", 1000,
        ...                 Decimal("1.2"), Decimal("1.0"))
        >>> # Si density > 1000: retourne 1.2, sinon 1.0
    """

    def __init__(
        self, name, var_node: Node, op: Union[str, Callable], threshold, then_val, else_val
    ):
        """
        Initialise un nœud conditionnel.

        Args:
            name: Nom du nœud
            var_node: Nœud à tester
            op: Opérateur ("<", "<=", ">", ">=") ou callable
            threshold: Valeur de comparaison
            then_val: Valeur retournée si condition vraie
            else_val: Valeur retournée si condition fausse

        Raises:
            ValueError: Si l'opérateur est invalide
        """
        super().__init__(name)
        self.var_node = var_node
        # accept either operator symbol or a callable
        if isinstance(op, str):
            if op not in OPS:
                raise ValueError(f"Unknown operator symbol: {op}")
            self.op = OPS[op]
        else:
            self.op = op
        self.threshold = to_decimal(threshold)
        self.then_val = to_decimal(then_val)
        self.else_val = to_decimal(else_val)

    def dependencies(self):
        """Dépend du nœud testé."""
        return [self.var_node.name]

    def evaluate(self, context, cache):
        """
        Évalue la condition et retourne la valeur appropriée.

        Raises:
            ValueError: Si la valeur testée est None
        """
        value = cache[self.var_node.name]
        if value is None:
            raise ValueError(f"IF node '{self.name}' got None from '{self.var_node.name}'")
        return self.then_val if self.op(value, self.threshold) else self.else_val


class RoundNode(Node):
    """
    Nœud effectuant un arrondi.

    Attributes:
        input_node: Nœud à arrondir
        decimals: Nombre de décimales
        rounding: Mode d'arrondi (ROUND_HALF_UP ou ROUND_HALF_EVEN)

    Examples:
        >>> value = ConstantNode("value", Decimal("123.456"))
        >>> rounded = RoundNode("rounded", value, 2, "HALF_UP")
        >>> # Résultat: 123.46
    """

    def __init__(self, name, input_node, decimals, mode):
        """
        Initialise un nœud d'arrondi.

        Args:
            name: Nom du nœud
            input_node: Nœud à arrondir
            decimals: Nombre de décimales
            mode: Mode d'arrondi ("HALF_UP" ou "HALF_EVEN")
        """
        super().__init__(name)
        self.input_node = input_node
        self.decimals = int(decimals)
        self.rounding = ROUNDING_MODES[mode]

    def dependencies(self):
        """Dépend du nœud d'entrée."""
        return [self.input_node.name]

    def evaluate(self, context, cache):
        """
        Arrondit la valeur d'entrée.

        Returns:
            None si l'entrée est None, sinon la valeur arrondie
        """
        value = cache[self.input_node.name]
        if value is None:
            return None
        quant = Decimal("1").scaleb(-self.decimals)
        return value.quantize(quant, rounding=self.rounding)


class SwitchNode(Node):
    """
    Nœud de branchement multiple (switch/case).

    Alternative élégante aux IfNode imbriqués pour gérer plusieurs cas.
    Évalue une variable d'entrée et retourne la valeur correspondant au cas
    qui correspond, avec une valeur par défaut optionnelle.

    Attributes:
        var_node: Nœud fournissant la valeur à tester
        cases: Dictionnaire {valeur_test -> valeur_retour}
        default: Valeur par défaut si aucun cas ne correspond

    Examples:
        >>> region = InputNode("region", dtype=str)
        >>> cases = {
        ...     "Paris": Decimal("1.5"),
        ...     "Lyon": Decimal("1.3"),
        ...     "Marseille": Decimal("1.2"),
        ... }
        >>> factor = SwitchNode("region_factor", region, cases, Decimal("1.0"))
        >>> # Si region == "Paris": retourne 1.5
        >>> # Si region == "Lyon": retourne 1.3
        >>> # Si region non reconnue: retourne 1.0 (default)
    """

    def __init__(self, name: str, var_node: Node, cases: dict, default=None):
        """
        Initialise un nœud switch.

        Args:
            name: Nom du nœud
            var_node: Nœud fournissant la valeur à tester
            cases: Dictionnaire {valeur_test -> valeur_retour}
            default: Valeur par défaut si aucun cas ne correspond

        Raises:
            ValueError: Si cases est vide ou si var_node est None
        """
        super().__init__(name)
        if var_node is None:
            raise ValueError("SwitchNode requires a var_node")
        if not cases:
            raise ValueError("SwitchNode requires at least one case")
        self.var_node = var_node
        # Convertir les valeurs en Decimal si possible
        self.cases = {k: to_decimal(v) if v is not None else None for k, v in cases.items()}
        self.default = to_decimal(default) if default is not None else None

    def dependencies(self):
        """Dépend du nœud testé."""
        return [self.var_node.name]

    def evaluate(self, context, cache):
        """
        Évalue le switch et retourne la valeur du cas correspondant.

        Raises:
            ValueError: Si la valeur testée est None et qu'il n'y a pas de défaut
            KeyError: Si aucun cas ne correspond et qu'il n'y a pas de défaut
        """
        value = cache[self.var_node.name]

        if value in self.cases:
            return self.cases[value]

        if self.default is not None:
            return self.default

        raise KeyError(
            f"Switch node '{self.name}': value '{value}' not found in cases "
            f"and no default provided. Available cases: {list(self.cases.keys())}"
        )


class CoalesceNode(Node):
    """
    Nœud retournant la première valeur non-nulle parmi ses inputs.

    Utile pour gérer des valeurs par défaut ou des fallbacks en cascade.

    Attributes:
        inputs: Liste des nœuds à évaluer dans l'ordre

    Examples:
        >>> optional_discount = InputNode("discount")
        >>> default_discount = ConstantNode("default", Decimal("0"))
        >>> final_discount = CoalesceNode("final_discount", [optional_discount, default_discount])
        >>> # Si discount est fourni: utilise discount
        >>> # Sinon: utilise 0
    """

    def __init__(self, name: str, inputs: list[Node]):
        """
        Initialise un nœud coalesce.

        Args:
            name: Nom du nœud
            inputs: Liste des nœuds à évaluer (ordre prioritaire)

        Raises:
            ValueError: Si la liste d'inputs est vide
        """
        super().__init__(name)
        if not inputs:
            raise ValueError("CoalesceNode requires at least one input")
        self.inputs = inputs

    def dependencies(self):
        """Dépend de tous les nœuds d'entrée."""
        return [n.name for n in self.inputs]

    def evaluate(self, context, cache):
        """
        Retourne la première valeur non-nulle.

        Returns:
            La première valeur non-None, ou None si toutes sont None
        """
        for node in self.inputs:
            value = cache[node.name]
            if value is not None:
                return value
        return None


class MinNode(ReduceNode):
    """
    Nœud retournant le minimum de ses inputs.

    Examples:
        >>> price1 = ConstantNode("price1", Decimal("500"))
        >>> price2 = ConstantNode("price2", Decimal("450"))
        >>> best_price = MinNode("best_price", [price1, price2])
        >>> # Résultat: 450
    """

    def __init__(self, name: str, inputs: list[Node]):
        """
        Initialise un nœud minimum.

        Args:
            name: Nom du nœud
            inputs: Liste des nœuds à comparer
        """
        # On ne peut pas utiliser le pattern ReduceNode standard car min() n'a pas d'identité simple
        # On va override evaluate() directement
        Node.__init__(self, name)
        if not inputs:
            raise ValueError("MinNode requires at least one input")
        self.inputs = inputs

    def dependencies(self):
        """Dépend de tous les nœuds d'entrée."""
        return [n.name for n in self.inputs]

    def evaluate(self, context, cache):
        """
        Retourne le minimum des valeurs.

        Returns:
            None si tous les inputs sont None, sinon la valeur minimale
        """
        values = []
        for node in self.inputs:
            val = cache[node.name]
            if val is not None:
                values.append(val)

        if not values:
            return None

        return min(values)


class MaxNode(ReduceNode):
    """
    Nœud retournant le maximum de ses inputs.

    Examples:
        >>> deductible1 = ConstantNode("deductible1", Decimal("100"))
        >>> deductible2 = ConstantNode("deductible2", Decimal("200"))
        >>> final_deductible = MaxNode("final_deductible", [deductible1, deductible2])
        >>> # Résultat: 200
    """

    def __init__(self, name: str, inputs: list[Node]):
        """
        Initialise un nœud maximum.

        Args:
            name: Nom du nœud
            inputs: Liste des nœuds à comparer
        """
        Node.__init__(self, name)
        if not inputs:
            raise ValueError("MaxNode requires at least one input")
        self.inputs = inputs

    def dependencies(self):
        """Dépend de tous les nœuds d'entrée."""
        return [n.name for n in self.inputs]

    def evaluate(self, context, cache):
        """
        Retourne le maximum des valeurs.

        Returns:
            None si tous les inputs sont None, sinon la valeur maximale
        """
        values = []
        for node in self.inputs:
            val = cache[node.name]
            if val is not None:
                values.append(val)

        if not values:
            return None

        return max(values)


class AbsNode(Node):
    """
    Nœud retournant la valeur absolue de son input.

    Attributes:
        input_node: Nœud dont on veut la valeur absolue

    Examples:
        >>> diff = ConstantNode("diff", Decimal("-50"))
        >>> abs_diff = AbsNode("abs_diff", diff)
        >>> # Résultat: 50
    """

    def __init__(self, name: str, input_node: Node):
        """
        Initialise un nœud valeur absolue.

        Args:
            name: Nom du nœud
            input_node: Nœud d'entrée

        Raises:
            ValueError: Si input_node est None
        """
        super().__init__(name)
        if input_node is None:
            raise ValueError("AbsNode requires an input_node")
        self.input_node = input_node

    def dependencies(self):
        """Dépend du nœud d'entrée."""
        return [self.input_node.name]

    def evaluate(self, context, cache):
        """
        Retourne la valeur absolue.

        Returns:
            None si l'entrée est None, sinon abs(valeur)
        """
        value = cache[self.input_node.name]
        if value is None:
            return None
        return abs(value)
