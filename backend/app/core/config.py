from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "AI Recruitment Copilot API"
    app_version: str = "0.1.0"
    environment: str = "development"
    debug: bool = True
    api_prefix: str = "/api/v1"
    database_url: str

    resume_storage_directory: Path = Path(
        "local_storage/resumes"
    )
    resume_max_file_size_bytes: int = 5 * 1024 * 1024
    resume_allowed_extensions: str = ".pdf,.docx"
    resume_allowed_content_types: str = (
        "application/pdf,"
        "application/vnd.openxmlformats-officedocument."
        "wordprocessingml.document"
    )

    cors_origins: str = (
        "http://localhost:5173,"
        "http://127.0.0.1:5173"
    )

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @property
    def cors_origin_list(self) -> list[str]:
        return [
            origin.strip()
            for origin in self.cors_origins.split(",")
            if origin.strip()
        ]

    @property
    def resume_allowed_extension_set(self) -> set[str]:
        return {
            extension.strip().lower()
            for extension in self.resume_allowed_extensions.split(",")
            if extension.strip()
        }

    @property
    def resume_allowed_content_type_set(self) -> set[str]:
        return {
            content_type.strip().lower()
            for content_type in self.resume_allowed_content_types.split(",")
            if content_type.strip()
        }


@lru_cache
def get_settings() -> Settings:
    return Settings()