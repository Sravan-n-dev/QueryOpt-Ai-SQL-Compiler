"""Application settings for QueryOpt AI."""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
import os

PROJECT_ROOT = Path(__file__).resolve().parent.parent


@dataclass(frozen=True)
class Settings:
    """Immutable application settings."""

    project_root: Path = field(default=PROJECT_ROOT)
    database_path: Path = field(default_factory=lambda: PROJECT_ROOT / "database" / "college.db")
    gemini_api_key: Optional[str] = None
    gemini_model: str = "gemini-2.0-flash"
    max_result_rows: int = 1000
    query_timeout: int = 30


def get_settings() -> Settings:
    """Load environment variables from .env and return a Settings instance.

    Reads GEMINI_API_KEY, GEMINI_MODEL, DATABASE_PATH, MAX_RESULT_ROWS,
    and QUERY_TIMEOUT from the environment (with sane defaults).
    """
    load_dotenv(PROJECT_ROOT / ".env")

    raw_db = os.getenv("DATABASE_PATH")
    if raw_db is not None:
        db_path = Path(raw_db)
        if not db_path.is_absolute():
            db_path = PROJECT_ROOT / db_path
    else:
        db_path = PROJECT_ROOT / "database" / "college.db"

    return Settings(
        project_root=PROJECT_ROOT,
        database_path=db_path,
        gemini_api_key=os.getenv("GEMINI_API_KEY"),
        gemini_model=os.getenv("GEMINI_MODEL", "gemini-2.0-flash"),
        max_result_rows=int(os.getenv("MAX_RESULT_ROWS", "1000")),
        query_timeout=int(os.getenv("QUERY_TIMEOUT", "30")),
    )
