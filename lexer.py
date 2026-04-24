"""
Lexer (Tokenizer) for a subset of C.
Supports: int/char/void types, if/else/while/return/for keywords,
arithmetic/comparison/logical operators, literals, identifiers.
"""
import re
from dataclasses import dataclass
from enum import Enum, auto


class TT(Enum): 
    # Literals
    INT_LIT    = auto()
    CHAR_LIT   = auto()
    STRING_LIT = auto()
    # Identifiers & keywords
    IDENT      = auto()
    INT        = auto()
    CHAR       = auto()
    VOID       = auto()
    IF         = auto()
    ELSE       = auto()
    WHILE      = auto()
    FOR        = auto()
    RETURN     = auto()
    # Operators
    PLUS       = auto()
    MINUS      = auto()
    STAR       = auto()
    SLASH      = auto()
    PERCENT    = auto()
    AMP        = auto()
    EQ         = auto()
    NEQ        = auto()
    LT         = auto()
    GT         = auto()
    LEQ        = auto()
    GEQ        = auto()
    ASSIGN     = auto()
    AND        = auto()
    OR         = auto()
    NOT        = auto()
    PLUSEQ     = auto()
    MINUSEQ    = auto()
    PLUSPLUS   = auto()
    MINUSMINUS = auto()
    # Delimiters
    LPAREN     = auto()
    RPAREN     = auto()
    LBRACE     = auto()
    RBRACE     = auto()
    LBRACKET   = auto()
    RBRACKET   = auto()
    SEMICOLON  = auto()
    COMMA      = auto()
    # Special
    EOF        = auto()


KEYWORDS = {
    'int': TT.INT, 'char': TT.CHAR, 'void': TT.VOID,
    'if': TT.IF, 'else': TT.ELSE, 'while': TT.WHILE,
    'for': TT.FOR, 'return': TT.RETURN,
}


@dataclass
class Token:
    type: TT
    value: object
    line: int
    col: int

    def __repr__(self):
        return f"Token({self.type.name}, {self.value!r}, {self.line}:{self.col})"


class LexError(Exception):
    pass


class Lexer:
    def __init__(self, source: str):
        self.src = source
        self.pos = 0
        self.line = 1
        self.col = 1
        self.tokens: list[Token] = []

    def error(self, msg):
        raise LexError(f"[Lexer] {msg} at line {self.line}, col {self.col}")

    def peek(self, offset=0) -> str:
        p = self.pos + offset
        return self.src[p] if p < len(self.src) else ''

    def advance(self) -> str:
        ch = self.src[self.pos]
        self.pos += 1
        if ch == '\n':
            self.line += 1
            self.col = 1
        else:
            self.col += 1
        return ch

    def match(self, expected: str) -> bool:
        if self.peek() == expected:
            self.advance()
            return True
        return False

    def skip_whitespace_and_comments(self):
        while self.pos < len(self.src):
            ch = self.peek()
            if ch in ' \t\r\n':
                self.advance()
            elif ch == '/' and self.peek(1) == '/':
                while self.peek() and self.peek() != '\n':
                    self.advance()
            elif ch == '/' and self.peek(1) == '*':
                self.advance(); self.advance()
                while self.pos < len(self.src):
                    if self.peek() == '*' and self.peek(1) == '/':
                        self.advance(); self.advance()
                        break
                    self.advance()
            else:
                break

    def read_string(self) -> Token:
        line, col = self.line, self.col
        self.advance()  # opening "
        chars = []
        while self.peek() and self.peek() != '"':
            ch = self.advance()
            if ch == '\\':
                esc = self.advance()
                ch = {'n': '\n', 't': '\t', '\\': '\\', '"': '"', '0': '\0'}.get(esc, esc)
            chars.append(ch)
        if not self.peek():
            self.error("Unterminated string literal")
        self.advance()  # closing "
        return Token(TT.STRING_LIT, ''.join(chars), line, col)

    def read_char(self) -> Token:
        line, col = self.line, self.col
        self.advance()  # opening '
        ch = self.advance()
        if ch == '\\':
            esc = self.advance()
            ch = {'n': '\n', 't': '\t', '\\': '\\', "'": "'", '0': '\0'}.get(esc, esc)
        if self.peek() != "'":
            self.error("Unterminated char literal")
        self.advance()
        return Token(TT.CHAR_LIT, ord(ch), line, col)

    def read_number(self) -> Token:
        line, col = self.line, self.col
        start = self.pos
        while self.peek().isdigit():
            self.advance()
        return Token(TT.INT_LIT, int(self.src[start:self.pos]), line, col)

    def read_ident(self) -> Token:
        line, col = self.line, self.col
        start = self.pos
        while self.peek().isalnum() or self.peek() == '_':
            self.advance()
        word = self.src[start:self.pos]
        tt = KEYWORDS.get(word, TT.IDENT)
        return Token(tt, word, line, col)

    def tokenize(self) -> list[Token]:
        SIMPLE = {
            '(': TT.LPAREN, ')': TT.RPAREN,
            '{': TT.LBRACE, '}': TT.RBRACE,
            '[': TT.LBRACKET, ']': TT.RBRACKET,
            ';': TT.SEMICOLON, ',': TT.COMMA,
            '%': TT.PERCENT,
        }
        while True:
            self.skip_whitespace_and_comments()
            if self.pos >= len(self.src):
                break
            line, col = self.line, self.col
            ch = self.peek()

            if ch == '"':
                self.tokens.append(self.read_string())
            elif ch == "'":
                self.tokens.append(self.read_char())
            elif ch.isdigit():
                self.tokens.append(self.read_number())
            elif ch.isalpha() or ch == '_':
                self.tokens.append(self.read_ident())
            elif ch in SIMPLE:
                self.advance()
                self.tokens.append(Token(SIMPLE[ch], ch, line, col))
            elif ch == '+':
                self.advance()
                if self.match('+'):
                    self.tokens.append(Token(TT.PLUSPLUS, '++', line, col))
                elif self.match('='):
                    self.tokens.append(Token(TT.PLUSEQ, '+=', line, col))
                else:
                    self.tokens.append(Token(TT.PLUS, '+', line, col))
            elif ch == '-':
                self.advance()
                if self.match('-'):
                    self.tokens.append(Token(TT.MINUSMINUS, '--', line, col))
                elif self.match('='):
                    self.tokens.append(Token(TT.MINUSEQ, '-=', line, col))
                else:
                    self.tokens.append(Token(TT.MINUS, '-', line, col))
            elif ch == '*':
                self.advance()
                self.tokens.append(Token(TT.STAR, '*', line, col))
            elif ch == '/':
                self.advance()
                self.tokens.append(Token(TT.SLASH, '/', line, col))
            elif ch == '=':
                self.advance()
                if self.match('='):
                    self.tokens.append(Token(TT.EQ, '==', line, col))
                else:
                    self.tokens.append(Token(TT.ASSIGN, '=', line, col))
            elif ch == '!':
                self.advance()
                if self.match('='):
                    self.tokens.append(Token(TT.NEQ, '!=', line, col))
                else:
                    self.tokens.append(Token(TT.NOT, '!', line, col))
            elif ch == '<':
                self.advance()
                if self.match('='):
                    self.tokens.append(Token(TT.LEQ, '<=', line, col))
                else:
                    self.tokens.append(Token(TT.LT, '<', line, col))
            elif ch == '>':
                self.advance()
                if self.match('='):
                    self.tokens.append(Token(TT.GEQ, '>=', line, col))
                else:
                    self.tokens.append(Token(TT.GT, '>', line, col))
            elif ch == '&':
                self.advance()
                if self.match('&'):
                    self.tokens.append(Token(TT.AND, '&&', line, col))
                else:
                    self.tokens.append(Token(TT.AMP, '&', line, col))
            elif ch == '|':
                self.advance()
                if self.match('|'):
                    self.tokens.append(Token(TT.OR, '||', line, col))
                else:
                    self.error(f"Unknown character '|'")
            else:
                self.error(f"Unknown character '{ch}'")

        self.tokens.append(Token(TT.EOF, None, self.line, self.col))
        return self.tokens