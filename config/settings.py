"""Application settings for QueryOpt AI."""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional
import os

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent.parent


@dataclass(frozen=True)
class Settings:
    """Immutable application settings."""

    project_root: Path = field(default=PROJECT_ROOT)
    database_path: Path = field(default_factory=lambda: PROJECT_ROOT / "database" / "college.db")
    azure_openai_api_key: Optional[str] = None
    azure_openai_endpoint: Optional[str] = None
    azure_openai_deployment: str = "gpt-5-mini"
    max_result_rows: int = 1000
    query_timeout: int = 30


def get_settings() -> Settings:
    """Load environment variables from the project .env file."""
    load_dotenv(PROJECT_ROOT / ".env", override=False)

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
        azure_openai_api_key=os.getenv("AZURE_OPENAI_API_KEY"),
        azure_openai_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
        azure_openai_deployment=os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-5-mini"),
        max_result_rows=int(os.getenv("MAX_RESULT_ROWS", "1000")),
        query_timeout=int(os.getenv("QUERY_TIMEOUT", "30")),
    )
