"""
SentinelX AST Node Definitions
All AST nodes used by the parser and subsequent phases.
"""

from dataclasses import dataclass, field
from typing import List, Optional, Any


class ASTNode:
    pass


# ── Expressions ──────────────────────────────────────────────────────────────

@dataclass
class Literal(ASTNode):
    value: Any
    dtype: str   # 'int', 'float', 'string', 'bool'
    line: int = 0

    def node_type(self): return "Literal"


@dataclass
class Identifier(ASTNode):
    name: str
    line: int = 0

    def node_type(self): return "Identifier"


@dataclass
class BinaryOp(ASTNode):
    op: str
    left: ASTNode
    right: ASTNode
    line: int = 0

    def node_type(self): return "BinaryOp"


@dataclass
class UnaryOp(ASTNode):
    op: str
    operand: ASTNode
    line: int = 0

    def node_type(self): return "UnaryOp"


# ── Statements ────────────────────────────────────────────────────────────────

@dataclass
class VarDecl(ASTNode):
    dtype: str
    name: str
    init: Optional[ASTNode]
    line: int = 0

    def node_type(self): return "VarDecl"


@dataclass
class Assignment(ASTNode):
    name: str
    value: ASTNode
    line: int = 0

    def node_type(self): return "Assignment"


@dataclass
class IfStmt(ASTNode):
    condition: ASTNode
    then_block: List[ASTNode]
    else_block: Optional[List[ASTNode]]
    line: int = 0

    def node_type(self): return "IfStmt"


@dataclass
class WhileStmt(ASTNode):
    condition: ASTNode
    body: List[ASTNode]
    line: int = 0

    def node_type(self): return "WhileStmt"


@dataclass
class PrintStmt(ASTNode):
    expr: ASTNode
    line: int = 0

    def node_type(self): return "PrintStmt"


@dataclass
class Program(ASTNode):
    statements: List[ASTNode] = field(default_factory=list)

    def node_type(self): return "Program"


# ── AST → JSON for frontend visualization ────────────────────────────────────

def ast_to_dict(node: ASTNode) -> dict:
    if node is None:
        return None

    if isinstance(node, Program):
        return {
            "type": "Program",
            "children": [ast_to_dict(s) for s in node.statements]
        }
    elif isinstance(node, Literal):
        return {
            "type": "Literal",
            "dtype": node.dtype,
            "value": str(node.value),
            "line": node.line
        }
    elif isinstance(node, Identifier):
        return {
            "type": "Identifier",
            "name": node.name,
            "line": node.line
        }
    elif isinstance(node, BinaryOp):
        return {
            "type": "BinaryOp",
            "op": node.op,
            "line": node.line,
            "children": [ast_to_dict(node.left), ast_to_dict(node.right)]
        }
    elif isinstance(node, UnaryOp):
        return {
            "type": "UnaryOp",
            "op": node.op,
            "line": node.line,
            "children": [ast_to_dict(node.operand)]
        }
    elif isinstance(node, VarDecl):
        d = {
            "type": "VarDecl",
            "dtype": node.dtype,
            "name": node.name,
            "line": node.line,
        }
        if node.init:
            d["children"] = [ast_to_dict(node.init)]
        return d
    elif isinstance(node, Assignment):
        return {
            "type": "Assignment",
            "name": node.name,
            "line": node.line,
            "children": [ast_to_dict(node.value)]
        }
    elif isinstance(node, IfStmt):
        d = {
            "type": "IfStmt",
            "line": node.line,
            "condition": ast_to_dict(node.condition),
            "then": [ast_to_dict(s) for s in node.then_block],
        }
        if node.else_block:
            d["else"] = [ast_to_dict(s) for s in node.else_block]
        return d
    elif isinstance(node, WhileStmt):
        return {
            "type": "WhileStmt",
            "line": node.line,
            "condition": ast_to_dict(node.condition),
            "body": [ast_to_dict(s) for s in node.body]
        }
    elif isinstance(node, PrintStmt):
        return {
            "type": "PrintStmt",
            "line": node.line,
            "children": [ast_to_dict(node.expr)]
        }
    else:
        return {"type": "Unknown", "repr": str(node)}
