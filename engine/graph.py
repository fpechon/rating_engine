from engine.nodes import Node

class TariffGraph:
    def __init__(self, nodes: dict[str, Node]):
        self.nodes = nodes

    def evaluate(self, root, context, trace=None):
        cache = {}

        def eval_node(name):
            if name in cache:
                return cache[name]

            node = self.nodes[name]
            for dep in node.dependencies():
                eval_node(dep)

            val = node.evaluate(context, cache)
            cache[name] = val

            if trace is not None:
                trace[name] = {
                    "value": val,
                    "type": type(node).__name__,
                    # optionally add more info here
                }

            return val

        eval_node(root)
        return cache[root] if trace is None else trace
