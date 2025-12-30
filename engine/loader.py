"""
Module de chargement et validation des tarifs depuis YAML.

Ce module fournit les outils pour charger des définitions de tarifs
depuis des fichiers YAML et construire les graphes de calcul correspondants.
"""
import yaml
from decimal import Decimal
from typing import cast, Type
from engine.nodes import (
    ConstantNode,
    AddNode,
    MultiplyNode,
    LookupNode,
    IfNode,
    RoundNode,
    InputNode,
    OPS,
)


def parse_condition(expr: str):
    """
    Parse une expression conditionnelle en ses composants.

    Args:
        expr: Expression sous forme "var > threshold" (ex: "density > 1000")

    Returns:
        Tuple (nom_variable, opérateur, seuil)

    Raises:
        ValueError: Si l'expression est invalide

    Examples:
        >>> parse_condition("density > 1000")
        ('density', '>', Decimal('1000'))
        >>> parse_condition("age >= 18")
        ('age', '>=', Decimal('18'))
    """
    # check longer operator symbols first (e.g. '<=' before '<')
    for op_str in sorted(OPS.keys(), key=len, reverse=True):
        if op_str in expr:
            var, threshold = expr.split(op_str)
            return var.strip(), op_str, Decimal(threshold.strip())
    raise ValueError(f"Invalid condition: {expr}")


class TariffLoader:
    """
    Chargeur et validateur de tarifs depuis YAML.

    Cette classe gère le chargement de définitions de tarifs au format YAML
    et la construction des graphes de nœuds correspondants.

    Attributes:
        tables: Dictionnaire des tables de lookup disponibles

    Examples:
        >>> tables = {"age_table": load_range_table("age_factors.csv")}
        >>> loader = TariffLoader(tables=tables)
        >>> nodes = loader.load("tariff.yaml")
        >>> graph = TariffGraph(nodes)
    """

    def __init__(self, tables=None):
        """
        Initialise le chargeur de tarifs.

        Args:
            tables: Dictionnaire optionnel {nom -> table} des tables de lookup
        """
        self.tables = tables or {}

    def validate(self, data):
        """
        Valide la structure d'un tarif YAML.

        Args:
            data: Dictionnaire parsé depuis YAML

        Raises:
            ValueError: Si la structure est invalide
        """
        if "nodes" not in data:
            raise ValueError("Tariff YAML must contain 'nodes'")

        nodes = data["nodes"]

        for name, spec in nodes.items():
            if "type" not in spec:
                raise ValueError(f"Node '{name}' missing 'type'")

            node_type = spec["type"]

            if node_type == "CONSTANT":
                if "value" not in spec:
                    raise ValueError(f"CONSTANT node '{name}' missing 'value'")

            elif node_type in ("ADD", "MULTIPLY"):
                inputs = spec.get("inputs")
                if not isinstance(inputs, list) or len(inputs) == 0:
                    raise ValueError(
                        f"{node_type} node '{name}' must have non-empty 'inputs' list"
                    )

            elif node_type == "LOOKUP":
                if "table" not in spec:
                    raise ValueError(f"LOOKUP node '{name}' must have a 'table'")
                if spec["table"] not in self.tables:
                    raise ValueError(
                        f"LOOKUP node '{name}' references unknown table '{spec['table']}'"
                    )

                if "key_node" not in spec:
                    raise ValueError(
                        f"LOOKUP node '{name}' must define 'key_node' (no 'key' allowed)"
                    )

                key_node_name = spec["key_node"]
                if key_node_name not in nodes:
                    raise ValueError(
                        f"LOOKUP node '{name}' references unknown key_node '{key_node_name}'"
                    )

            elif node_type == "IF":
                for field in ("condition", "then", "else"):
                    if field not in spec:
                        raise ValueError(f"IF node '{name}' missing '{field}'")

            elif node_type == "ROUND":
                if "input" not in spec:
                    raise ValueError(f"ROUND node '{name}' missing 'input'")
                if "mode" in spec and spec["mode"] not in ("HALF_UP", "HALF_EVEN"):
                    raise ValueError(
                        f"ROUND node '{name}' has invalid mode '{spec['mode']}'"
                    )

            elif node_type == "INPUT":
                # leaf node wrapping a context variable, must have no extra fields
                allowed_fields = {"type", "dtype"}
                extra_fields = set(spec.keys()) - allowed_fields
                if extra_fields:
                    raise ValueError(
                        f"INPUT node '{name}' should not have extra fields: {extra_fields}"
                    )

            else:
                raise ValueError(f"Unknown node type '{node_type}' in node '{name}'")

    def load(self, path: str):
        """
        Charge un tarif depuis un fichier YAML.

        Cette méthode effectue un chargement en deux passes:
        1. Création des nœuds feuilles (CONSTANT, INPUT)
        2. Création des nœuds composites avec références

        Args:
            path: Chemin vers le fichier YAML du tarif

        Returns:
            Dictionnaire {nom -> Node} des nœuds créés

        Raises:
            ValueError: Si la validation échoue
            FileNotFoundError: Si le fichier n'existe pas

        Examples:
            >>> loader = TariffLoader(tables={"age_table": age_table})
            >>> nodes = loader.load("tariff.yaml")
            >>> # nodes contient tous les nœuds du graphe
        """
        with open(path) as f:
            data = yaml.safe_load(f)

        self.validate(data)

        node_defs = data["nodes"]
        nodes = {}

        # First pass: create leaf nodes (CONSTANT or INPUT)
        for name, spec in node_defs.items():
            node_type = spec["type"]

            if node_type == "CONSTANT":
                nodes[name] = ConstantNode(name=name, value=Decimal(str(spec["value"])))

            elif node_type == "INPUT":
                dtype_str = spec.get("dtype", "decimal").lower()
                if dtype_str == "decimal":
                    dtype = Decimal
                elif dtype_str == "str":
                    dtype = str
                else:
                    raise ValueError(
                        f"INPUT node '{name}' has unknown dtype '{dtype_str}'"
                    )

                nodes[name] = InputNode(
                    name=name, dtype=cast(Type[Decimal], dtype)
                )  # new node type wrapping context

            elif node_type in ("ADD", "MULTIPLY", "LOOKUP", "IF", "ROUND"):
                # composite nodes wired later
                nodes[name] = None

            else:
                raise ValueError(f"Unknown node type {node_type}")

        # Second pass: wire composite nodes
        for name, spec in node_defs.items():
            node_type = spec["type"]

            if node_type in ("ADD", "MULTIPLY"):
                # inputs must be nodes
                inputs = [nodes[i] for i in spec.get("inputs", [])]

                if node_type == "ADD":
                    nodes[name] = AddNode(name, inputs)
                elif node_type == "MULTIPLY":
                    nodes[name] = MultiplyNode(name, inputs)

            elif node_type == "LOOKUP":
                table_name = spec["table"]
                table = self.tables[table_name]

                # always use key_node; context variables must be wrapped as INPUT nodes
                key_node_name = spec["key_node"]
                key_node = nodes[key_node_name]
                nodes[name] = LookupNode(name=name, table=table, key_node=key_node)

            elif node_type == "IF":
                # var must be an input node
                var, op, threshold = parse_condition(spec["condition"])
                var_node = nodes[var]

                nodes[name] = IfNode(
                    name=name,
                    var_node=var_node,
                    op=op,
                    threshold=threshold,
                    then_val=spec["then"],
                    else_val=spec["else"],
                )

            elif node_type == "ROUND":
                input_name = spec["input"]
                input_node = nodes[input_name]

                decimals = spec.get("decimals", 2)
                mode = spec.get("mode", "HALF_UP")

                nodes[name] = RoundNode(
                    name=name,
                    input_node=input_node,
                    decimals=decimals,
                    mode=mode,
                )

        return nodes
