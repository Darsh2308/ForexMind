"""Environment-based configuration. No secrets are hardcoded or committed."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(_PROJECT_ROOT / ".env")


@dataclass(frozen=True)
class Config:
    twelve_data_api_key: str | None
    twelve_data_daily_request_limit: int
    db_path: Path
    log_level: str
    env: str

    @property
    def has_twelve_data_key(self) -> bool:
        return bool(self.twelve_data_api_key)


def load_config() -> Config:
    db_path = Path(os.environ.get("DB_PATH", "./var/forexmind.db"))
    if not db_path.is_absolute():
        db_path = _PROJECT_ROOT / db_path
    return Config(
        twelve_data_api_key=os.environ.get("TWELVE_DATA_API_KEY") or None,
        twelve_data_daily_request_limit=int(
            os.environ.get("TWELVE_DATA_DAILY_REQUEST_LIMIT", "800")
        ),
        db_path=db_path,
        log_level=os.environ.get("LOG_LEVEL", "INFO").upper(),
        env=os.environ.get("ENV", "development"),
    )
