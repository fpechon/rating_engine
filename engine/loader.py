import yaml
from decimal import Decimal
from engine.nodes import (
    ConstantNode,
    AddNode,
    MultiplyNode
)

class TariffLoader:
    def load(self, path: str):
        with open(path) as f:
            data = yaml.safe_load(f)

        node_defs = data["nodes"]
        nodes = {}

        # First pass: create all nodes without wiring inputs
        for name, spec in node_defs.items():
            node_type = spec["type"]

            if node_type == "CONSTANT":
                nodes[name] = ConstantNode(
                    name=name,
                    value=Decimal(str(spec["value"]))
                )

            elif node_type in ("ADD", "MULTIPLY"):
                # inputs wired later
                nodes[name] = None

            else:
                raise ValueError(f"Unknown node type {node_type}")

        # Second pass: wire composite nodes
        for name, spec in node_defs.items():
            node_type = spec["type"]

            if node_type == "ADD":
                inputs = [nodes[i] for i in spec["inputs"]]
                nodes[name] = AddNode(name, inputs)

            elif node_type == "MULTIPLY":
                inputs = [nodes[i] for i in spec["inputs"]]
                nodes[name] = MultiplyNode(name, inputs)

        return nodes
