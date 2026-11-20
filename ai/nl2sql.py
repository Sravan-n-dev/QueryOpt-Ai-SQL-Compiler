"""
QueryOpt AI — Natural Language to SQL Translator
================================================
Converts English requests into schema-aware SQL SELECT statements using
Google Gemini API with a robust schema-grounded fallback engine.
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
    engine: str = "gemini"  # 'gemini' or 'schema_fallback'
    raw_response: str = ""

    def to_dict(self) -> dict:
        return {
            "sql": self.sql,
            "explanation": self.explanation,
            "assumptions": self.assumptions,
            "success": self.success,
            "error": self.error,
            "engine": self.engine,
        }


class NL2SQLTranslator:
    """Translates user English questions into SQL queries."""

    def __init__(self, conn: sqlite3.Connection, api_key: Optional[str] = None, model: Optional[str] = None):
        self.conn = conn
        self.client = GeminiClient(api_key=api_key, model=model)

    def is_available(self) -> bool:
        return self.client.is_available()

    def translate(self, natural_language_query: str) -> TranslationResult:
        """Translate natural language text to SQL."""
        nl_text = natural_language_query.strip()
        if not nl_text:
            return TranslationResult(
                sql="",
                explanation="",
                success=False,
                error="Please enter a natural language query.",
            )

        # 1. If Gemini API is available, try generating with live model
        if self.is_available():
            try:
                system_prompt = build_system_prompt(self.conn)
                user_prompt = build_user_prompt(nl_text)

                raw = self.client.generate(system_prompt, user_prompt)

                clean_text = raw.strip()
                if "```" in clean_text:
                    clean_text = re.sub(r"^```(?:json)?\s*", "", clean_text, flags=re.MULTILINE)
                    clean_text = re.sub(r"\s*```$", "", clean_text, flags=re.MULTILINE)

                # Extract JSON block if surrounded by text
                json_match = re.search(r"\{[\s\S]*\}", clean_text)
                if json_match:
                    clean_text = json_match.group(0)

                data = json.loads(clean_text)
                sql = data.get("sql", "").strip()
                explanation = data.get("explanation", "")
                assumptions = data.get("assumptions", [])

                if sql:
                    # Clean semicolons
                    sql = sql.rstrip(";").strip() + ";"
                    # Security checks
                    if sql.upper().startswith("SELECT"):
                        forbidden = ["INSERT", "UPDATE", "DELETE", "DROP", "ALTER", "CREATE", "TRUNCATE"]
                        if not any(re.search(rf"\b{f}\b", sql, re.IGNORECASE) for f in forbidden):
                            return TranslationResult(
                                sql=sql,
                                explanation=f"[Google Gemini Live] {explanation}",
                                assumptions=assumptions,
                                success=True,
                                engine="gemini",
                                raw_response=raw,
                            )
            except Exception as exc:
                # If Gemini API fails (quota 429, network, etc.), fallback gracefully
                return self._fallback_translate(nl_text, fallback_reason=f"Gemini API returned: {str(exc)}")

        # 2. If Gemini is not configured, use the smart schema-grounded fallback
        return self._fallback_translate(nl_text, fallback_reason="Gemini API key is not configured.")

    def _fallback_translate(self, query: str, fallback_reason: str = "") -> TranslationResult:
        """Schema-aware heuristic translation ensuring Natural Language always functions."""
        q = query.lower()

        # Check for non-existent columns / entities (attendance, fee, salary, etc.)
        invalid_entities = ["attendance", "fee", "fees", "salary", "stipend", "hostel", "transport", "bus"]
        for inv in invalid_entities:
            if inv in q:
                return TranslationResult(
                    sql="",
                    explanation="",
                    success=False,
                    error=f"Requested attribute '{inv}' does not exist in the College Database schema.",
                    assumptions=["The College database contains: Student, Department, Course, Enrollment."],
                    engine="schema_fallback",
                )

        note = f" (Engine: Schema Fallback - {fallback_reason})" if fallback_reason else " (Engine: Schema Fallback)"

        # ---------------------------------------------------------
        # Pattern 1: Department relation
        # e.g. "Show all departments", "List departments"
        # ---------------------------------------------------------
        if ("department" in q or "departments" in q) and not ("student" in q or "enroll" in q or "course" in q):
            sql = "SELECT dept_id, dept_name, hod\nFROM Department\nLIMIT 10;"
            return TranslationResult(
                sql=sql,
                explanation=f"Retrieved records from Department relation.{note}",
                assumptions=["Limited to 10 rows for display."],
                success=True,
                engine="schema_fallback",
            )

        # ---------------------------------------------------------
        # Pattern 2: Course relation
        # e.g. "List all courses", "Courses with 4 credits"
        # ---------------------------------------------------------
        if ("course" in q or "courses" in q) and not ("student" in q or "enroll" in q):
            credits_match = re.search(r"(\d+)\s*credits?", q)
            if credits_match:
                cr_val = int(credits_match.group(1))
                sql = f"SELECT course_id, course_name, credits\nFROM Course\nWHERE credits = {cr_val}\nLIMIT 10;"
                exp = f"Filtered Course relation for courses with {cr_val} credits."
            else:
                sql = "SELECT course_id, course_name, credits\nFROM Course\nLIMIT 10;"
                exp = "Retrieved records from Course relation."
            return TranslationResult(
                sql=sql,
                explanation=f"{exp}{note}",
                assumptions=["Limited to 10 rows."],
                success=True,
                engine="schema_fallback",
            )

        # ---------------------------------------------------------
        # Pattern 3: Multi-Table JOIN — Student + Enrollment + Course
        # e.g. "Find students who scored more than 80 marks in their courses"
        # ---------------------------------------------------------
        if ("scored" in q or "marks" in q or "grade" in q) and ("course" in q or "enroll" in q or "exam" in q):
            marks_threshold = 80
            match_num = re.search(r"(?:more than|greater than|above|>|over)\s*(\d+)", q)
            if match_num:
                marks_threshold = int(match_num.group(1))

            sql = (
                "SELECT s.name, c.course_name, e.marks\n"
                "FROM Student s\n"
                "INNER JOIN Enrollment e ON s.student_id = e.student_id\n"
                "INNER JOIN Course c ON e.course_id = c.course_id\n"
                f"WHERE e.marks > {marks_threshold}\n"
                "LIMIT 10;"
            )
            return TranslationResult(
                sql=sql,
                explanation=f"Joined Student, Enrollment, and Course tables filtering where marks > {marks_threshold}.{note}",
                assumptions=["Defaulted to showing top 10 matching records."],
                success=True,
                engine="schema_fallback",
            )

        # ---------------------------------------------------------
        # Pattern 4: Multi-Table JOIN — Student + Department
        # e.g. "List students and their departments", "Students in computer science department"
        # ---------------------------------------------------------
        if ("department" in q or "dept" in q) and ("student" in q or "students" in q):
            dept_name = None
            if "computer science" in q or "cs" in q:
                dept_name = "Computer Science"
            elif "electronics" in q or "ece" in q:
                dept_name = "Electronics"
            elif "mechanical" in q or "mech" in q:
                dept_name = "Mechanical"
            elif "civil" in q:
                dept_name = "Civil"
            elif "math" in q:
                dept_name = "Mathematics"

            where_clause = f"\nWHERE d.dept_name = '{dept_name}'" if dept_name else ""
            sql = (
                "SELECT s.name, s.branch, d.dept_name\n"
                "FROM Student s\n"
                "INNER JOIN Department d ON s.dept_id = d.dept_id"
                f"{where_clause}\n"
                "LIMIT 10;"
            )
            return TranslationResult(
                sql=sql,
                explanation=f"Joined Student and Department relations on foreign key dept_id.{note}",
                assumptions=["Limited to 10 rows."],
                success=True,
                engine="schema_fallback",
            )

        # ---------------------------------------------------------
        # Pattern 5: Top students by CGPA
        # e.g. "List the top 10 students based on CGPA"
        # ---------------------------------------------------------
        if ("top" in q or "highest" in q or "best" in q or "rank" in q) and "cgpa" in q:
            limit_val = 10
            match_limit = re.search(r"top\s*(\d+)", q)
            if match_limit:
                limit_val = int(match_limit.group(1))

            sql = (
                "SELECT name, cgpa, branch\n"
                "FROM Student\n"
                "ORDER BY cgpa DESC\n"
                f"LIMIT {limit_val};"
            )
            return TranslationResult(
                sql=sql,
                explanation=f"Selected Student sorted by CGPA in descending order with LIMIT {limit_val}.{note}",
                assumptions=[],
                success=True,
                engine="schema_fallback",
            )

        # ---------------------------------------------------------
        # Pattern 6: Student relation with branch, age, or cgpa filters
        # e.g. "List out all the students above age 23 whose branch is ECE."
        # ---------------------------------------------------------
        branch_code = None
        if "ece" in q or "electronics" in q:
            branch_code = "ECE"
        elif "cse" in q or "computer science" in q:
            branch_code = "CSE"
        elif "me" in q or "mechanical" in q or "mech" in q:
            branch_code = "ME"
        elif "ce" in q or "civil" in q:
            branch_code = "CE"
        elif "math" in q or "mathematics" in q:
            branch_code = "MATH"

        # Age filters
        age_cond = None
        match_age_gt = re.search(r"(?:above|greater than|older than|>)\s*(?:age\s*)?(\d+)", q)
        match_age_lt = re.search(r"(?:below|less than|younger than|<)\s*(?:age\s*)?(\d+)", q)
        match_age_eq = re.search(r"(?:age\s*(?:is|=|of)?\s*)(\d+)", q)

        if match_age_gt:
            age_cond = f"age > {match_age_gt.group(1)}"
        elif match_age_lt:
            age_cond = f"age < {match_age_lt.group(1)}"
        elif match_age_eq and "above" not in q and "below" not in q and "greater" not in q:
            age_cond = f"age = {match_age_eq.group(1)}"

        # CGPA filters
        cgpa_cond = None
        match_cgpa = re.search(r"cgpa\s*(?:greater than|above|>|>=)\s*([\d\.]+)", q)
        if match_cgpa:
            cgpa_cond = f"cgpa > {match_cgpa.group(1)}"

        # Projections
        cols = []
        if "name" in q or "names" in q:
            cols.append("name")
        if "cgpa" in q and not cgpa_cond:
            cols.append("cgpa")
        if "age" in q and not age_cond:
            cols.append("age")
        if "branch" in q and not branch_code:
            cols.append("branch")

        proj_str = ", ".join(cols) if cols else "*"

        conditions = []
        if age_cond:
            conditions.append(age_cond)
        if branch_code:
            conditions.append(f"branch = '{branch_code}'")
        if cgpa_cond:
            conditions.append(cgpa_cond)

        where_str = f"\nWHERE {' AND '.join(conditions)}" if conditions else ""
        sql = f"SELECT {proj_str}\nFROM Student{where_str}\nLIMIT 10;"

        return TranslationResult(
            sql=sql,
            explanation=f"Synthesized query on Student relation applying filters {conditions if conditions else 'none'}.{note}",
            assumptions=["Limited to 10 rows for display."],
            success=True,
            engine="schema_fallback",
        )
