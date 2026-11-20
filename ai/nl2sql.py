"""
QueryOpt AI — Natural Language to SQL Translator
================================================
Converts English requests into schema-aware SQL SELECT statements.
"""

from __future__ import annotations

import json
import re
import sqlite3
from dataclasses import dataclass, field
from typing import List, Optional

from ai.llm_client import GeminiClient
from ai.prompts import build_system_prompt, build_user_prompt


@dataclass
class TranslationResult:
    """Result of natural language to SQL translation."""

    sql: str
    explanation: str
    assumptions: List[str] = field(default_factory=list)
    success: bool = True
    error: Optional[str] = None
    raw_response: str = ""

    def to_dict(self) -> dict:
        return {
            "sql": self.sql,
            "explanation": self.explanation,
            "assumptions": self.assumptions,
            "success": self.success,
            "error": self.error,
        }


class NL2SQLTranslator:
    """Translates user English questions into SQL queries using Gemini."""

    def __init__(self, conn: sqlite3.Connection, api_key: Optional[str] = None, model: Optional[str] = None):
        self.conn = conn
        self.client = GeminiClient(api_key=api_key, model=model)

    def is_available(self) -> bool:
        return self.client.is_available()

    def translate(self, natural_language_query: str) -> TranslationResult:
        """Translate natural language text to SQL."""
        if not self.is_available():
            return TranslationResult(
                sql="",
                explanation="",
                success=False,
                error="Gemini API is not configured. Please provide GEMINI_API_KEY in .env or settings.",
            )

        try:
            system_prompt = build_system_prompt(self.conn)
            user_prompt = build_user_prompt(natural_language_query)

            raw = self.client.generate(system_prompt, user_prompt)

            # Strip markdown json blocks (e.g. ```json ... ```)
            clean_text = raw.strip()
            if clean_text.startswith("```"):
                clean_text = re.sub(r"^```(?:json)?\s*", "", clean_text)
                clean_text = re.sub(r"\s*```$", "", clean_text)

            data = json.loads(clean_text)
            sql = data.get("sql", "").strip().rstrip(";")
            explanation = data.get("explanation", "")
            assumptions = data.get("assumptions", [])

            # Security check: must be a SELECT statement
            if not sql.upper().startswith("SELECT"):
                return TranslationResult(
                    sql="",
                    explanation="",
                    success=False,
                    error=f"Generated statement is not a SELECT query: {sql}",
                    raw_response=raw,
                )

            # Reject dangerous write operations
            forbidden = ["INSERT", "UPDATE", "DELETE", "DROP", "ALTER", "CREATE", "TRUNCATE"]
            if any(re.search(rf"\b{f}\b", sql, re.IGNORECASE) for f in forbidden):
                return TranslationResult(
                    sql="",
                    explanation="",
                    success=False,
                    error="Modification statements are strictly forbidden in QueryOpt AI.",
                    raw_response=raw,
                )

            return TranslationResult(
                sql=sql,
                explanation=explanation,
                assumptions=assumptions,
                success=True,
                raw_response=raw,
            )
        except json.JSONDecodeError:
            # Fallback regex extraction of SELECT ... FROM
            match = re.search(r"(SELECT\s+.*?\s+FROM\s+.*)", raw, re.IGNORECASE | re.DOTALL)
            if match:
                sql = match.group(1).split(";")[0].strip()
                return TranslationResult(
                    sql=sql,
                    explanation="Extracted SQL query from model response.",
                    success=True,
                    raw_response=raw,
                )
            return TranslationResult(
                sql="",
                explanation="",
                success=False,
                error=f"Could not parse structured JSON from LLM response:\n{raw}",
                raw_response=raw,
            )
        except Exception as exc:
            return TranslationResult(
                sql="",
                explanation="",
                success=False,
                error=f"AI Translation failed: {str(exc)}",
            )
