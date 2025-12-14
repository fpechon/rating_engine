from graphviz import Digraph


def node_color(node):
    if node.__class__.__name__ == "LookupNode":
        return "lightblue"
    if node.__class__.__name__ == "MultiplyNode":
        return "lightgreen"
    if node.__class__.__name__ == "AddNode":
        return "lightyellow"
    if node.__class__.__name__ == "IfNode":
        return "orange"
    if node.__class__.__name__ == "RoundNode":
        return "pink"
    if node.__class__.__name__ == "ContextNode":
        return "gray"
    return "white"


def visualize_graph(graph):
    dot = Digraph(comment="Tariff Graph")

    for name, node in graph.nodes.items():
        label = f"{name}\n[{node.__class__.__name__}]"
        dot.node(name, label, style="filled", fillcolor=node_color(node))

        for dep in node.dependencies():
            dot.edge(dep, name)

    return dot
