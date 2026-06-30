from datetime import datetime
from typing import Literal, Optional
from pydantic import BaseModel, Field


# --- Auth ---

class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshRequest(BaseModel):
    refresh_token: str


# --- Frame Analysis ---

class AnalyzeRequest(BaseModel):
    frame_base64: Optional[str] = Field(None, description="Base64-encoded JPEG frame; if omitted, camera captures one")
    prompt: Optional[str] = Field(None, description="Custom analysis prompt")


class DetectionItem(BaseModel):
    object_name: str
    confidence: float
    # Normalized [x1, y1, x2, y2] in 0..1 — the same list shape produced by the
    # detector (Detection.bbox) and persisted as bbox_json. Declaring it a dict
    # caused a 500 on every stored detection (Pydantic dict_type validation error).
    bbox: Optional[list[float]] = None


class MetricItem(BaseModel):
    metric_name: str
    value: float


class EnvironmentScanSchema(BaseModel):
    people_count: int
    environment_type: str
    crowd_density: str
    ambient_conditions: dict
    notable_observations: list[str]


class AnalysisResponse(BaseModel):
    id: int
    frame_id: str
    provider: str
    detections: list[DetectionItem]
    metrics: list[MetricItem]
    raw_response: str
    environment_scan: Optional[EnvironmentScanSchema] = None
    frame_thumbnail: Optional[str] = None
    people_count_live: Optional[int] = None
    people_count_cumulative: Optional[int] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class AnalysisListResponse(BaseModel):
    items: list[AnalysisResponse]
    total: int
    page: int
    page_size: int


# --- Schedules ---

class ScheduleCreateRequest(BaseModel):
    name: str
    interval_seconds: int = Field(..., ge=5, description="Minimum 5 seconds")
    enabled: bool = True
    alert_threshold: Optional[float] = Field(None, ge=0.0, le=1.0, description="Fail-rate threshold (0–1) for alerts")


class ScheduleUpdateRequest(BaseModel):
    name: Optional[str] = None
    interval_seconds: Optional[int] = Field(None, ge=5)
    enabled: Optional[bool] = None
    alert_threshold: Optional[float] = Field(None, ge=0.0, le=1.0)


class ScheduleResponse(BaseModel):
    id: int
    name: str
    interval_seconds: int
    enabled: bool
    last_run: Optional[datetime]
    next_run: Optional[datetime]
    success_count: int
    fail_count: int
    alert_threshold: Optional[float] = None
    created_at: datetime

    model_config = {"from_attributes": True}


# --- Health ---

class AdapterStatus(BaseModel):
    name: str
    interface: str
    up: bool
    ip: Optional[str] = None


class DetectorStatus(BaseModel):
    backend: str
    available: bool
    enabled: bool


class OllamaStatus(BaseModel):
    enabled: bool
    reachable: bool
    model: str
    model_present: bool
    host: str


class HealthResponse(BaseModel):
    status: str
    camera_connected: bool
    camera_source: Optional[str] = None
    active_adapter: Optional[str]
    adapters: list[AdapterStatus]
    cpu_percent: Optional[float] = None
    memory_percent: Optional[float] = None
    uptime_seconds: Optional[float] = None
    detector: Optional[DetectorStatus] = None
    ollama: Optional[OllamaStatus] = None


# --- Runtime configuration ---

class ConfigResponse(BaseModel):
    camera_source: str
    camera_rotation: int
    detection_enabled: bool
    detection_conf_threshold: float
    detection_iou_threshold: float
    detection_interval_seconds: float
    counting_min_hits: int
    counting_person_alert_threshold: int
    ollama_enabled: bool
    ollama_model: str
    analysis_default_interval_seconds: int
    allow_cloud: bool
    store_frames: bool


class ConfigUpdateRequest(BaseModel):
    camera_rotation: Optional[Literal[0, 90, 180, 270]] = None
    detection_enabled: Optional[bool] = None
    detection_conf_threshold: Optional[float] = Field(None, ge=0.0, le=1.0)
    detection_iou_threshold: Optional[float] = Field(None, ge=0.0, le=1.0)
    detection_interval_seconds: Optional[float] = Field(None, ge=0.5, le=30.0)
    counting_min_hits: Optional[int] = Field(None, ge=1)
    counting_person_alert_threshold: Optional[int] = Field(None, ge=0)
    ollama_model: Optional[str] = None
    analysis_default_interval_seconds: Optional[int] = Field(None, ge=5)
    allow_cloud: Optional[bool] = None
    store_frames: Optional[bool] = None


# --- Events / logs ---

class EventResponse(BaseModel):
    id: int
    kind: str
    severity: str
    message: str
    data_json: Optional[dict] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class EventListResponse(BaseModel):
    items: list[EventResponse]
    total: int
    page: int
    page_size: int
