from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Literal


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # AI Providers
    gemini_api_key: str = ""
    openai_api_key: str = ""
    ai_primary_provider: Literal["gemini", "openai"] = "gemini"
    ai_retry_max: int = 3
    ai_retry_backoff_base: float = 2.0

    # JWT Auth
    secret_key: str = "CHANGE_THIS_IN_PRODUCTION"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 15
    refresh_token_expire_days: int = 7

    # Default admin user seeded on first run (leave blank to skip seeding)
    default_username: str = ""
    default_password: str = ""

    # Database
    database_url: str = "sqlite+aiosqlite:///./rasperify.db"

    # Camera
    camera_resolution_width: int = 1280
    camera_resolution_height: int = 720
    camera_frame_queue_size: int = 5
    camera_mock: bool = False
    camera_jpeg_quality: int = 85

    # Analysis
    analysis_worker_count: int = 2
    analysis_default_interval_seconds: int = 30

    # Network config path
    network_config_path: str = "../config/network.yml"


settings = Settings()
