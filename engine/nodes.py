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
    def __init__(self, name, var, op, threshold, then_val, else_val):
        super().__init__(name)
        self.var = var  # context variable name
        self.op = op  # operator function
        self.threshold = threshold  # Decimal
        self.then_val = Decimal(str(then_val))
        self.else_val = Decimal(str(else_val))

    def dependencies(self):
        return []  # leaf node

    def evaluate(self, context, cache):
        value = Decimal(str(context[self.var]))
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
