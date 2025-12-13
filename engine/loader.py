import yaml
from decimal import Decimal
from engine.nodes import ConstantNode, AddNode, MultiplyNode, ContextNode, LookupNode


def resolve_node(name, nodes):
    if name in nodes:
        return nodes[name]
    node = ContextNode(name)
    nodes[name] = node  # add to nodes so graph can find it
    return node


class TariffLoader:
    def __init__(self, tables=None):
        self.tables = tables or {}

    def load(self, path: str):
        with open(path) as f:
            data = yaml.safe_load(f)

        node_defs = data["nodes"]
        nodes = {}

        # First pass: create leaf nodes only (constants)
        for name, spec in node_defs.items():
            node_type = spec["type"]

            if node_type == "CONSTANT":
                nodes[name] = ConstantNode(name=name, value=Decimal(str(spec["value"])))

            elif node_type in ("ADD", "MULTIPLY", "LOOKUP"):
                # composite nodes wired later
                nodes[name] = None

            else:
                raise ValueError(f"Unknown node type {node_type}")

        # Second pass: wire composite nodes
        for name, spec in node_defs.items():
            node_type = spec["type"]

            if node_type in ("ADD", "MULTIPLY"):
                # resolve_node handles YAML nodes or context nodes
                inputs = [resolve_node(i, nodes) for i in spec.get("inputs", [])]

                if node_type == "ADD":
                    nodes[name] = AddNode(name, inputs)
                elif node_type == "MULTIPLY":
                    nodes[name] = MultiplyNode(name, inputs)
            elif node_type == "LOOKUP":
                table_name = spec["table"]
                table = self.tables[table_name]
                key = spec["key"]
                nodes[name] = LookupNode(name=name, table=table, key=key)

        return nodes
