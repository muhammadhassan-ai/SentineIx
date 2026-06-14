SentinelX — Mini Compiler Assistant
A fully functional compiler for a statically-typed mini language, with a browser-based IDE. Implements all 6 classical compiler phases: lexing → parsing → semantic analysis → IR generation → optimization → execution.

Built as a course project for Compiler Construction (CSC6605) at Lahore Garrison University.

Live Demo
Input source code in the browser → inspect every compilation stage in real time.

Ctrl+Enter — Compile & Run

Compiler Pipeline
All 6 phases run on every compile. Results for each phase are returned as JSON and displayed in the IDE.

Phase	File	Output
1. Lexical Analysis	compiler/lexer.py	Token stream with line/col tracking
2. Syntax Analysis	compiler/parser.py	Abstract Syntax Tree (recursive descent)
3. Semantic Analysis	compiler/semantic.py	Symbol table, type errors, warnings
4. IR Generation	compiler/ir_generator.py	Three-address code (TAC)
5. Optimization	compiler/ir_generator.py	Optimized TAC + optimization report
6. Execution	compiler/interpreter.py	Program output (tree-walking interpreter)
Optimization Passes
The optimizer runs 4 passes in sequence:

Constant Folding — evaluates compile-time expressions (3 + 4 → 7)
Constant Propagation — substitutes known constant values into expressions
Dead Code Elimination — removes unreachable or unused instructions
Strength Reduction — replaces expensive operations with cheaper equivalents
Constant folding runs twice (before and after propagation) to catch newly constant expressions.

Language Features
// Types
int x = 5;
float pi = 3.14;
string name = "SentinelX";
bool flag = true;

// Control flow
if (x < 10) {
    print(x);
} else {
    print("big");
}

// Loops (with 10,000 iteration guard)
while (i < 8) {
    print(i);
    i = i + 1;
}

// Operators
// Arithmetic : + - * / %
// Comparison : == != < > <= >=
// Logical    : && || !
Errors Detected
Stage	Errors
Lexical	Unknown/invalid characters
Syntax	Missing ;, {, ), malformed expressions
Semantic	Duplicate declarations, undeclared variables, type mismatches
Runtime	Division by zero, infinite loop (>10,000 iterations)
Project Structure
sentinelx/
├── app.py                    # Flask backend — single POST /api/compile endpoint
├── requirements.txt
├── compiler/
│   ├── __init__.py
│   ├── lexer.py              # Regex-based tokenizer with line/column tracking
│   ├── parser.py             # Recursive descent parser → AST
│   ├── ast_nodes.py          # AST node dataclasses + JSON serializer
│   ├── semantic.py           # Type checker + symbol table builder
│   ├── ir_generator.py       # TAC generator + 4-pass optimizer
│   ├── interpreter.py        # Tree-walking interpreter
│   └── pipeline.py           # Orchestrates all 6 phases → unified JSON result
└── templates/
    └── index.html            # Full IDE UI (single file, no build step required)
Quick Start
Prerequisites
Python 3.8+
pip
1. Clone the repository
git clone https://github.com/muhammadhassan-ai/machine-learning-project.git
cd sentinelx
2. Install dependencies
pip install -r requirements.txt
3. Run
python app.py
# Open http://localhost:5000
API
POST /api/compile

Request:

{ "source": "int x = 3 + 4; print(x);" }
Response — returns all 6 phase results:

{
  "success": true,
  "output": ["7"],
  "errors": [],
  "warnings": [],
  "phases": {
    "lexer":        { "tokens": [...], "token_count": 12, "errors": [] },
    "parser":       { "ast": {...}, "errors": [] },
    "semantic":     { "symbol_table": {...}, "errors": [], "warnings": [] },
    "ir":           { "original": [...], "optimized": [...] },
    "optimization": { "optimizations": [...], "count": 2 },
    "execution":    { "output": ["7"], "errors": [] }
  }
}
Built-in Samples
Hit /api/sample/<name> to load example programs:

Name	Demonstrates
hello	Basic arithmetic and print
fibonacci	While loop, variable reassignment
conditions	Nested if-else
optimization	Constant folding and propagation
types	All 4 supported types
errors	Duplicate declaration, type mismatch, undeclared variable
Author
Muhammad Hassan BSCS — Lahore Garrison University github.com/muhammadhassan-ai · LinkedIn
