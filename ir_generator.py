"""
SentinelX Intermediate Representation Generator
Generates Three-Address Code (TAC) from the AST, then applies optimizations.

Optimizations implemented:
  1. Constant Folding       — evaluate constant expressions at compile time
  2. Constant Propagation   — replace variable uses with known constant values
  3. Dead Code Elimination  — remove assignments to variables never used after
  4. Strength Reduction     — x*2 → x+x, x**2 → x*x (simple cases)
"""

from typing import List, Optional, Tuple, Dict, Any
from .ast_nodes import *


class TACInstruction:
    def __init__(self, op: str, dest=None, arg1=None, arg2=None, label=None, comment=""):
        self.op = op          # 'assign', 'binop', 'unop', 'goto', 'if_false', 'label',
                              # 'print', 'param', 'call'
        self.dest = dest
        self.arg1 = arg1
        self.arg2 = arg2
        self.label = label
        self.comment = comment

    def __repr__(self):
        if self.op == 'label':
            return f"{self.label}:"
        if self.op == 'assign':
            return f"    {self.dest} = {self.arg1}"
        if self.op == 'binop':
            return f"    {self.dest} = {self.arg1} {self.label} {self.arg2}"
        if self.op == 'unop':
            return f"    {self.dest} = {self.label}{self.arg1}"
        if self.op == 'if_false':
            return f"    if_false {self.arg1} goto {self.label}"
        if self.op == 'goto':
            return f"    goto {self.label}"
        if self.op == 'print':
            return f"    print {self.arg1}"
        return f"    {self.op} {self.dest or ''} {self.arg1 or ''} {self.arg2 or ''}"

    def to_dict(self):
        return {
            "op": self.op,
            "dest": self.dest,
            "arg1": str(self.arg1) if self.arg1 is not None else None,
            "arg2": str(self.arg2) if self.arg2 is not None else None,
            "label": self.label,
            "text": repr(self)
        }


class TACGenerator:
    def __init__(self):
        self.code: List[TACInstruction] = []
        self._temp_count = 0
        self._label_count = 0

    def _new_temp(self) -> str:
        self._temp_count += 1
        return f"t{self._temp_count}"

    def _new_label(self) -> str:
        self._label_count += 1
        return f"L{self._label_count}"

    def emit(self, instr: TACInstruction):
        self.code.append(instr)

    def generate(self, program: Program):
        for stmt in program.statements:
            self._gen_stmt(stmt)

    def _gen_stmt(self, node: ASTNode):
        if isinstance(node, VarDecl):
            if node.init:
                val = self._gen_expr(node.init)
                self.emit(TACInstruction('assign', dest=node.name, arg1=val))
            else:
                self.emit(TACInstruction('assign', dest=node.name, arg1=0))

        elif isinstance(node, Assignment):
            val = self._gen_expr(node.value)
            self.emit(TACInstruction('assign', dest=node.name, arg1=val))

        elif isinstance(node, PrintStmt):
            val = self._gen_expr(node.expr)
            self.emit(TACInstruction('print', arg1=val))

        elif isinstance(node, IfStmt):
            cond = self._gen_expr(node.condition)
            else_label = self._new_label()
            end_label = self._new_label()
            self.emit(TACInstruction('if_false', arg1=cond, label=else_label))
            for s in node.then_block:
                self._gen_stmt(s)
            if node.else_block:
                self.emit(TACInstruction('goto', label=end_label))
            self.emit(TACInstruction('label', label=else_label))
            if node.else_block:
                for s in node.else_block:
                    self._gen_stmt(s)
                self.emit(TACInstruction('label', label=end_label))

        elif isinstance(node, WhileStmt):
            start_label = self._new_label()
            end_label = self._new_label()
            self.emit(TACInstruction('label', label=start_label))
            cond = self._gen_expr(node.condition)
            self.emit(TACInstruction('if_false', arg1=cond, label=end_label))
            for s in node.body:
                self._gen_stmt(s)
            self.emit(TACInstruction('goto', label=start_label))
            self.emit(TACInstruction('label', label=end_label))

    def _gen_expr(self, node: ASTNode) -> Any:
        if isinstance(node, Literal):
            if node.dtype == 'string':
                return f'"{node.value}"'
            return node.value

        if isinstance(node, Identifier):
            return node.name

        if isinstance(node, BinaryOp):
            l = self._gen_expr(node.left)
            r = self._gen_expr(node.right)
            t = self._new_temp()
            self.emit(TACInstruction('binop', dest=t, arg1=l, arg2=r, label=node.op))
            return t

        if isinstance(node, UnaryOp):
            val = self._gen_expr(node.operand)
            t = self._new_temp()
            self.emit(TACInstruction('unop', dest=t, arg1=val, label=node.op))
            return t

        return "?"

    def get_code_strings(self) -> List[str]:
        return [repr(i) for i in self.code]


# ── Optimizer ─────────────────────────────────────────────────────────────────

class Optimizer:
    def __init__(self, code: List[TACInstruction]):
        self.original = [repr(i) for i in code]
        self.code = [TACInstruction(
            i.op, i.dest, i.arg1, i.arg2, i.label, i.comment
        ) for i in code]
        self.optimizations: List[dict] = []

    def _is_const(self, val) -> bool:
        if val is None: return False
        try:
            float(str(val))
            return True
        except:
            return False

    def _const_val(self, val):
        try:
            f = float(str(val))
            return int(f) if f == int(f) else f
        except:
            return val

    def constant_folding(self):
        """Evaluate binop/unop with literal operands at compile time."""
        for instr in self.code:
            if instr.op == 'binop' and self._is_const(instr.arg1) and self._is_const(instr.arg2):
                a = self._const_val(instr.arg1)
                b = self._const_val(instr.arg2)
                op = instr.label
                result = None
                try:
                    if op == '+':  result = a + b
                    elif op == '-': result = a - b
                    elif op == '*': result = a * b
                    elif op == '/' and b != 0: result = a / b
                    elif op == '%' and b != 0: result = a % b
                    elif op == '<':  result = a < b
                    elif op == '>':  result = a > b
                    elif op == '<=': result = a <= b
                    elif op == '>=': result = a >= b
                    elif op == '==': result = a == b
                    elif op == '!=': result = a != b
                except: pass
                if result is not None:
                    old = repr(instr)
                    instr.op = 'assign'
                    instr.arg1 = int(result) if isinstance(result, float) and result == int(result) else result
                    instr.arg2 = None
                    instr.label = None
                    self.optimizations.append({
                        "type": "Constant Folding",
                        "before": old.strip(),
                        "after": repr(instr).strip(),
                        "explanation": f"Evaluated '{a} {op} {b}' at compile time → {result}"
                    })

            elif instr.op == 'unop' and self._is_const(instr.arg1):
                a = self._const_val(instr.arg1)
                op = instr.label
                result = None
                if op == '-': result = -a
                elif op == '!': result = not a
                if result is not None:
                    old = repr(instr)
                    instr.op = 'assign'
                    instr.arg1 = result
                    instr.arg2 = None
                    instr.label = None
                    self.optimizations.append({
                        "type": "Constant Folding",
                        "before": old.strip(),
                        "after": repr(instr).strip(),
                        "explanation": f"Evaluated '{op}{a}' at compile time → {result}"
                    })

    def constant_propagation(self):
        """Replace uses of known-constant variables."""
        const_map: Dict[str, Any] = {}
        for instr in self.code:
            if instr.op == 'assign' and self._is_const(instr.arg1):
                const_map[instr.dest] = self._const_val(instr.arg1)
            elif instr.op in ('assign', 'binop', 'unop'):
                # Propagate in args
                for attr in ('arg1', 'arg2'):
                    val = getattr(instr, attr)
                    if val is not None and str(val) in const_map:
                        old = repr(instr)
                        setattr(instr, attr, const_map[str(val)])
                        self.optimizations.append({
                            "type": "Constant Propagation",
                            "before": old.strip(),
                            "after": repr(instr).strip(),
                            "explanation": f"Replaced '{val}' with its known constant value {const_map[str(val)]}"
                        })
                # If dest is reassigned with non-const, remove from map
                if instr.dest and instr.dest in const_map:
                    if not (instr.op == 'assign' and self._is_const(instr.arg1)):
                        del const_map[instr.dest]

    def dead_code_elimination(self):
        """Remove assignments to temporaries that are never used."""
        # Count uses of each dest
        defined = {}
        used = set()
        for i, instr in enumerate(self.code):
            if instr.dest and instr.dest.startswith('t'):
                defined[instr.dest] = i
            for attr in ('arg1', 'arg2'):
                val = getattr(instr, attr)
                if val is not None and str(val).startswith('t'):
                    used.add(str(val))

        dead = [i for dest, i in defined.items() if dest not in used]
        for i in sorted(dead, reverse=True):
            instr = self.code[i]
            self.optimizations.append({
                "type": "Dead Code Elimination",
                "before": repr(instr).strip(),
                "after": "(removed)",
                "explanation": f"Temporary '{instr.dest}' is assigned but never used"
            })
        self.code = [instr for i, instr in enumerate(self.code) if i not in dead]

    def strength_reduction(self):
        """Replace expensive operations with cheaper equivalents."""
        for instr in self.code:
            if instr.op == 'binop':
                # x * 1 → x, x * 0 → 0, x + 0 → x
                if instr.label == '*':
                    if str(instr.arg2) == '1':
                        old = repr(instr)
                        instr.op = 'assign'
                        instr.arg2 = None
                        instr.label = None
                        self.optimizations.append({
                            "type": "Strength Reduction",
                            "before": old.strip(),
                            "after": repr(instr).strip(),
                            "explanation": "x * 1 → x (identity elimination)"
                        })
                    elif str(instr.arg2) == '0' or str(instr.arg1) == '0':
                        old = repr(instr)
                        instr.op = 'assign'
                        instr.arg1 = 0
                        instr.arg2 = None
                        instr.label = None
                        self.optimizations.append({
                            "type": "Strength Reduction",
                            "before": old.strip(),
                            "after": repr(instr).strip(),
                            "explanation": "x * 0 → 0 (zero multiplication)"
                        })
                    elif str(instr.arg2) == '2':
                        old = repr(instr)
                        v = instr.arg1
                        instr.op = 'binop'
                        instr.arg2 = v
                        instr.label = '+'
                        self.optimizations.append({
                            "type": "Strength Reduction",
                            "before": old.strip(),
                            "after": repr(instr).strip(),
                            "explanation": "x * 2 → x + x (cheaper addition)"
                        })
                elif instr.label == '+' and (str(instr.arg2) == '0' or str(instr.arg1) == '0'):
                    old = repr(instr)
                    keep = instr.arg1 if str(instr.arg2) == '0' else instr.arg2
                    instr.op = 'assign'
                    instr.arg1 = keep
                    instr.arg2 = None
                    instr.label = None
                    self.optimizations.append({
                        "type": "Strength Reduction",
                        "before": old.strip(),
                        "after": repr(instr).strip(),
                        "explanation": "x + 0 → x (additive identity)"
                    })

    def run_all(self) -> List[TACInstruction]:
        self.constant_folding()
        self.constant_propagation()
        self.constant_folding()  # second pass after propagation
        self.strength_reduction()
        self.dead_code_elimination()
        return self.code

    def get_report(self) -> dict:
        return {
            "original": self.original,
            "optimized": [repr(i) for i in self.code],
            "optimizations": self.optimizations,
            "count": len(self.optimizations)
        }
