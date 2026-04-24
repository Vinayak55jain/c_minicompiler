from dataclasses import dataclass
from typing import List, Optional

@dataclass
class CType:
    base: str
    ptr: int = 0

    def __str__(self):
        return self.base + '*' * self.ptr

    def __eq__(self, other):
        return isinstance(other, CType) and self.base == other.base and self.ptr == other.ptr

# AST Nodes

@dataclass
class Node:
    pass

@dataclass
class Program(Node):
    decls: List[Node]

@dataclass
class FuncDecl(Node):
    name: str
    ret_type: CType
    params: List['Param']
    body: Optional['Block']

@dataclass
class Param(Node):
    name: str
    ctype: CType

@dataclass
class VarDecl(Node):
    name: str
    ctype: CType
    array_size: Optional[int] = None
    init: Optional[Node] = None

@dataclass
class Block(Node):
    stmts: List[Node]

@dataclass
class ExprStmt(Node):
    expr: Node

@dataclass
class IfStmt(Node):
    cond: Node
    then_branch: Node
    else_branch: Optional[Node] = None

@dataclass
class WhileStmt(Node):
    cond: Node
    body: Node

@dataclass
class ForStmt(Node):
    init: Optional[Node]
    cond: Optional[Node]
    incr: Optional[Node]
    body: Node

@dataclass
class ReturnStmt(Node):
    value: Optional[Node] = None

# Expressions

@dataclass
class Expr(Node):
    pass

@dataclass
class BinOp(Expr):
    left: Expr
    op: str
    right: Expr

@dataclass
class UnaryOp(Expr):
    op: str
    operand: Expr
    prefix: bool = True

@dataclass
class Call(Expr):
    name: str
    args: List[Expr]

@dataclass
class Identifier(Expr):
    name: str

@dataclass
class IntLiteral(Expr):
    value: int

@dataclass
class CharLiteral(Expr):
    value: int

@dataclass
class StringLiteral(Expr):
    value: str

@dataclass
class Assign(Expr):
    target: Expr
    op: str
    value: Expr

@dataclass
class ArrayIndex(Expr):
    array: Expr
    index: Expr

@dataclass
class AddrOf(Expr):
    expr: Expr

@dataclass
class Deref(Expr):
    expr: Expr