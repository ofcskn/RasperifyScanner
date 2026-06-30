from pydantic_settings import (
    BaseSettings,
    PydanticBaseSettingsSource,
    SettingsConfigDict,
    YamlConfigSettingsSource,
)
from typing import Literal, Type


class Settings(BaseSettings):
    # Precedence (high -> low): env > .env > config/scanner.yml > code defaults.
    # scanner.yml holds the user-facing, version-controlled defaults; env/.env
    # override per-deployment without editing the file.
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        yaml_file=["config/scanner.yml", "../config/scanner.yml", "/config/scanner.yml"],
        yaml_file_encoding="utf-8",
    )

    # --- AI providers (Stage 2) ---
    # Ollama is the default local provider; cloud providers are only used when
    # allow_cloud is true AND their key is set (see MultiAIProviderService).
    ai_primary_provider: Literal["ollama", "gemini", "openai"] = "ollama"
    ai_retry_max: int = 3
    ai_retry_backoff_base: float = 2.0

    # Ollama (local vision LLM)
    ollama_host: str = "http://localhost:11434"
    ollama_model: str = "moondream"
    ollama_enabled: bool = True
    # On a CPU-only Pi 4 the vision encoder (image -> ~730 prompt tokens) is the
    # bottleneck and a single warm inference measures ~130s; the old 120s ceiling
    # tripped an httpx ReadTimeout *every* call. Give real headroom.
    ollama_timeout_seconds: float = 300.0
    # Keep the model resident between analyses so we pay the ~1.3GB load cost once
    # instead of on every call (a reload can also OOM under memory pressure).
    ollama_keep_alive: str = "30m"
    # Cap generation so a runaway/looping response can never blow the timeout.
    ollama_num_predict: int = 256

    # Cloud (optional, off by default for privacy)
    allow_cloud: bool = False
    gemini_api_key: str = ""
    openai_api_key: str = ""

    # --- Stage 1: on-device detection ---
    detection_enabled: bool = True
    detection_backend: Literal["onnx-yolo"] = "onnx-yolo"
    detection_model_path: str = "models/yolo.onnx"
    detection_conf_threshold: float = 0.45  # higher = fewer low-confidence misclassifications
    detection_iou_threshold: float = 0.45
    detection_input_size: int = 640
    detection_target_labels: list[str] = []  # empty = all COCO classes
    detection_frame_budget_seconds: float = 1.0  # over budget -> skip frames (degrade)
    # ONNX Runtime intra-op thread count. 0 = auto (leave 1 core free for the
    # capture thread + event loop). Capping this stops YOLO inference from
    # pinning every Pi core and freezing the live video.
    detection_num_threads: int = 0

    # --- People counting ---
    counting_min_hits: int = 3        # frames a track must persist before counting
    counting_iou_match: float = 0.3   # IoU to match a detection to an existing track
    counting_max_age: int = 15        # frames a track survives unseen before eviction
    counting_person_alert_threshold: int = 0  # >0 raises an event when live count exceeds it

    # --- JWT Auth ---
    secret_key: str = "CHANGE_THIS_IN_PRODUCTION"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 15
    refresh_token_expire_days: int = 30

    # Default admin user seeded on first run (leave blank to skip seeding)
    default_username: str = ""
    default_password: str = ""

    # --- Database ---
    database_url: str = "sqlite+aiosqlite:///./rasperify.db"

    # --- Camera ---
    camera_source: str = "picamera2"  # "picamera2" | "usb:/dev/video0" | "rtsp://host/stream"
    camera_resolution_width: int = 1280
    camera_resolution_height: int = 720
    camera_frame_queue_size: int = 5
    camera_mock: bool = False
    camera_jpeg_quality: int = 85

    # --- Analysis (Stage 2 cadence) ---
    analysis_worker_count: int = 2
    analysis_default_interval_seconds: int = 30

    # --- Privacy / storage ---
    store_frames: bool = True          # persist frame thumbnails to the DB
    storage_path: str = "./data"

    # --- Network config path ---
    network_config_path: str = "../config/network.yml"

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: Type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        # Insert the YAML source below env/.env so environment variables win.
        return (
            init_settings,
            env_settings,
            dotenv_settings,
            YamlConfigSettingsSource(settings_cls),
            file_secret_settings,
        )


settings = Settings()
