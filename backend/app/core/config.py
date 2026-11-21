from functools import lru_cache
from pathlib import Path

from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "Student Skills and Internship Tracker API"
    database_url: str = "sqlite:///./skilltrack.db"
    jwt_secret_key: str = "development-only-change-this-secret-before-deploying"
    jwt_access_minutes: int = 30
    jwt_refresh_days: int = 14
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"
    max_resume_size_mb: int = 5
    upload_dir: str = "./uploads"
    ml_artifact_path: str | None = None
    ml_feature_info_path: str | None = None
    frontend_url: str = "http://localhost:5173"
    app_env: str = "development"
    smtp_host: str | None = None
    smtp_port: int = 587
    smtp_username: str | None = None
    smtp_password: str | None = None
    smtp_from_email: str | None = None
    ocr_enabled: bool = True
    ocr_language: str = "eng"
    tesseract_cmd: str | None = None
    rate_limit_redis_url: str | None = None

    @field_validator("database_url", mode="before")
    @classmethod
    def anchor_relative_sqlite_database(cls, value):
        """Keep the API and Alembic pointed at one DB regardless of launch cwd."""
        if not isinstance(value, str) or not value.startswith("sqlite:///"):
            return value
        database_path = value.removeprefix("sqlite:///")
        if database_path == ":memory:" or Path(database_path).is_absolute():
            return value
        backend_root = Path(__file__).resolve().parents[2]
        return f"sqlite:///{(backend_root / database_path).resolve().as_posix()}"

    @field_validator("upload_dir", mode="before")
    @classmethod
    def anchor_relative_upload_directory(cls, value):
        if not isinstance(value, str) or not value or Path(value).is_absolute():
            return value
        backend_root = Path(__file__).resolve().parents[2]
        return str((backend_root / value).resolve())

    @model_validator(mode="after")
    def validate_production_secrets(self):
        if self.app_env.lower() == "production" and len(self.jwt_secret_key) < 32:
            raise ValueError("JWT_SECRET_KEY must be at least 32 characters in production")
        if self.app_env.lower() == "production" and not self.rate_limit_redis_url:
            raise ValueError("RATE_LIMIT_REDIS_URL is required in production for shared rate limiting")
        return self

    @property
    def allowed_origins(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
