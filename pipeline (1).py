"""
SentinelX Compiler Pipeline
Orchestrates all phases and returns a unified JSON result.
"""

from .lexer import Lexer
from .parser import Parser
from .semantic import SemanticAnalyzer
from .ir_generator import TACGenerator, Optimizer
from .interpreter import Interpreter
from .ast_nodes import ast_to_dict


def compile_and_run(source: str) -> dict:
    result = {
        "source": source,
        "phases": {},
        "errors": [],
        "warnings": [],
        "output": [],
        "success": False
    }

    # ── Phase 1: Lexical Analysis ──────────────────────────────────────────────
    lexer = Lexer(source)
    tokens = lexer.tokenize()
    token_table = lexer.get_token_table()

    result["phases"]["lexer"] = {
        "name": "Lexical Analysis",
        "tokens": token_table,
        "token_count": len(token_table),
        "errors": lexer.errors
    }
    result["errors"].extend(lexer.errors)

    if lexer.errors:
        # Don't stop — try to parse anyway with error tokens filtered
        pass

    # ── Phase 2: Parsing ───────────────────────────────────────────────────────
    parser = Parser(tokens)
    ast = parser.parse()
    ast_dict = ast_to_dict(ast)

    result["phases"]["parser"] = {
        "name": "Syntax Analysis",
        "ast": ast_dict,
        "errors": parser.errors
    }
    result["errors"].extend(parser.errors)

    if parser.errors and not ast.statements:
        return result

    # ── Phase 3: Semantic Analysis + Type Checking ────────────────────────────
    sem = SemanticAnalyzer()
    sem.analyze(ast)

    sem_errors = sem.all_errors()
    sem_only_errors = [e for e in sem_errors if not e["type"].startswith("Warning:")]
    warnings = [e for e in sem_errors if e["type"].startswith("Warning:")]

    result["phases"]["semantic"] = {
        "name": "Semantic Analysis & Type Checking",
        "symbol_table": sem.get_symbol_table(),
        "errors": sem_only_errors,
        "warnings": warnings
    }
    result["errors"].extend(sem_only_errors)
    result["warnings"].extend(warnings)

    # ── Phase 4: IR / TAC Generation ──────────────────────────────────────────
    tac_gen = TACGenerator()
    tac_gen.generate(ast)
    original_tac = tac_gen.get_code_strings()

    # ── Phase 5: Optimization ─────────────────────────────────────────────────
    optimizer = Optimizer(tac_gen.code)
    optimized_code = optimizer.run_all()
    opt_report = optimizer.get_report()

    result["phases"]["ir"] = {
        "name": "Intermediate Representation (3-Address Code)",
        "original": original_tac,
        "optimized": opt_report["optimized"],
    }
    result["phases"]["optimization"] = {
        "name": "Optimization",
        "optimizations": opt_report["optimizations"],
        "count": opt_report["count"]
    }

    # ── Phase 6: Interpretation / Execution ───────────────────────────────────
    interp = Interpreter()
    if not sem_only_errors:  # only run if no semantic errors
        interp.execute(ast)

    result["phases"]["execution"] = {
        "name": "Execution",
        "output": interp.output,
        "errors": interp.errors
    }
    result["output"] = interp.output
    result["errors"].extend(interp.errors)

    result["success"] = len(result["errors"]) == 0
    return result
