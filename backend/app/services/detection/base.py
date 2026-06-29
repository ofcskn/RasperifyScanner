"""Detector — abstract base (Polymorphism + Protected Variations, GRASP).

A Detector takes a base64 JPEG frame and returns normalized detections. Keeping
the boundary at base64 (the same currency CameraService and the WebSocket use)
means backends can be swapped (ONNX YOLO, OpenCV DNN, a future NPU/Coral path)
without touching callers.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class Detection:
    """A single detected object.

    bbox is normalized to the source frame as [x1, y1, x2, y2] in the range 0..1,
    so the frontend can scale it to whatever size the image is rendered at.
    track_id is assigned by the tracker (None before tracking).
    """

    label: str
    confidence: float
    bbox: list[float]  # [x1, y1, x2, y2] normalized 0..1
    track_id: int | None = None

    def to_dict(self) -> dict:
        return {
            "label": self.label,
            "confidence": round(self.confidence, 4),
            "bbox": [round(v, 5) for v in self.bbox],
            "track_id": self.track_id,
        }


class Detector(ABC):
    """Information Expert for a single detection backend."""

    @property
    @abstractmethod
    def name(self) -> str: ...

    @property
    @abstractmethod
    def available(self) -> bool:
        """True when the backend is loaded and able to run inference."""

    @abstractmethod
    def detect(self, frame_base64: str) -> list[Detection]:
        """Run detection on a base64 JPEG frame and return normalized detections."""
