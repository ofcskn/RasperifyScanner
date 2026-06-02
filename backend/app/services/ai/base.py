"""AIProvider — Abstract base (Polymorphism + Protected Variations, GRASP)."""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass
class DetectedObject:
    object_name: str
    confidence: float
    bbox: dict | None = None


@dataclass
class AnalysisResult:
    provider: str
    raw_response: str
    detections: list[DetectedObject] = field(default_factory=list)
    metrics: dict[str, float] = field(default_factory=dict)


class AIProvider(ABC):
    """Information Expert for a single AI vision provider."""

    @property
    @abstractmethod
    def name(self) -> str: ...

    @abstractmethod
    async def analyze(self, frame_base64: str, prompt: str | None = None) -> AnalysisResult: ...
