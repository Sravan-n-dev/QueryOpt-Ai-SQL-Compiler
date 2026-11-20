"""
QueryOpt AI — Lightweight, Zero-Dependency Web Server & REST API
================================================================
Serves the modern developer frontend IDE and REST API using Python's
built-in ThreadingHTTPServer. Guaranteed to run on any machine without framework version conflicts.
"""

from __future__ import annotations

import json
import os
import sys
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Dict
from urllib.parse import urlparse

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Load .env if present
try:
    from dotenv import load_dotenv
    load_dotenv(PROJECT_ROOT / ".env")
except Exception:
    pass

from config.database_config import get_connection, initialize_database
from database.catalog import get_all_tables, get_table_stats
from pipeline import QueryPipeline
from relational_algebra.visualizer import ra_to_text_tree

# Ensure DB initialized
initialize_database()

STATIC_DIR = PROJECT_ROOT / "static"
pipeline = QueryPipeline()


class QueryOptHandler(SimpleHTTPRequestHandler):
    """Custom HTTP request handler serving static SPA and REST endpoints."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(PROJECT_ROOT), **kwargs)

    def end_headers(self):
        # Enable CORS for local development
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        super().end_headers()

    def do_OPTIONS(self):
        self.send_response(200)
        self.end_headers()

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path

        if path in ("", "/"):
            self._serve_file(STATIC_DIR / "index.html", "text/html; charset=utf-8")
        elif path.startswith("/assets/"):
            rel_path = path[len("/assets/"):]
            file_path = STATIC_DIR / "assets" / rel_path
            self._serve_static(file_path)
        elif path.startswith("/static/"):
            rel_path = path[len("/static/"):]
            file_path = STATIC_DIR / rel_path
            self._serve_static(file_path)
        elif path == "/api/stats":
            self._handle_stats()
        elif path == "/api/schema":
            self._handle_schema()
        elif path == "/api/config/gemini":
            self._handle_get_gemini_config()
        elif (STATIC_DIR / path.lstrip("/")).is_file():
            self._serve_static(STATIC_DIR / path.lstrip("/"))
        else:
            self.send_error(404, "Endpoint not found")

    def _serve_static(self, file_path: Path):
        content_type = "text/plain"
        if file_path.suffix == ".html":
            content_type = "text/html; charset=utf-8"
        elif file_path.suffix == ".css":
            content_type = "text/css; charset=utf-8"
        elif file_path.suffix == ".js":
            content_type = "application/javascript; charset=utf-8"
        elif file_path.suffix == ".svg":
            content_type = "image/svg+xml"
        elif file_path.suffix in (".png", ".jpg", ".jpeg", ".ico"):
            ext = "jpeg" if file_path.suffix == ".jpg" else file_path.suffix[1:]
            content_type = f"image/{ext}"
        elif file_path.suffix == ".json":
            content_type = "application/json"
        self._serve_file(file_path, content_type)

    def do_POST(self):
        parsed = urlparse(self.path)
        path = parsed.path

        if path == "/api/compile":
            self._handle_compile()
        elif path == "/api/config/gemini":
            self._handle_set_gemini_config()
        else:
            self.send_error(404, "Endpoint not found")

    def _serve_file(self, file_path: Path, content_type: str):
        if not file_path.exists():
            self.send_error(404, f"File {file_path.name} not found")
            return
        try:
            with open(file_path, "rb") as f:
                content = f.read()
            self.send_response(200)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(content)))
            self.end_headers()
            self.wfile.write(content)
        except Exception as e:
            self.send_error(500, f"Error reading file: {str(e)}")

    def _send_json(self, data: Any, status: int = 200):
        body = json.dumps(data, default=str).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _handle_stats(self):
        try:
            conn = get_connection()
            tables = get_all_tables(conn)
            total_records = 0
            total_indexes = 0
            for tbl in tables:
                stats = get_table_stats(conn, tbl)
                total_records += stats.row_count
                total_indexes += len(stats.indexes)

            self._send_json({
                "tables_count": len(tables),
                "total_records": total_records,
                "total_indexes": total_indexes,
                "ai_available": pipeline.nl_translator.is_available(),
                "ai_model": pipeline.nl_translator.client.model_name,
            })
        except Exception as e:
            self._send_json({"error": str(e)}, status=500)

    def _handle_get_gemini_config(self):
        key = pipeline.nl_translator.client.api_key
        masked_key = f"{key[:6]}...{key[-4:]}" if len(key) > 10 else ("***" if key else "")
        self._send_json({
            "is_configured": pipeline.nl_translator.is_available(),
            "model": pipeline.nl_translator.client.model_name,
            "masked_key": masked_key,
        })

    def _handle_set_gemini_config(self):
        try:
            content_len = int(self.headers.get("Content-Length", 0))
            raw_body = self.rfile.read(content_len).decode("utf-8")
            data = json.loads(raw_body)
            api_key = data.get("api_key", "").strip()
            model = data.get("model", "gemini-2.0-flash").strip()
            test_conn = bool(data.get("test", True))

            success, msg = pipeline.nl_translator.client.set_api_key(
                api_key, model=model, test_connection=test_conn
            )

            if success:
                # Persist to .env file if key provided
                env_path = PROJECT_ROOT / ".env"
                env_lines = []
                if env_path.exists():
                    with open(env_path, "r", encoding="utf-8") as f:
                        env_lines = f.readlines()

                key_written = False
                model_written = False
                new_lines = []
                for line in env_lines:
                    if line.startswith("GEMINI_API_KEY="):
                        new_lines.append(f"GEMINI_API_KEY={api_key}\n")
                        key_written = True
                    elif line.startswith("GEMINI_MODEL="):
                        new_lines.append(f"GEMINI_MODEL={model}\n")
                        model_written = True
                    else:
                        new_lines.append(line)

                if not key_written:
                    new_lines.append(f"GEMINI_API_KEY={api_key}\n")
                if not model_written:
                    new_lines.append(f"GEMINI_MODEL={model}\n")

                with open(env_path, "w", encoding="utf-8") as f:
                    f.writelines(new_lines)

                self._send_json({
                    "success": True,
                    "message": msg,
                    "is_live": pipeline.nl_translator.is_available(),
                    "model": model,
                })
            else:
                self._send_json({
                    "success": False,
                    "message": msg,
                    "is_live": False,
                }, status=400)
        except Exception as e:
            self._send_json({"success": False, "message": str(e)}, status=500)

    def _handle_schema(self):
        try:
            conn = get_connection()
            tables = get_all_tables(conn)
            schema_info = []
            for tbl in tables:
                stats = get_table_stats(conn, tbl)
                schema_info.append({
                    "table_name": stats.table_name,
                    "row_count": stats.row_count,
                    "columns": [
                        {
                            "name": col.name,
                            "type": col.data_type,
                            "num_distinct": col.num_distinct,
                            "min_val": col.min_val,
                            "max_val": col.max_val,
                            "null_count": col.null_count,
                        }
                        for col in stats.columns
                    ],
                    "indexes": [
                        {
                            "name": idx.name,
                            "columns": idx.columns,
                            "is_unique": idx.is_unique,
                        }
                        for idx in stats.indexes
                    ],
                })
            self._send_json({"tables": schema_info})
        except Exception as e:
            self._send_json({"error": str(e)}, status=500)

    def _handle_compile(self):
        try:
            content_len = int(self.headers.get("Content-Length", 0))
            raw_body = self.rfile.read(content_len).decode("utf-8")
            try:
                payload = json.loads(raw_body)
            except Exception as json_err:
                self._send_json({"success": False, "error_stage": "Input", "error_message": f"Malformed JSON: {str(json_err)}"}, status=400)
                return

            query = payload.get("query", "").strip()
            mode = payload.get("mode", "sql")

            if not query:
                self._send_json({"success": False, "error_stage": "Input", "error_message": "Query cannot be empty."}, status=400)
                return

            if mode == "natural_language" or mode == "nl":
                res = pipeline.process_natural_language(query)
            else:
                res = pipeline.process_sql(query)

            # Format tokens
            tokens_data = [t.to_dict() for t in res.tokens] if res.tokens else []

            # Format AST
            ast_dict = res.ast.to_dict() if res.ast else None
            ast_pretty = res.ast.pretty_print() if res.ast else ""

            # Format RA trees
            ra_tree_dict = res.ra_tree.to_dict() if res.ra_tree else None
            ra_tree_text = ra_to_text_tree(res.ra_tree) if res.ra_tree else ""

            ra_tree_opt_dict = res.ra_tree_optimized.to_dict() if res.ra_tree_optimized else None
            ra_tree_opt_text = ra_to_text_tree(res.ra_tree_optimized) if res.ra_tree_optimized else ""

            # Applied rules
            applied_rules_data = [r.to_dict() for r in res.applied_rules] if res.applied_rules else []

            # Physical plan
            physical_plan_dict = res.physical_plan.to_dict() if res.physical_plan else None
            physical_plan_pretty = res.physical_plan.pretty_print() if res.physical_plan else ""

            # Optimization report
            opt_report_data = res.optimization_report.to_dict() if res.optimization_report else None

            # Execution result
            exec_res_data = None
            if res.execution_result:
                clean_rows = []
                for r in res.execution_result.rows:
                    clean_r = {k.split(".")[-1]: v for k, v in r.items() if "." not in k or len(r) == 1}
                    if not clean_r:
                        clean_r = {k.split(".")[-1]: v for k, v in r.items()}
                    clean_rows.append(clean_r)

                exec_res_data = {
                    "rows": clean_rows,
                    "row_count": res.execution_result.row_count,
                    "execution_time_ms": res.execution_result.execution_time_ms,
                    "rows_scanned": res.execution_result.rows_scanned,
                    "column_names": list(clean_rows[0].keys()) if clean_rows else [],
                    "success": res.execution_result.success,
                    "error": res.execution_result.error,
                }

            # Stages telemetry
            stages_data = [
                {
                    "stage_number": s.stage_number,
                    "stage_name": s.stage_name,
                    "status": s.status,
                    "duration_ms": s.duration_ms,
                    "error": s.error,
                    "details": s.details,
                }
                for s in res.stages
            ]

            response_payload = {
                "success": res.success,
                "input_query": res.input_query,
                "input_type": res.input_type,
                "generated_sql": res.generated_sql,
                "translation_info": res.translation_info.to_dict() if res.translation_info else None,
                "error_stage": res.error_stage,
                "error_message": res.error_message,
                "total_time_ms": res.total_time_ms,
                "results_match": res.results_match,
                "tokens": tokens_data,
                "ast": ast_dict,
                "ast_pretty": ast_pretty,
                "semantic_valid": res.semantic_valid,
                "ra_tree": ra_tree_dict,
                "ra_tree_text": ra_tree_text,
                "ra_tree_optimized": ra_tree_opt_dict,
                "ra_tree_optimized_text": ra_tree_opt_text,
                "applied_rules": applied_rules_data,
                "physical_plan": physical_plan_dict,
                "physical_plan_pretty": physical_plan_pretty,
                "optimization_report": opt_report_data,
                "execution_result": exec_res_data,
                "stages": stages_data,
            }

            self._send_json(response_payload)
        except Exception as e:
            self._send_json({"success": False, "error_stage": "Server", "error_message": str(e)}, status=500)


def run_server(host: str = "0.0.0.0", port: int = 8000):
    server_address = (host, port)
    httpd = ThreadingHTTPServer(server_address, QueryOptHandler)
    print("=" * 70)
    print("  🚀 QueryOpt AI: SQL Compiler, Optimizer & Natural Language IDE")
    print(f"  Web Application available at: http://localhost:{port}")
    print("=" * 70)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down server...")
        httpd.server_close()


if __name__ == "__main__":
    run_server()
