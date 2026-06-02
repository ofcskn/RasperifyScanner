from datetime import datetime
from typing import Optional
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
    frame_base64: str = Field(..., description="Base64-encoded JPEG frame")
    prompt: Optional[str] = Field(None, description="Custom analysis prompt")


class DetectionItem(BaseModel):
    object_name: str
    confidence: float
    bbox: Optional[dict] = None


class MetricItem(BaseModel):
    metric_name: str
    value: float


class AnalysisResponse(BaseModel):
    id: int
    frame_id: str
    provider: str
    detections: list[DetectionItem]
    metrics: list[MetricItem]
    raw_response: str
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


class HealthResponse(BaseModel):
    status: str
    camera_connected: bool
    active_adapter: Optional[str]
    adapters: list[AdapterStatus]
    cpu_percent: Optional[float] = None
    memory_percent: Optional[float] = None
    uptime_seconds: Optional[float] = None
