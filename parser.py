"""
SentinelX Parser — Recursive Descent
Grammar:
  program      → statement* EOF
  statement    → varDecl | assignment | ifStmt | whileStmt | printStmt
  varDecl      → TYPE IDENT ('=' expr)? ';'
  assignment   → IDENT '=' expr ';'
  ifStmt       → 'if' '(' expr ')' block ('else' block)?
  whileStmt    → 'while' '(' expr ')' block
  printStmt    → 'print' '(' expr ')' ';'
  block        → '{' statement* '}'
  expr         → logicOr
  logicOr      → logicAnd ('||' logicAnd)*
  logicAnd     → equality ('&&' equality)*
  equality     → comparison (('==' | '!=') comparison)*
  comparison   → addition (('<' | '>' | '<=' | '>=') addition)*
  addition     → multiplication (('+' | '-') multiplication)*
  multiplication → unary (('*' | '/' | '%') unary)*
  unary        → ('!' | '-') unary | primary
  primary      → FLOAT_LIT | INT_LIT | STRING_LIT | BOOL_LIT | IDENT | '(' expr ')'
"""

from typing import List, Optional
from .lexer import Token, TokenType
from .ast_nodes import *


class ParseError(Exception):
    def __init__(self, msg: str, line: int, col: int, suggestion: str = ""):
        super().__init__(msg)
        self.line = line
        self.col = col
        self.suggestion = suggestion


TYPE_TOKENS = {TokenType.INT, TokenType.FLOAT, TokenType.STRING, TokenType.BOOL}
TYPE_MAP = {
    TokenType.INT: 'int',
    TokenType.FLOAT: 'float',
    TokenType.STRING: 'string',
    TokenType.BOOL: 'bool',
}


class Parser:
    def __init__(self, tokens: List[Token]):
        self.tokens = [t for t in tokens if t.type != TokenType.ERROR]
        self.pos = 0
        self.errors: List[dict] = []

    # ── Helpers ───────────────────────────────────────────────────────────────

    @property
    def current(self) -> Token:
        return self.tokens[self.pos]

    def peek(self, offset=1) -> Token:
        i = self.pos + offset
        if i < len(self.tokens):
            return self.tokens[i]
        return self.tokens[-1]  # EOF

    def advance(self) -> Token:
        tok = self.tokens[self.pos]
        if tok.type != TokenType.EOF:
            self.pos += 1
        return tok

    def check(self, *types: TokenType) -> bool:
        return self.current.type in types

    def match(self, *types: TokenType) -> Optional[Token]:
        if self.check(*types):
            return self.advance()
        return None

    def expect(self, ttype: TokenType, msg: str, suggestion: str = "") -> Token:
        if self.check(ttype):
            return self.advance()
        tok = self.current
        self._error(msg, tok, suggestion)
        # Error recovery: skip until we find something useful
        return tok

    def _error(self, msg: str, tok: Token, suggestion: str = ""):
        self.errors.append({
            "type": "SyntaxError",
            "message": msg,
            "line": tok.line,
            "col": tok.col,
            "token": tok.value,
            "suggestion": suggestion or "Check syntax near this location"
        })

    def synchronize(self):
        """Panic-mode error recovery: skip to next statement boundary."""
        while not self.check(TokenType.EOF):
            if self.current.type == TokenType.SEMICOLON:
                self.advance()
                return
            if self.current.type in (TokenType.RBRACE, TokenType.IF,
                                      TokenType.WHILE, TokenType.PRINT,
                                      *TYPE_TOKENS):
                return
            self.advance()

    # ── Entry point ───────────────────────────────────────────────────────────

    def parse(self) -> Program:
        stmts = []
        while not self.check(TokenType.EOF):
            stmt = self._statement()
            if stmt:
                stmts.append(stmt)
        return Program(statements=stmts)

    # ── Statements ────────────────────────────────────────────────────────────

    def _statement(self) -> Optional[ASTNode]:
        try:
            if self.check(*TYPE_TOKENS):
                return self._var_decl()
            if self.check(TokenType.IF):
                return self._if_stmt()
            if self.check(TokenType.WHILE):
                return self._while_stmt()
            if self.check(TokenType.PRINT):
                return self._print_stmt()
            if self.check(TokenType.IDENT):
                return self._assignment()
            # Unexpected token
            tok = self.current
            self._error(
                f"Unexpected token '{tok.value}'",
                tok,
                "Expected a statement: variable declaration, if, while, print, or assignment"
            )
            self.synchronize()
            return None
        except ParseError:
            self.synchronize()
            return None

    def _var_decl(self) -> VarDecl:
        type_tok = self.advance()
        dtype = TYPE_MAP[type_tok.type]
        name_tok = self.expect(
            TokenType.IDENT,
            f"Expected variable name after '{dtype}'",
            f"Example: {dtype} myVar;"
        )
        init = None
        if self.match(TokenType.ASSIGN):
            init = self._expr()
        self.expect(
            TokenType.SEMICOLON,
            f"Missing ';' after variable declaration '{name_tok.value}'",
            f"Add ';' at end: {dtype} {name_tok.value} = ...;"
        )
        return VarDecl(dtype=dtype, name=name_tok.value, init=init, line=type_tok.line)

    def _assignment(self) -> Assignment:
        name_tok = self.advance()
        self.expect(
            TokenType.ASSIGN,
            f"Expected '=' after '{name_tok.value}'",
            "Use '=' for assignment, '==' for comparison"
        )
        val = self._expr()
        self.expect(
            TokenType.SEMICOLON,
            f"Missing ';' after assignment to '{name_tok.value}'",
            f"Add ';': {name_tok.value} = ...;"
        )
        return Assignment(name=name_tok.value, value=val, line=name_tok.line)

    def _if_stmt(self) -> IfStmt:
        line = self.current.line
        self.advance()  # 'if'
        self.expect(TokenType.LPAREN, "Expected '(' after 'if'", "Syntax: if (condition) { ... }")
        cond = self._expr()
        self.expect(TokenType.RPAREN, "Expected ')' to close if-condition", "Add missing ')'")
        then_block = self._block()
        else_block = None
        if self.match(TokenType.ELSE):
            else_block = self._block()
        return IfStmt(condition=cond, then_block=then_block, else_block=else_block, line=line)

    def _while_stmt(self) -> WhileStmt:
        line = self.current.line
        self.advance()  # 'while'
        self.expect(TokenType.LPAREN, "Expected '(' after 'while'", "Syntax: while (condition) { ... }")
        cond = self._expr()
        self.expect(TokenType.RPAREN, "Expected ')' to close while-condition", "Add missing ')'")
        body = self._block()
        return WhileStmt(condition=cond, body=body, line=line)

    def _print_stmt(self) -> PrintStmt:
        line = self.current.line
        self.advance()  # 'print'
        self.expect(TokenType.LPAREN, "Expected '(' after 'print'", "Syntax: print(expr);")
        expr = self._expr()
        self.expect(TokenType.RPAREN, "Expected ')' to close print()", "Add missing ')'")
        self.expect(TokenType.SEMICOLON, "Missing ';' after print statement", "Add ';' at end")
        return PrintStmt(expr=expr, line=line)

    def _block(self) -> List[ASTNode]:
        self.expect(TokenType.LBRACE, "Expected '{' to open block", "Wrap statements in { ... }")
        stmts = []
        while not self.check(TokenType.RBRACE, TokenType.EOF):
            stmt = self._statement()
            if stmt:
                stmts.append(stmt)
        self.expect(TokenType.RBRACE, "Expected '}' to close block", "Add missing '}'")
        return stmts

    # ── Expressions ───────────────────────────────────────────────────────────

    def _expr(self) -> ASTNode:
        return self._logic_or()

    def _logic_or(self) -> ASTNode:
        left = self._logic_and()
        while self.check(TokenType.OR):
            op_tok = self.advance()
            right = self._logic_and()
            left = BinaryOp(op='||', left=left, right=right, line=op_tok.line)
        return left

    def _logic_and(self) -> ASTNode:
        left = self._equality()
        while self.check(TokenType.AND):
            op_tok = self.advance()
            right = self._equality()
            left = BinaryOp(op='&&', left=left, right=right, line=op_tok.line)
        return left

    def _equality(self) -> ASTNode:
        left = self._comparison()
        while self.check(TokenType.EQ, TokenType.NEQ):
            op_tok = self.advance()
            right = self._comparison()
            left = BinaryOp(op=op_tok.value, left=left, right=right, line=op_tok.line)
        return left

    def _comparison(self) -> ASTNode:
        left = self._addition()
        while self.check(TokenType.LT, TokenType.GT, TokenType.LTE, TokenType.GTE):
            op_tok = self.advance()
            right = self._addition()
            left = BinaryOp(op=op_tok.value, left=left, right=right, line=op_tok.line)
        return left

    def _addition(self) -> ASTNode:
        left = self._multiplication()
        while self.check(TokenType.PLUS, TokenType.MINUS):
            op_tok = self.advance()
            right = self._multiplication()
            left = BinaryOp(op=op_tok.value, left=left, right=right, line=op_tok.line)
        return left

    def _multiplication(self) -> ASTNode:
        left = self._unary()
        while self.check(TokenType.STAR, TokenType.SLASH, TokenType.PERCENT):
            op_tok = self.advance()
            right = self._unary()
            left = BinaryOp(op=op_tok.value, left=left, right=right, line=op_tok.line)
        return left

    def _unary(self) -> ASTNode:
        if self.check(TokenType.NOT):
            op_tok = self.advance()
            return UnaryOp(op='!', operand=self._unary(), line=op_tok.line)
        if self.check(TokenType.MINUS):
            op_tok = self.advance()
            return UnaryOp(op='-', operand=self._unary(), line=op_tok.line)
        return self._primary()

    def _primary(self) -> ASTNode:
        tok = self.current

        if tok.type == TokenType.FLOAT_LIT:
            self.advance()
            return Literal(value=float(tok.value), dtype='float', line=tok.line)

        if tok.type == TokenType.INT_LIT:
            self.advance()
            return Literal(value=int(tok.value), dtype='int', line=tok.line)

        if tok.type == TokenType.STRING_LIT:
            self.advance()
            return Literal(value=tok.value[1:-1], dtype='string', line=tok.line)

        if tok.type == TokenType.BOOL_LIT:
            self.advance()
            return Literal(value=tok.value == 'true', dtype='bool', line=tok.line)

        if tok.type == TokenType.IDENT:
            self.advance()
            return Identifier(name=tok.value, line=tok.line)

        if tok.type == TokenType.LPAREN:
            self.advance()
            expr = self._expr()
            self.expect(TokenType.RPAREN, "Expected ')' to close expression", "Add missing ')'")
            return expr

        self._error(
            f"Unexpected token '{tok.value}' in expression",
            tok,
            "Expected a value: number, string, variable, or (expression)"
        )
        raise ParseError("Unexpected token", tok.line, tok.col)
