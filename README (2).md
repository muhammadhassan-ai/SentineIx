# SentinelX — Smart Compiler Assistant

A complete mini compiler frontend with a professional browser-based IDE.

## Quick Start

```bash
pip install flask flask-cors
python app.py
# Open http://localhost:5000
```

## Project Structure

```
sentinelx/
├── app.py                   # Flask backend & API
├── requirements.txt
├── compiler/
│   ├── lexer.py             # Tokenizer (regex-based, line/col tracking)
│   ├── parser.py            # Recursive descent parser + AST builder
│   ├── ast_nodes.py         # All AST node dataclasses + JSON serializer
│   ├── semantic.py          # Semantic analyzer + type checker + symbol table
│   ├── ir_generator.py      # TAC generator + 4-pass optimizer
│   ├── interpreter.py       # Tree-walking interpreter (executes AST)
│   └── pipeline.py          # Orchestrates all 6 phases → JSON result
└── templates/
    └── index.html           # Full IDE UI (single file, no build step)
```

## Language Features

```
// Types
int x = 5;
float pi = 3.14;
string name = "SentinelX";
bool flag = true;

// Control flow
if (x < 10) { print(x); } else { print("big"); }

// Loops
while (i < 8) { print(i); i = i + 1; }

// Operators: + - * / %  == != < > <= >=  && ||  !
```

## API

`POST /api/compile`
```json
{ "source": "int x = 3 + 4; print(x);" }
```

Returns all phase results: tokens, AST, semantic errors, symbol table, IR, optimizations, output.

## Keyboard Shortcut

`Ctrl+Enter` — Compile & Run

## Compiler Phases

| Phase | File | Output |
|-------|------|--------|
| Lexical Analysis | `lexer.py` | Token stream |
| Syntax Analysis | `parser.py` | AST |
| Semantic Analysis | `semantic.py` | Type errors, symbol table |
| IR Generation | `ir_generator.py` | Three-address code |
| Optimization | `ir_generator.py` | Optimized TAC + report |
| Execution | `interpreter.py` | Program output |

## Errors Detected

- Lexical: unknown characters
- Syntax: missing `;`, `{`, `)`, invalid tokens
- Semantic: duplicate declarations, undeclared variables
- Type: mismatched assignments and operations
- Runtime: division by zero, infinite loop guard (10,000 iter limit)
