"""
Tests for Natural Language to SQL and Azure OpenAI integration.
"""

from config.database_config import get_connection
from ai.nl2sql import NL2SQLTranslator
from pipeline import QueryPipeline


def test_nl_ece_query():
    conn = get_connection()
    translator = NL2SQLTranslator(conn)
    res = translator.translate("List out all the students above age 23 whose branch is ECE.")
    assert res.success is True
    assert "Student" in res.sql
    assert "branch = 'ECE'" in res.sql
    assert "age > 23" in res.sql


def test_nl_cse_query():
    conn = get_connection()
    translator = NL2SQLTranslator(conn)
    res = translator.translate("Show the names and CGPA of all CSE students.")
    assert res.success is True
    assert "Student" in res.sql
    assert "branch = 'CSE'" in res.sql


def test_nl_marks_query():
    conn = get_connection()
    translator = NL2SQLTranslator(conn)
    res = translator.translate("Find students who scored more than 80 marks in their courses.")
    assert res.success is True
    assert "Enrollment" in res.sql
    assert "marks > 80" in res.sql


def test_nl_nonexistent_attribute():
    conn = get_connection()
    translator = NL2SQLTranslator(conn)
    res = translator.translate("Show students with attendance above 75 percent.")
    assert res.success is False
    assert "attendance" in res.error.lower()


def test_pipeline_nl_execution():
    pipeline = QueryPipeline()
    res = pipeline.process_natural_language("List out all the students above age 23 whose branch is ECE.")
    assert res.success is True
    assert res.execution_result is not None
    assert res.execution_result.row_count > 0
    assert len(res.execution_result.rows) > 0
