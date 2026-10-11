from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from dotenv import load_dotenv


PROJECT_ROOT = Path(__file__).resolve().parent.parent


@dataclass(frozen=True)
class Settings:
    database_path: Path
    cors_origins: tuple[str, ...]
    database_url: str | None = None


def get_settings() -> Settings:
    load_dotenv(PROJECT_ROOT / ".env", override=False)
    raw_db = os.environ.get("TRAVELMATE_API_DB", "").strip()
    database_path = Path(raw_db).expanduser() if raw_db else PROJECT_ROOT / "travelmate_api.db"
    raw_origins = os.environ.get("TRAVELMATE_CORS_ORIGINS", "http://localhost:8081,http://localhost:19006")
    origins = tuple(item.strip() for item in raw_origins.split(",") if item.strip())
    database_url = os.environ.get("DATABASE_URL", "").strip() or None
    return Settings(database_path=database_path, cors_origins=origins, database_url=database_url)

