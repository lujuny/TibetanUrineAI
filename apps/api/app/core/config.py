from functools import lru_cache
from pathlib import Path
from typing import Any

from pydantic_settings import BaseSettings, SettingsConfigDict


API_ROOT = Path(__file__).resolve().parents[2]


def _resolve_path_from_api_root(value: str) -> str:
    path = Path(value)
    if path.is_absolute():
        return str(path)
    return str((API_ROOT / path).resolve())


def _resolve_sqlite_url_from_api_root(value: str) -> str:
    if value == "sqlite:///:memory:":
        return value
    if not value.startswith("sqlite:///"):
        return value

    db_path = value.removeprefix("sqlite:///")
    if Path(db_path).is_absolute():
        return value
    return f"sqlite:///{(API_ROOT / db_path).resolve()}"


class Settings(BaseSettings):
    app_env: str = "development"
    database_url: str = "sqlite:///./data/tibetan_urine_ai.db"
    upload_dir: str = "./data/uploads"
    gemma_api_base: str = ""
    gemma_api_key: str = ""
    gemma_model: str = "gemma-4"
    gemma_quality_review_enabled: bool = True
    gemma_quality_timeout_seconds: int = 30
    gemma_feature_review_enabled: bool = True
    gemma_feature_timeout_seconds: int = 45
    cors_origins: list[str] = ["http://127.0.0.1:8022", "http://localhost:8022"]

    model_config = SettingsConfigDict(
        env_file=str(API_ROOT / ".env"),
        env_file_encoding="utf-8",
    )

    def model_post_init(self, __context: Any) -> None:
        self.database_url = _resolve_sqlite_url_from_api_root(self.database_url)
        self.upload_dir = _resolve_path_from_api_root(self.upload_dir)


@lru_cache
def get_settings() -> Settings:
    return Settings()
