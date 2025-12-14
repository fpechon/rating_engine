from engine.nodes import Node

class TariffGraph:
    def __init__(self, nodes: dict[str, Node]):
        self.nodes = nodes

    def evaluate(self, root: str, context: dict, full=False):
        cache = {}

        def eval_node(name):
            if name in cache:
                return cache[name]
            node = self.nodes[name]
            for dep in node.dependencies():
                eval_node(dep)
            cache[name] = node.evaluate(context, cache)
            return cache[name]

        eval_node(root)
        return cache if full else cache[root]
