"""
QueryOpt AI — Central Compiler & Optimizer Pipeline
===================================================
Orchestrates the entire compilation, optimization, and execution lifecycle:
  Input -> Tokens -> AST -> Semantic Analysis -> Canonical RA Tree ->
  Optimized RA Tree -> Physical Plan (CBO) -> Volcano Execution -> Verification
"""

from __future__ import annotations

import sqlite3
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from ai.nl2sql import NL2SQLTranslator, TranslationResult
from compiler.ast_nodes import SelectStatement
from compiler.diagnostics import CompilerError
from compiler.lexer import SQLLexer, Token
from compiler.parser import SQLParser
from compiler.semantic_analyzer import SemanticAnalyzer
from config.database_config import get_connection, initialize_database
from execution.executor import ExecutionResult, QueryExecutor
from execution.physical_plan import PhysicalNode
from optimizer.cost_optimizer import CostBasedOptimizer, OptimizationReport
from optimizer.logical_optimizer import AppliedRule, LogicalOptimizer
from relational_algebra.converter import ASTToRAConverter
from relational_algebra.nodes import RANode


@dataclass
class StageResult:
    """Telemetry and diagnostics for an individual compilation stage."""

    stage_number: int
    stage_name: str
    status: str  # 'success', 'error', 'skipped'
    duration_ms: float = 0.0
    error: Optional[str] = None
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PipelineResult:
    """Complete output produced across all compilation and execution stages."""

    input_query: str
    input_type: str  # 'sql' or 'natural_language'
    generated_sql: Optional[str] = None
    translation_info: Optional[TranslationResult] = None
    tokens: List[Token] = field(default_factory=list)
    ast: Optional[SelectStatement] = None
    semantic_valid: bool = False
    ra_tree: Optional[RANode] = None
    ra_tree_optimized: Optional[RANode] = None
    applied_rules: List[AppliedRule] = field(default_factory=list)
    physical_plan: Optional[PhysicalNode] = None
    optimization_report: Optional[OptimizationReport] = None
    execution_result: Optional[ExecutionResult] = None
    reference_result: Optional[List[Dict[str, Any]]] = None
    results_match: Optional[bool] = None
    stages: List[StageResult] = field(default_factory=list)
    total_time_ms: float = 0.0
    success: bool = True
    error_stage: Optional[str] = None
    error_message: Optional[str] = None


class QueryPipeline:
    """The complete QueryOpt AI Compiler and Optimizer Pipeline."""

    def __init__(self, conn: Optional[sqlite3.Connection] = None):
        if conn is None:
            initialize_database()
            self.conn = get_connection()
        else:
            self.conn = conn

        self.lexer = SQLLexer()
        self.parser = SQLParser()
        self.semantic_analyzer = SemanticAnalyzer(self.conn)
        self.ra_converter = ASTToRAConverter()
        self.logical_optimizer = LogicalOptimizer()
        self.cost_optimizer = CostBasedOptimizer(self.conn)
        self.executor = QueryExecutor(self.conn)
        self.nl_translator = NL2SQLTranslator(self.conn)

    def process_natural_language(self, nl_query: str) -> PipelineResult:
        """Translate English question to SQL and execute through the compiler."""
        t0 = time.perf_counter()
        stage_nl = StageResult(stage_number=0, stage_name="Natural Language Translation", status="running")

        trans_res = self.nl_translator.translate(nl_query)
        stage_nl.duration_ms = round((time.perf_counter() - t0) * 1000.0, 3)

        if not trans_res.success:
            stage_nl.status = "error"
            stage_nl.error = trans_res.error
            return PipelineResult(
                input_query=nl_query,
                input_type="natural_language",
                translation_info=trans_res,
                stages=[stage_nl],
                total_time_ms=stage_nl.duration_ms,
                success=False,
                error_stage="Natural Language Translation",
                error_message=trans_res.error,
            )

        stage_nl.status = "success"
        stage_nl.details = {"generated_sql": trans_res.sql, "explanation": trans_res.explanation}

        # Send generated SQL through the canonical pipeline
        res = self.process_sql(trans_res.sql)
        res.input_query = nl_query
        res.input_type = "natural_language"
        res.generated_sql = trans_res.sql
        res.translation_info = trans_res
        res.stages.insert(0, stage_nl)
        res.total_time_ms += stage_nl.duration_ms
        return res

    def process_sql(self, sql: str) -> PipelineResult:
        """Compile, optimize, and execute an SQL query through all 7 stages."""
        overall_start = time.perf_counter()
        stages: List[StageResult] = []

        res = PipelineResult(
            input_query=sql,
            input_type="sql",
            generated_sql=sql,
        )

        # STAGE 1: Lexical Analysis
        s1 = StageResult(stage_number=1, stage_name="Lexical Analysis", status="running")
        t0 = time.perf_counter()
        try:
            tokens = self.lexer.tokenize(sql)
            s1.duration_ms = round((time.perf_counter() - t0) * 1000.0, 3)
            s1.status = "success"
            s1.details = {"token_count": len(tokens)}
            res.tokens = tokens
            stages.append(s1)
        except Exception as exc:
            s1.duration_ms = round((time.perf_counter() - t0) * 1000.0, 3)
            s1.status = "error"
            s1.error = str(exc)
            stages.append(s1)
            return self._fail(res, stages, "Lexical Analysis", str(exc), overall_start)

        # STAGE 2: Syntax Analysis & AST Construction
        s2 = StageResult(stage_number=2, stage_name="Syntax Analysis (Parsing)", status="running")
        t0 = time.perf_counter()
        try:
            ast = self.parser.parse(sql)
            s2.duration_ms = round((time.perf_counter() - t0) * 1000.0, 3)
            s2.status = "success"
            res.ast = ast
            stages.append(s2)
        except Exception as exc:
            s2.duration_ms = round((time.perf_counter() - t0) * 1000.0, 3)
            s2.status = "error"
            s2.error = str(exc)
            stages.append(s2)
            return self._fail(res, stages, "Syntax Analysis", str(exc), overall_start)

        # STAGE 3: Semantic Analysis
        s3 = StageResult(stage_number=3, stage_name="Semantic Analysis", status="running")
        t0 = time.perf_counter()
        try:
            validated_ast = self.semantic_analyzer.analyze(ast)
            s3.duration_ms = round((time.perf_counter() - t0) * 1000.0, 3)
            s3.status = "success"
            res.ast = validated_ast
            res.semantic_valid = True
            stages.append(s3)
        except Exception as exc:
            s3.duration_ms = round((time.perf_counter() - t0) * 1000.0, 3)
            s3.status = "error"
            s3.error = str(exc)
            stages.append(s3)
            return self._fail(res, stages, "Semantic Analysis", str(exc), overall_start)

        # STAGE 4: Relational Algebra Generation
        s4 = StageResult(stage_number=4, stage_name="Logical Plan Generation", status="running")
        t0 = time.perf_counter()
        try:
            ra_tree = self.ra_converter.convert(validated_ast)
            s4.duration_ms = round((time.perf_counter() - t0) * 1000.0, 3)
            s4.status = "success"
            res.ra_tree = ra_tree
            stages.append(s4)
        except Exception as exc:
            s4.duration_ms = round((time.perf_counter() - t0) * 1000.0, 3)
            s4.status = "error"
            s4.error = str(exc)
            stages.append(s4)
            return self._fail(res, stages, "Logical Plan Generation", str(exc), overall_start)

        # STAGE 5: Logical Optimization (Rewrite Rules)
        s5 = StageResult(stage_number=5, stage_name="Logical Optimization", status="running")
        t0 = time.perf_counter()
        try:
            opt_ra_tree, applied_rules = self.logical_optimizer.optimize(ra_tree)
            s5.duration_ms = round((time.perf_counter() - t0) * 1000.0, 3)
            s5.status = "success"
            s5.details = {"applied_rules_count": len(applied_rules)}
            res.ra_tree_optimized = opt_ra_tree
            res.applied_rules = applied_rules
            stages.append(s5)
        except Exception as exc:
            s5.duration_ms = round((time.perf_counter() - t0) * 1000.0, 3)
            s5.status = "error"
            s5.error = str(exc)
            stages.append(s5)
            return self._fail(res, stages, "Logical Optimization", str(exc), overall_start)

        # STAGE 6: Cost-Based Optimization & Physical Planning
        s6 = StageResult(stage_number=6, stage_name="Cost-Based Optimization", status="running")
        t0 = time.perf_counter()
        try:
            phys_plan, opt_report = self.cost_optimizer.optimize(opt_ra_tree)
            s6.duration_ms = round((time.perf_counter() - t0) * 1000.0, 3)
            s6.status = "success"
            s6.details = {
                "estimated_cost": opt_report.optimized_cost,
                "baseline_cost": opt_report.baseline_cost,
            }
            res.physical_plan = phys_plan
            res.optimization_report = opt_report
            stages.append(s6)
        except Exception as exc:
            s6.duration_ms = round((time.perf_counter() - t0) * 1000.0, 3)
            s6.status = "error"
            s6.error = str(exc)
            stages.append(s6)
            return self._fail(res, stages, "Cost-Based Optimization", str(exc), overall_start)

        # STAGE 7: Physical Execution Engine (Volcano iterator execution)
        s7 = StageResult(stage_number=7, stage_name="Physical Plan Execution", status="running")
        t0 = time.perf_counter()
        try:
            exec_res = self.executor.execute(phys_plan)
            s7.duration_ms = round((time.perf_counter() - t0) * 1000.0, 3)
            if exec_res.success:
                s7.status = "success"
                s7.details = {
                    "row_count": exec_res.row_count,
                    "rows_scanned": exec_res.rows_scanned,
                    "engine_time_ms": exec_res.execution_time_ms,
                }
            else:
                s7.status = "error"
                s7.error = exec_res.error
            res.execution_result = exec_res
            stages.append(s7)
        except Exception as exc:
            s7.duration_ms = round((time.perf_counter() - t0) * 1000.0, 3)
            s7.status = "error"
            s7.error = str(exc)
            stages.append(s7)
            return self._fail(res, stages, "Physical Execution", str(exc), overall_start)

        # STAGE 8 & 9: Reference Execution & Verification
        try:
            ref_rows = self.executor.execute_reference(sql)
            res.reference_result = ref_rows
            if exec_res and exec_res.success:
                res.results_match = self.executor.compare_results(exec_res.rows, ref_rows)
        except Exception:
            res.results_match = None

        res.stages = stages
        res.total_time_ms = round((time.perf_counter() - overall_start) * 1000.0, 3)
        res.success = True
        return res

    def _fail(
        self,
        res: PipelineResult,
        stages: List[StageResult],
        stage_name: str,
        error_msg: str,
        start_time: float,
    ) -> PipelineResult:
        res.stages = stages
        res.success = False
        res.error_stage = stage_name
        res.error_message = error_msg
        res.total_time_ms = round((time.perf_counter() - start_time) * 1000.0, 3)
        return res
