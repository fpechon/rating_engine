from abc import ABC, abstractmethod
from decimal import Decimal, ROUND_HALF_UP, ROUND_HALF_EVEN
import operator
from typing import Optional, Union, Callable

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


ZERO = Decimal("0")
ONE = Decimal("1")


def to_decimal(value) -> Optional[Decimal]:
    """Convert a value to Decimal, preserving None and Decimal inputs."""
    if value is None:
        return None
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


class Node(ABC):
    def __init__(self, name: str):
        self.name = name

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({self.name})"

    @abstractmethod
    def dependencies(self) -> list[str]:
        pass

    @abstractmethod
    def evaluate(self, context: dict, cache: dict) -> Optional[Decimal]:
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
            return to_decimal(value)
        return value


class LookupNode(Node):
    def __init__(self, name, table, key_node):
        super().__init__(name)
        self.table = table
        if key_node is None:
            raise ValueError("LookupNode requires a key_node")
        self.key_node = key_node

    def dependencies(self):
        return [self.key_node.name]

    def evaluate(self, context, cache):
        value = cache[self.key_node.name]
        return self.table.lookup(value)


class ReduceNode(Node):
    """General aggregation node over input nodes.

    `op` is a binary callable (like operator.add) and `identity`
    the neutral element (ZERO for add, ONE for multiply).
    """

    def __init__(self, name: str, inputs: list[Node], op: Callable, identity: Decimal):
        super().__init__(name)
        self.inputs = inputs
        self.op = op
        self.identity = identity

    def dependencies(self):
        return [n.name for n in self.inputs]

    def evaluate(self, context, cache):
        acc = self.identity
        for n in self.inputs:
            v = cache[n.name]
            if v is None:
                return None
            acc = self.op(acc, v)
        return acc


class AddNode(ReduceNode):
    def __init__(self, name: str, inputs: list[Node]):
        super().__init__(name, inputs, op=operator.add, identity=ZERO)


class MultiplyNode(ReduceNode):
    def __init__(self, name: str, inputs: list[Node]):
        super().__init__(name, inputs, op=operator.mul, identity=ONE)


class IfNode(Node):
    def __init__(self, name, var_node: Node, op: Union[str, Callable], threshold, then_val, else_val):
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
        return [self.var_node.name]

    def evaluate(self, context, cache):
        value = cache[self.var_node.name]
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
        if value is None:
            return None
        quant = Decimal("1").scaleb(-self.decimals)
        return value.quantize(quant, rounding=self.rounding)
