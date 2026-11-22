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
        elif path == "/api/config/azure-openai":
            self._handle_get_azure_openai_config()
        elif path == "/api/config/gemini":
            # Backward-compatible route for an old prebuilt frontend bundle.
            self._handle_get_azure_openai_config(legacy=True)
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
        elif path == "/api/config/azure-openai":
            self._handle_set_azure_openai_config()
        elif path == "/api/config/gemini":
            # Backward-compatible route for an old prebuilt frontend bundle.
            self._handle_set_legacy_ai_config()
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
                "ai_model": pipeline.nl_translator.client.deployment_name,
            })
        except Exception as e:
            self._send_json({"error": str(e)}, status=500)

    def _handle_get_azure_openai_config(self, legacy=False):
        client = pipeline.nl_translator.client
        key = client.api_key
        masked_key = f"{key[:6]}...{key[-4:]}" if len(key) > 10 else ("***" if key else "")
        payload = {
            "is_configured": pipeline.nl_translator.is_available(),
            "endpoint": client.endpoint,
            "deployment": client.deployment_name,
            "masked_key": masked_key,
        }
        if legacy:
            payload["model"] = client.deployment_name
        self._send_json(payload)

    def _write_azure_openai_env(self, values):
        """Update Azure settings in .env without changing unrelated settings."""
        env_path = PROJECT_ROOT / ".env"
        existing = []
        if env_path.exists():
            with open(env_path, "r", encoding="utf-8") as f:
                existing = f.readlines()

        # Remove the retired Gemini settings and replace Azure settings atomically.
        managed = {
            "AZURE_OPENAI_ENDPOINT",
            "AZURE_OPENAI_API_KEY",
            "AZURE_OPENAI_DEPLOYMENT",
            "GEMINI_API_KEY",
            "GEMINI_MODEL",
        }
        new_lines = []
        written = set()
        for line in existing:
            stripped = line.strip()
            key_name = stripped.split("=", 1)[0].strip() if "=" in stripped else ""
            if key_name not in managed:
                new_lines.append(line)
                continue
            if key_name in values and key_name not in written:
                import json as _json
                new_lines.append(f"{key_name}={_json.dumps(str(values[key_name]))}\n")
                written.add(key_name)

        import json as _json
        for key_name, value in values.items():
            if key_name not in written:
                new_lines.append(f"{key_name}={_json.dumps(str(value))}\n")

        temp_path = env_path.with_suffix(".env.tmp")
        with open(temp_path, "w", encoding="utf-8") as f:
            f.writelines(new_lines)
        temp_path.replace(env_path)

    def _handle_set_legacy_ai_config(self):
        """Support old UI bundles that only send an API key and model field.

        The Azure endpoint and deployment must already be present in .env.
        New frontend source uses /api/config/azure-openai instead.
        """
        try:
            content_len = int(self.headers.get("Content-Length", 0))
            data = json.loads(self.rfile.read(content_len).decode("utf-8") or "{}")
            client = pipeline.nl_translator.client
            api_key = (data.get("api_key") or "").strip()

            if not api_key:
                client.clear()
                self._write_azure_openai_env({})
                self._send_json({
                    "success": True,
                    "message": "Azure OpenAI credentials cleared. The built-in schema fallback is active.",
                    "is_live": False,
                })
                return

            if not client.endpoint:
                self._send_json({
                    "success": False,
                    "message": "Set AZURE_OPENAI_ENDPOINT and AZURE_OPENAI_DEPLOYMENT in .env first, then use this older dialog to enter the key.",
                    "is_live": False,
                }, status=400)
                return

            success, msg = client.configure(
                endpoint=client.endpoint,
                api_key=api_key,
                deployment=client.deployment_name,
                test_connection=bool(data.get("test", True)),
            )
            if success:
                self._write_azure_openai_env({
                    "AZURE_OPENAI_ENDPOINT": client.endpoint,
                    "AZURE_OPENAI_API_KEY": client.api_key,
                    "AZURE_OPENAI_DEPLOYMENT": client.deployment_name,
                })
            self._send_json({
                "success": success,
                "message": msg,
                "is_live": pipeline.nl_translator.is_available() if success else False,
                "model": client.deployment_name,
            }, status=200 if success else 400)
        except Exception as exc:
            self._send_json({"success": False, "message": str(exc)}, status=500)

    def _handle_set_azure_openai_config(self):
        try:
            content_len = int(self.headers.get("Content-Length", 0))
            raw_body = self.rfile.read(content_len).decode("utf-8")
            data = json.loads(raw_body or "{}")
            client = pipeline.nl_translator.client

            if data.get("clear"):
                client.clear()
                self._write_azure_openai_env({})
                self._send_json({
                    "success": True,
                    "message": "Azure OpenAI credentials cleared. The built-in schema fallback is active.",
                    "is_live": False,
                })
                return

            endpoint = str(data.get("endpoint") or client.endpoint).strip()
            api_key = data.get("api_key", "").strip()
            deployment = str(data.get("deployment") or client.deployment_name).strip()
            test_conn = bool(data.get("test", True))

            success, msg = client.configure(
                endpoint=endpoint,
                api_key=api_key,
                deployment=deployment,
                test_connection=test_conn,
            )

            if success:
                self._write_azure_openai_env({
                    "AZURE_OPENAI_ENDPOINT": client.endpoint,
                    "AZURE_OPENAI_API_KEY": client.api_key,
                    "AZURE_OPENAI_DEPLOYMENT": client.deployment_name,
                })
                self._send_json({
                    "success": True,
                    "message": msg,
                    "is_live": pipeline.nl_translator.is_available(),
                    "deployment": client.deployment_name,
                    "endpoint": client.endpoint,
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
