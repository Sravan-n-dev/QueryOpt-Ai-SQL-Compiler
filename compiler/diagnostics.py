"""
QueryOpt AI — Compiler Diagnostics
==================================
Structured error types for every compiler stage (lexer, parser, semantic
analysis) plus an ErrorCollector that accumulates multiple diagnostics.
"""

from __future__ import annotations

from typing import List, Optional, Tuple


class CompilerError(Exception):
    """Base exception for all compiler-stage errors."""

    def __init__(
        self,
        stage: str,
        message: str,
        position: Optional[Tuple[int, int]] = None,
        hint: Optional[str] = None,
    ) -> None:
        self.stage = stage
        self.message = message
        self.position = position
        self.hint = hint
        super().__init__(self._format())

    def _format(self) -> str:
        return format_error(self)


class LexerError(CompilerError):
    """Error raised during tokenisation / lexical analysis."""

    def __init__(
        self,
        message: str,
        position: Optional[Tuple[int, int]] = None,
        hint: Optional[str] = None,
        stage: str = "lexer",
    ) -> None:
        super().__init__(stage=stage, message=message, position=position, hint=hint)


class ParseError(CompilerError):
    """Error raised during parsing (grammar mismatch)."""

    def __init__(
        self,
        message: str,
        position: Optional[Tuple[int, int]] = None,
        hint: Optional[str] = None,
        stage: str = "parser",
    ) -> None:
        super().__init__(stage=stage, message=message, position=position, hint=hint)


class SemanticError(CompilerError):
    """Error raised during semantic analysis (type checks, name resolution, etc.)."""

    def __init__(
        self,
        message: str,
        position: Optional[Tuple[int, int]] = None,
        hint: Optional[str] = None,
        stage: str = "semantic",
    ) -> None:
        super().__init__(stage=stage, message=message, position=position, hint=hint)


def format_error(error: CompilerError) -> str:
    """Return a richly formatted diagnostic string for *error*."""
    parts: List[str] = [f"[{error.stage}] Error"]

    if error.position is not None:
        line, col = error.position
        parts.append(f" at line {line}, col {col}")

    parts.append(f": {error.message}")
    result = "".join(parts)

    if error.hint:
        result += f"\n  Hint: {error.hint}"

    return result


class ErrorCollector:
    """Accumulates CompilerError instances across compiler stages."""

    def __init__(self) -> None:
        self._errors: List[CompilerError] = []

    def add(self, error: CompilerError) -> None:
        self._errors.append(error)

    def add_lexer_error(
        self,
        message: str,
        position: Optional[Tuple[int, int]] = None,
        hint: Optional[str] = None,
    ) -> None:
        self.add(LexerError(message=message, position=position, hint=hint))

    def add_parse_error(
        self,
        message: str,
        position: Optional[Tuple[int, int]] = None,
        hint: Optional[str] = None,
    ) -> None:
        self.add(ParseError(message=message, position=position, hint=hint))

    def add_semantic_error(
        self,
        message: str,
        position: Optional[Tuple[int, int]] = None,
        hint: Optional[str] = None,
    ) -> None:
        self.add(SemanticError(message=message, position=position, hint=hint))

    def clear(self) -> None:
        self._errors.clear()

    @property
    def errors(self) -> List[CompilerError]:
        return list(self._errors)

    @property
    def count(self) -> int:
        return len(self._errors)

    def has_errors(self) -> bool:
        return len(self._errors) > 0

    def errors_by_stage(self, stage: str) -> List[CompilerError]:
        return [e for e in self._errors if e.stage == stage]

    def report(self, *, separator: str = "\n") -> str:
        if not self._errors:
            return ""
        lines = [format_error(e) for e in self._errors]
        summary = f"\n{separator}{len(self._errors)} error(s) total."
        return separator.join(lines) + summary

    def raise_first(self) -> None:
        if self._errors:
            raise self._errors[0]

    def raise_all(self) -> None:
        if not self._errors:
            return
        if len(self._errors) == 1:
            raise self._errors[0]
        raise CompilerError(
            stage="multiple",
            message=self.report(),
        )

    def raise_if_any(self) -> None:
        """Alias for raise_all."""
        self.raise_all()

    def __len__(self) -> int:
        return len(self._errors)

    def __bool__(self) -> bool:
        return self.has_errors()

    def __iter__(self):
        return iter(self._errors)

    def __repr__(self) -> str:
        return f"ErrorCollector(count={self.count})"
