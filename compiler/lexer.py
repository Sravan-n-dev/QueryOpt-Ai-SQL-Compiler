"""
QueryOpt AI — SQL Lexer
=======================
Tokenises raw SQL strings using the Lark grammar terminals, producing a
structured, inspectable stream of Token objects.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

from lark import Lark
from lark.exceptions import UnexpectedCharacters, LarkError

from compiler.diagnostics import LexerError

GRAMMAR_PATH = Path(__file__).parent / "grammar.lark"


@dataclass
class Token:
    """Represents a single token identified in the SQL input."""

    type: str
    value: str
    line: int
    column: int
    pos_start: int
    pos_end: int

    def to_dict(self) -> dict:
        return {
            "type": self.type,
            "value": self.value,
            "line": self.line,
            "column": self.column,
            "pos_start": self.pos_start,
            "pos_end": self.pos_end,
        }

    def __repr__(self) -> str:
        return f"Token({self.type}, {self.value!r}, line={self.line}, col={self.column})"


class SQLLexer:
    """SQL Lexer powered by Lark grammar definitions."""

    def __init__(self, grammar_path: Optional[Path] = None):
        path = grammar_path or GRAMMAR_PATH
        with open(path, "r", encoding="utf-8") as f:
            grammar_text = f.read()

        # Initialize Lark with lexer-only / parser="earley"
        self._lark = Lark(
            grammar_text,
            start="start",
            parser="earley",
            lexer="basic",
            propagate_positions=True,
        )

    def tokenize(self, sql: str) -> List[Token]:
        """Tokenise an SQL query string into a list of Token objects.

        Raises:
            LexerError: if invalid or unexpected characters are encountered.
        """
        if not sql or not sql.strip():
            return []

        clean_sql = sql.strip()
        tokens: List[Token] = []

        try:
            lark_tokens = self._lark.lex(clean_sql)
            for tok in lark_tokens:
                start_pos = getattr(tok, "start_pos", 0) or 0
                end_pos = getattr(tok, "end_pos", start_pos + len(str(tok.value))) or (start_pos + len(str(tok.value)))
                tokens.append(
                    Token(
                        type=tok.type,
                        value=str(tok.value),
                        line=getattr(tok, "line", 1) or 1,
                        column=getattr(tok, "column", 1) or 1,
                        pos_start=start_pos,
                        pos_end=end_pos,
                    )
                )
            return tokens
        except UnexpectedCharacters as exc:
            line = getattr(exc, "line", 1)
            column = getattr(exc, "column", 1)
            char = exc.char if hasattr(exc, "char") else clean_sql[exc.pos_in_stream] if exc.pos_in_stream < len(clean_sql) else "EOF"
            hint = f"Unexpected character '{char}'. Ensure identifier names follow SQL rules and quotes are closed."
            raise LexerError(
                stage="lexer",
                message=f"Lexical error at line {line}, column {column}: unexpected character '{char}'",
                position=(line, column),
                hint=hint,
            ) from exc
        except LarkError as exc:
            raise LexerError(
                stage="lexer",
                message=f"Lexical scanning failed: {str(exc)}",
                position=(1, 1),
                hint="Verify SQL input characters.",
            ) from exc


# Module-level convenience function
_default_lexer: Optional[SQLLexer] = None


def tokenize(sql: str) -> List[Token]:
    global _default_lexer
    if _default_lexer is None:
        _default_lexer = SQLLexer()
    return _default_lexer.tokenize(sql)
