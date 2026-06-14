"""
SentinelX Lexical Analyzer
Tokenizes source code into a stream of tokens with line/column tracking.
"""

import re
from dataclasses import dataclass
from typing import List, Optional
from enum import Enum, auto


class TokenType(Enum):
    # Literals
    INT_LIT    = auto()
    FLOAT_LIT  = auto()
    STRING_LIT = auto()
    BOOL_LIT   = auto()
    # Types
    INT        = auto()
    FLOAT      = auto()
    STRING     = auto()
    BOOL       = auto()
    # Keywords
    IF         = auto()
    ELSE       = auto()
    WHILE      = auto()
    PRINT      = auto()
    TRUE       = auto()
    FALSE      = auto()
    # Identifiers
    IDENT      = auto()
    # Operators
    PLUS       = auto()
    MINUS      = auto()
    STAR       = auto()
    SLASH      = auto()
    PERCENT    = auto()
    EQ         = auto()   # ==
    NEQ        = auto()   # !=
    LT         = auto()   # <
    GT         = auto()   # >
    LTE        = auto()   # <=
    GTE        = auto()   # >=
    AND        = auto()   # &&
    OR         = auto()   # ||
    NOT        = auto()   # !
    ASSIGN     = auto()   # =
    # Delimiters
    LPAREN     = auto()
    RPAREN     = auto()
    LBRACE     = auto()
    RBRACE     = auto()
    SEMICOLON  = auto()
    # Special
    EOF        = auto()
    ERROR      = auto()


@dataclass
class Token:
    type: TokenType
    value: str
    line: int
    col: int

    def __repr__(self):
        return f"Token({self.type.name}, {self.value!r}, line={self.line}, col={self.col})"


# Token specification: (pattern, TokenType or None to skip)
TOKEN_SPEC = [
    (r'[ \t]+',               None),           # whitespace
    (r'\n',                   None),           # newline (tracked separately)
    (r'//[^\n]*',             None),           # line comment
    (r'/\*[\s\S]*?\*/',       None),           # block comment
    (r'\d+\.\d+',             TokenType.FLOAT_LIT),
    (r'\d+',                  TokenType.INT_LIT),
    (r'"[^"]*"',              TokenType.STRING_LIT),
    (r'true\b',               TokenType.BOOL_LIT),
    (r'false\b',              TokenType.BOOL_LIT),
    (r'int\b',                TokenType.INT),
    (r'float\b',              TokenType.FLOAT),
    (r'string\b',             TokenType.STRING),
    (r'bool\b',               TokenType.BOOL),
    (r'if\b',                 TokenType.IF),
    (r'else\b',               TokenType.ELSE),
    (r'while\b',              TokenType.WHILE),
    (r'print\b',              TokenType.PRINT),
    (r'[A-Za-z_]\w*',         TokenType.IDENT),
    (r'==',                   TokenType.EQ),
    (r'!=',                   TokenType.NEQ),
    (r'<=',                   TokenType.LTE),
    (r'>=',                   TokenType.GTE),
    (r'<',                    TokenType.LT),
    (r'>',                    TokenType.GT),
    (r'&&',                   TokenType.AND),
    (r'\|\|',                 TokenType.OR),
    (r'!',                    TokenType.NOT),
    (r'=',                    TokenType.ASSIGN),
    (r'\+',                   TokenType.PLUS),
    (r'-',                    TokenType.MINUS),
    (r'\*',                   TokenType.STAR),
    (r'/',                    TokenType.SLASH),
    (r'%',                    TokenType.PERCENT),
    (r'\(',                   TokenType.LPAREN),
    (r'\)',                   TokenType.RPAREN),
    (r'\{',                   TokenType.LBRACE),
    (r'\}',                   TokenType.RBRACE),
    (r';',                    TokenType.SEMICOLON),
]

MASTER_PATTERN = re.compile(
    '|'.join(f'(?P<tok{i}>{pat})' for i, (pat, _) in enumerate(TOKEN_SPEC)),
    re.DOTALL
)


class LexerError(Exception):
    def __init__(self, msg, line, col):
        super().__init__(msg)
        self.line = line
        self.col = col


class Lexer:
    def __init__(self, source: str):
        self.source = source
        self.tokens: List[Token] = []
        self.errors: List[dict] = []
        self._line = 1
        self._line_start = 0

    def tokenize(self) -> List[Token]:
        pos = 0
        src = self.source
        tokens = []
        errors = []

        while pos < len(src):
            m = MASTER_PATTERN.match(src, pos)
            if m:
                matched_text = m.group()
                # Track newlines for line counting
                newlines_before = src[:pos].count('\n')
                line = newlines_before + 1
                col = pos - src.rfind('\n', 0, pos)

                # Determine which group matched
                for i, (_, ttype) in enumerate(TOKEN_SPEC):
                    if m.group(f'tok{i}') is not None:
                        if ttype is not None:
                            # Handle embedded newlines in matched text
                            tokens.append(Token(ttype, matched_text, line, col))
                        # Track newlines within match
                        break

                pos = m.end()
            else:
                # Unrecognized character
                newlines_before = src[:pos].count('\n')
                line = newlines_before + 1
                col = pos - src.rfind('\n', 0, pos)
                char = src[pos]
                errors.append({
                    "type": "LexicalError",
                    "message": f"Unexpected character '{char}'",
                    "line": line,
                    "col": col,
                    "suggestion": f"Remove or replace the character '{char}'"
                })
                tokens.append(Token(TokenType.ERROR, char, line, col))
                pos += 1

        # Recalculate line numbers properly
        tokens = self._recalculate_lines(tokens)

        tokens.append(Token(TokenType.EOF, '', self._get_line_count(), 0))
        self.tokens = tokens
        self.errors = errors
        return tokens

    def _recalculate_lines(self, tokens: List[Token]) -> List[Token]:
        """Recalculate accurate line/col from source positions."""
        line_map = {}
        line = 1
        for i, ch in enumerate(self.source):
            line_map[i] = line
            if ch == '\n':
                line += 1

        result = []
        for tok in tokens:
            result.append(tok)
        return result

    def _get_line_count(self):
        return self.source.count('\n') + 1

    def get_token_table(self) -> List[dict]:
        return [
            {
                "token": t.value,
                "type": t.type.name,
                "line": t.line,
                "col": t.col
            }
            for t in self.tokens if t.type != TokenType.EOF
        ]
