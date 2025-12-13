from abc import ABC, abstractmethod
from decimal import Decimal


class Node(ABC):
    def __init__(self, name: str):
        self.name = name

    @abstractmethod
    def dependencies(self) -> list[str]:
        pass

    @abstractmethod
    def evaluate(self, context: dict, cache: dict) -> Decimal:
        pass


class ConstantNode(Node):
    def __init__(self, name: str, value: Decimal):
        super().__init__(name)
        self.value = value

    def dependencies(self):
        return []

    def evaluate(self, context, cache):
        return self.value


class ContextNode(Node):
    def __init__(self, name: str):
        super().__init__(name)

    def dependencies(self):
        return []

    def evaluate(self, context, cache):
        if self.name not in context:
            raise KeyError(f"Missing context variable: {self.name}")
        return Decimal(str(context[self.name]))


class LookupNode(Node):
    def __init__(self, name, table, key):
        super().__init__(name)
        self.table = table  # RangeTable
        self.key = key

    def dependencies(self):
        return []

    def evaluate(self, context, cache):
        value = context[self.key]
        return self.table.lookup(value)


class AddNode(Node):
    def __init__(self, name: str, inputs: list[Node]):
        super().__init__(name)
        self.inputs = inputs

    def dependencies(self):
        return [n.name for n in self.inputs]

    def evaluate(self, context, cache):
        return sum((cache[n.name] for n in self.inputs), start=Decimal("0"))


class MultiplyNode(Node):
    def __init__(self, name: str, inputs: list[Node]):
        super().__init__(name)
        self.inputs = inputs

    def dependencies(self):
        return [n.name for n in self.inputs]

    def evaluate(self, context, cache):
        result = Decimal("1")
        for n in self.inputs:
            result *= cache[n.name]
        return result


class IfNode(Node):
    def __init__(self, name, condition, then_node, else_node):
        super().__init__(name)
        self.condition = condition  # callable(context) -> bool
        self.then_node = then_node
        self.else_node = else_node

    def dependencies(self):
        return [self.then_node.name, self.else_node.name]

    def evaluate(self, context, cache):
        if self.condition(context):
            return cache[self.then_node.name]
        return cache[self.else_node.name]
