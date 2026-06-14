"""
SentinelX Semantic Analyzer + Static Type Checker
Performs:
  - Symbol table construction
  - Undefined variable detection
  - Duplicate declaration detection
  - Type inference for expressions
  - Type mismatch detection
  - Division by zero (static detection)
  - Infinite loop warning (trivial cases)
"""

from typing import Dict, List, Optional, Any
from .ast_nodes import *


class SemanticError:
    def __init__(self, etype: str, msg: str, line: int, suggestion: str = ""):
        self.type = etype
        self.message = msg
        self.line = line
        self.suggestion = suggestion

    def to_dict(self):
        return {
            "type": self.type,
            "message": self.message,
            "line": self.line,
            "suggestion": self.suggestion
        }


class SymbolTable:
    def __init__(self, parent=None):
        self._table: Dict[str, dict] = {}
        self.parent = parent

    def declare(self, name: str, dtype: str, line: int) -> bool:
        if name in self._table:
            return False  # duplicate
        self._table[name] = {"dtype": dtype, "line": line, "used": False}
        return True

    def lookup(self, name: str) -> Optional[dict]:
        if name in self._table:
            return self._table[name]
        if self.parent:
            return self.parent.lookup(name)
        return None

    def mark_used(self, name: str):
        if name in self._table:
            self._table[name]["used"] = True
        elif self.parent:
            self.parent.mark_used(name)

    def get_all(self) -> List[dict]:
        rows = []
        for name, info in self._table.items():
            rows.append({"name": name, "type": info["dtype"],
                         "line": info["line"], "used": info["used"]})
        return rows

    def child(self):
        return SymbolTable(parent=self)


# Type compatibility rules
NUMERIC = {'int', 'float'}

def types_compatible_assign(target: str, val: str) -> bool:
    if target == val:
        return True
    if target == 'float' and val == 'int':
        return True
    return False

def result_type(op: str, left: str, right: str) -> Optional[str]:
    """Return resulting type for a binary operation, or None if invalid."""
    if op in ('+', '-', '*', '/', '%'):
        if left in NUMERIC and right in NUMERIC:
            return 'float' if 'float' in (left, right) else 'int'
        if op == '+' and left == 'string' and right == 'string':
            return 'string'
        return None
    if op in ('==', '!='):
        if left == right or (left in NUMERIC and right in NUMERIC):
            return 'bool'
        return None
    if op in ('<', '>', '<=', '>='):
        if left in NUMERIC and right in NUMERIC:
            return 'bool'
        return None
    if op in ('&&', '||'):
        if left == 'bool' and right == 'bool':
            return 'bool'
        return None
    return None


class SemanticAnalyzer:
    def __init__(self):
        self.errors: List[SemanticError] = []
        self.warnings: List[SemanticError] = []
        self.global_scope = SymbolTable()
        self._scope = self.global_scope

    def analyze(self, program: Program):
        for stmt in program.statements:
            self._visit_stmt(stmt)

    def _push_scope(self):
        self._scope = self._scope.child()

    def _pop_scope(self):
        self._scope = self._scope.parent

    def _error(self, etype, msg, line, suggestion=""):
        self.errors.append(SemanticError(etype, msg, line, suggestion))

    def _warn(self, etype, msg, line, suggestion=""):
        self.warnings.append(SemanticError(etype, msg, line, suggestion))

    # ── Statements ────────────────────────────────────────────────────────────

    def _visit_stmt(self, node: ASTNode):
        if isinstance(node, VarDecl):
            self._visit_var_decl(node)
        elif isinstance(node, Assignment):
            self._visit_assignment(node)
        elif isinstance(node, IfStmt):
            self._visit_if(node)
        elif isinstance(node, WhileStmt):
            self._visit_while(node)
        elif isinstance(node, PrintStmt):
            self._visit_print(node)

    def _visit_var_decl(self, node: VarDecl):
        if not self._scope.declare(node.name, node.dtype, node.line):
            self._error(
                "DuplicateDeclaration",
                f"Variable '{node.name}' is already declared in this scope",
                node.line,
                f"Rename one of the '{node.name}' declarations"
            )
        if node.init:
            init_type = self._visit_expr(node.init)
            if init_type and not types_compatible_assign(node.dtype, init_type):
                self._error(
                    "TypeMismatch",
                    f"Cannot assign {init_type} to {node.dtype} variable '{node.name}'",
                    node.line,
                    f"Cast or change the type: expected {node.dtype}, got {init_type}"
                )

    def _visit_assignment(self, node: Assignment):
        sym = self._scope.lookup(node.name)
        if not sym:
            self._error(
                "UndeclaredVariable",
                f"Variable '{node.name}' is used before declaration",
                node.line,
                f"Declare it first: int {node.name} = ...;"
            )
            self._visit_expr(node.value)
            return
        self._scope.mark_used(node.name)
        val_type = self._visit_expr(node.value)
        if val_type and not types_compatible_assign(sym["dtype"], val_type):
            self._error(
                "TypeMismatch",
                f"Cannot assign {val_type} to '{node.name}' (declared as {sym['dtype']})",
                node.line,
                f"Expected {sym['dtype']}, got {val_type}"
            )

    def _visit_if(self, node: IfStmt):
        cond_type = self._visit_expr(node.condition)
        if cond_type and cond_type != 'bool':
            self._error(
                "TypeMismatch",
                f"If-condition must be bool, got {cond_type}",
                node.line,
                "Use a comparison operator to produce a bool value"
            )
        self._push_scope()
        for s in node.then_block:
            self._visit_stmt(s)
        self._pop_scope()
        if node.else_block:
            self._push_scope()
            for s in node.else_block:
                self._visit_stmt(s)
            self._pop_scope()

    def _visit_while(self, node: WhileStmt):
        cond_type = self._visit_expr(node.condition)
        if cond_type and cond_type != 'bool':
            self._error(
                "TypeMismatch",
                f"While-condition must be bool, got {cond_type}",
                node.line,
                "Use a comparison operator"
            )
        # Warn about trivially infinite loops: while(true) with no break
        if isinstance(node.condition, Literal) and node.condition.value is True:
            self._warn(
                "InfiniteLoopWarning",
                "while(true) detected — possible infinite loop",
                node.line,
                "Add a break condition or flag variable"
            )
        self._push_scope()
        for s in node.body:
            self._visit_stmt(s)
        self._pop_scope()

    def _visit_print(self, node: PrintStmt):
        self._visit_expr(node.expr)

    # ── Expressions → returns inferred type ──────────────────────────────────

    def _visit_expr(self, node: ASTNode) -> Optional[str]:
        if isinstance(node, Literal):
            return node.dtype

        if isinstance(node, Identifier):
            sym = self._scope.lookup(node.name)
            if not sym:
                self._error(
                    "UndeclaredVariable",
                    f"Variable '{node.name}' is not declared",
                    node.line,
                    f"Declare it first, e.g.: int {node.name};"
                )
                return None
            self._scope.mark_used(node.name)
            return sym["dtype"]

        if isinstance(node, BinaryOp):
            left_type = self._visit_expr(node.left)
            right_type = self._visit_expr(node.right)
            # Division by zero check
            if node.op in ('/', '%'):
                if isinstance(node.right, Literal) and node.right.value == 0:
                    self._error(
                        "DivisionByZero",
                        "Division by zero detected",
                        node.line,
                        "Ensure the divisor is non-zero before dividing"
                    )
            if left_type and right_type:
                rtype = result_type(node.op, left_type, right_type)
                if rtype is None:
                    self._error(
                        "TypeMismatch",
                        f"Operator '{node.op}' cannot be applied to {left_type} and {right_type}",
                        node.line,
                        f"Ensure operands have compatible types for '{node.op}'"
                    )
                return rtype
            return None

        if isinstance(node, UnaryOp):
            operand_type = self._visit_expr(node.operand)
            if node.op == '!' and operand_type != 'bool':
                self._error(
                    "TypeMismatch",
                    f"'!' operator requires bool, got {operand_type}",
                    node.line,
                    "Apply '!' only to boolean expressions"
                )
                return 'bool'
            if node.op == '-' and operand_type not in NUMERIC:
                self._error(
                    "TypeMismatch",
                    f"Unary '-' requires numeric, got {operand_type}",
                    node.line,
                    "Unary minus is only valid on int or float"
                )
            return operand_type

        return None

    def get_symbol_table(self) -> List[dict]:
        return self.global_scope.get_all()

    def all_errors(self) -> List[dict]:
        return [e.to_dict() for e in self.errors] + \
               [{**w.to_dict(), "type": "Warning:" + w.type} for w in self.warnings]
