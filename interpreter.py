"""
SentinelX Mini Interpreter
Walks the AST and executes valid programs directly.
Supports: arithmetic, logic, comparisons, if/else, while, print, variables.
"""

from typing import Any, Dict, List, Optional
from .ast_nodes import *


class RuntimeError_(Exception):
    def __init__(self, msg: str, line: int):
        super().__init__(msg)
        self.line = line


class Environment:
    def __init__(self, parent=None):
        self._vars: Dict[str, Any] = {}
        self.parent = parent

    def set(self, name: str, value: Any):
        self._vars[name] = value

    def get(self, name: str) -> Any:
        if name in self._vars:
            return self._vars[name]
        if self.parent:
            return self.parent.get(name)
        raise KeyError(name)

    def update(self, name: str, value: Any):
        if name in self._vars:
            self._vars[name] = value
        elif self.parent:
            self.parent.update(name, value)
        else:
            raise KeyError(name)


MAX_ITERATIONS = 10_000   # guard against infinite loops


class Interpreter:
    def __init__(self):
        self.output: List[str] = []
        self.errors: List[dict] = []
        self._env = Environment()
        self._iteration_count = 0

    def execute(self, program: Program):
        for stmt in program.statements:
            self._exec_stmt(stmt)

    def _exec_stmt(self, node: ASTNode):
        try:
            if isinstance(node, VarDecl):
                val = self._eval(node.init) if node.init else self._default(node.dtype)
                self._env.set(node.name, val)

            elif isinstance(node, Assignment):
                val = self._eval(node.value)
                try:
                    self._env.update(node.name, val)
                except KeyError:
                    # Assign even if not declared (interpreter is lenient)
                    self._env.set(node.name, val)

            elif isinstance(node, PrintStmt):
                val = self._eval(node.expr)
                self.output.append(str(val))

            elif isinstance(node, IfStmt):
                cond = self._eval(node.condition)
                if self._truthy(cond):
                    env_prev = self._env
                    self._env = Environment(parent=self._env)
                    for s in node.then_block:
                        self._exec_stmt(s)
                    self._env = env_prev
                elif node.else_block:
                    env_prev = self._env
                    self._env = Environment(parent=self._env)
                    for s in node.else_block:
                        self._exec_stmt(s)
                    self._env = env_prev

            elif isinstance(node, WhileStmt):
                iterations = 0
                while self._truthy(self._eval(node.condition)):
                    iterations += 1
                    if iterations > MAX_ITERATIONS:
                        self.errors.append({
                            "type": "RuntimeError",
                            "message": f"Execution halted: exceeded {MAX_ITERATIONS} iterations (possible infinite loop)",
                            "line": node.line,
                            "suggestion": "Ensure the loop condition eventually becomes false"
                        })
                        break
                    env_prev = self._env
                    self._env = Environment(parent=self._env)
                    for s in node.body:
                        self._exec_stmt(s)
                    self._env = env_prev

        except RuntimeError_ as e:
            self.errors.append({
                "type": "RuntimeError",
                "message": str(e),
                "line": e.line,
                "suggestion": "Check runtime values"
            })
        except Exception as e:
            self.errors.append({
                "type": "RuntimeError",
                "message": str(e),
                "line": getattr(node, 'line', 0),
                "suggestion": ""
            })

    def _eval(self, node: ASTNode) -> Any:
        if isinstance(node, Literal):
            return node.value

        if isinstance(node, Identifier):
            try:
                return self._env.get(node.name)
            except KeyError:
                raise RuntimeError_(f"Undefined variable '{node.name}'", node.line)

        if isinstance(node, BinaryOp):
            l = self._eval(node.left)
            r = self._eval(node.right)
            op = node.op
            try:
                if op == '+':  return l + r
                if op == '-':  return l - r
                if op == '*':  return l * r
                if op == '/':
                    if r == 0:
                        raise RuntimeError_("Division by zero", node.line)
                    return l / r if isinstance(l, float) or isinstance(r, float) else l // r
                if op == '%':
                    if r == 0:
                        raise RuntimeError_("Modulo by zero", node.line)
                    return l % r
                if op == '<':  return l < r
                if op == '>':  return l > r
                if op == '<=': return l <= r
                if op == '>=': return l >= r
                if op == '==': return l == r
                if op == '!=': return l != r
                if op == '&&': return bool(l) and bool(r)
                if op == '||': return bool(l) or bool(r)
            except RuntimeError_:
                raise
            except Exception as e:
                raise RuntimeError_(f"Operation error: {e}", node.line)

        if isinstance(node, UnaryOp):
            val = self._eval(node.operand)
            if node.op == '-': return -val
            if node.op == '!': return not val

        return None

    def _truthy(self, val: Any) -> bool:
        if isinstance(val, bool): return val
        if isinstance(val, (int, float)): return val != 0
        if isinstance(val, str): return len(val) > 0
        return bool(val)

    def _default(self, dtype: str) -> Any:
        return {'int': 0, 'float': 0.0, 'string': '', 'bool': False}.get(dtype, None)
