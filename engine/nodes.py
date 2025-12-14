from abc import ABC, abstractmethod
from decimal import Decimal, ROUND_HALF_UP, ROUND_HALF_EVEN
import operator

OPS = {
    "<": operator.lt,
    "<=": operator.le,
    ">": operator.gt,
    ">=": operator.ge,
}

ROUNDING_MODES = {
    "HALF_UP": ROUND_HALF_UP,
    "HALF_EVEN": ROUND_HALF_EVEN,
}


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


class InputNode(Node):
    """
    Leaf node representing a value provided at evaluation time (from context).
    All other nodes should depend only on nodes, never directly on context.
    """
    def __init__(self, name: str, dtype=Decimal):
        super().__init__(name)
        self.dtype = dtype

    def dependencies(self):
        return []

    def evaluate(self, context, cache):
        if self.name not in context:
            raise KeyError(f"Missing input variable: {self.name}")
        value = context[self.name]

        if value is None:
            return None

        if self.dtype is Decimal:
            return Decimal(str(value))
        return value


class LookupNode(Node):
    def __init__(self, name, table, key=None, key_node=None):
        super().__init__(name)
        self.table = table
        self.key = key
        self.key_node = key_node

        if (key is None) == (key_node is None):
            raise ValueError("Provide exactly one of key or key_node")

    def dependencies(self):
        if self.key_node:
            return [self.key_node.name]
        return []

    def evaluate(self, context, cache):
        if self.key_node:
            value = cache[self.key_node.name]
        else:
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
    def __init__(self, name, var, op, threshold, then_val, else_val):
        super().__init__(name)
        self.var_node = var   # Node object
        self.op = op               # operator function
        self.threshold = Decimal(str(threshold))
        self.then_val = Decimal(str(then_val))
        self.else_val = Decimal(str(else_val))

    def dependencies(self):
        return [self.var_node.name]

    def evaluate(self, context, cache):
        value = cache[self.var_node.name]  # read from upstream node
        if value is None:
            raise ValueError(f"IF node '{self.name}' got None from '{self.var_node.name}'")
        return self.then_val if self.op(value, self.threshold) else self.else_val



class RoundNode(Node):
    def __init__(self, name, input_node, decimals, mode):
        super().__init__(name)
        self.input_node = input_node
        self.decimals = int(decimals)
        self.rounding = ROUNDING_MODES[mode]

    def dependencies(self):
        return [self.input_node.name]

    def evaluate(self, context, cache):
        value = cache[self.input_node.name]
        quant = Decimal("1").scaleb(-self.decimals)
        return value.quantize(quant, rounding=self.rounding)
