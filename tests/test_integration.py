"""
End-to-end integration tests for QueryOpt AI.
"""

from pipeline import QueryPipeline


def test_full_pipeline_student_query(db_connection):
    pipeline = QueryPipeline(conn=db_connection)
    res = pipeline.process_sql("SELECT name, age FROM Student WHERE age > 23 ORDER BY student_id LIMIT 10")

    assert res.success is True
    assert res.execution_result is not None
    assert res.execution_result.row_count == 10
    assert res.results_match is True


def test_full_pipeline_join_query(db_connection):
    pipeline = QueryPipeline(conn=db_connection)
    query = (
        "SELECT s.name, d.dept_name "
        "FROM Student s "
        "INNER JOIN Department d ON s.dept_id = d.dept_id "
        "WHERE s.age > 24 "
        "ORDER BY s.student_id "
        "LIMIT 10"
    )
    res = pipeline.process_sql(query)

    assert res.success is True
    assert res.execution_result is not None
    assert res.execution_result.row_count == 10
    assert res.results_match is True


def test_pipeline_catches_invalid_syntax(db_connection):
    pipeline = QueryPipeline(conn=db_connection)
    res = pipeline.process_sql("SELECT FROM Student")

    assert res.success is False
    assert res.error_stage == "Syntax Analysis"


def test_pipeline_catches_semantic_error(db_connection):
    pipeline = QueryPipeline(conn=db_connection)
    res = pipeline.process_sql("SELECT invalid_column FROM Student")

    assert res.success is False
    assert res.error_stage == "Semantic Analysis"
