"""DetectionService — Indirection + Pure Fabrication (GRASP).

Owns the detector backend, the tracker, and the people counter, and exposes a
single `process(frame_base64)` the live broadcaster calls per frame. Hides backend
selection and implements graceful degradation: when a frame takes longer than the
budget to process, subsequent frames are skipped (the last result is reused) so a
slow Pi keeps streaming video instead of falling behind.
"""
from __future__ import annotations

import logging
import time

from app.config.settings import settings
from app.services.detection.base import Detection, Detector
from app.services.detection.tracker import CentroidTracker, PeopleCounter

logger = logging.getLogger(__name__)


def _build_detector() -> Detector:
    """Factory: select the detection backend by config (currently onnx-yolo)."""
    backend = settings.detection_backend
    if backend == "onnx-yolo":
        from app.services.detection.onnx_yolo import OnnxYoloDetector

        return OnnxYoloDetector(
            model_path=settings.detection_model_path,
            conf_threshold=settings.detection_conf_threshold,
            iou_threshold=settings.detection_iou_threshold,
            target_labels=settings.detection_target_labels or None,
            input_size=settings.detection_input_size,
            num_threads=settings.detection_num_threads,
        )
    raise ValueError(f"Unknown detection backend: {backend}")


class DetectionService:
    def __init__(self) -> None:
        self._detector = _build_detector()
        self._tracker = CentroidTracker(
            iou_match_threshold=settings.counting_iou_match,
            max_age=settings.counting_max_age,
        )
        self._counter = PeopleCounter(
            self._tracker,
            person_label="person",
            min_hits=settings.counting_min_hits,
        )
        self._enabled = settings.detection_enabled
        self._budget_s = max(0.05, settings.detection_frame_budget_seconds)
        self._skip_remaining = 0
        self._last_result: dict | None = None

    @property
    def detector_name(self) -> str:
        return self._detector.name

    @property
    def available(self) -> bool:
        return self._enabled and self._detector.available

    def set_enabled(self, enabled: bool) -> None:
        self._enabled = enabled

    def apply_thresholds(self, conf: float | None = None, iou: float | None = None) -> None:
        setter = getattr(self._detector, "set_thresholds", None)
        if callable(setter):
            setter(conf=conf, iou=iou)

    def reset_counts(self) -> None:
        self._counter.reset()

    @property
    def cumulative_count(self) -> int:
        return self._counter.cumulative

    def snapshot(self, frame_base64: str) -> dict:
        """One-shot detection for the scheduled pipeline.

        Runs the detector WITHOUT advancing the live tracker/counter, so the
        periodic Stage-2 analysis can attach real boxes + a per-frame person count
        to the stored record without corrupting the live cumulative count.
        """
        if not self.available:
            return {"detections": [], "people_live": 0, "people_cumulative": self.cumulative_count,
                    "available": False}
        try:
            detections = self._detector.detect(frame_base64)
        except Exception as exc:
            logger.error("Snapshot detection failed: %s", exc)
            return {"detections": [], "people_live": 0, "people_cumulative": self.cumulative_count,
                    "available": True, "error": str(exc)}
        live = sum(1 for d in detections if d.label == "person")
        return {
            "detections": [d.to_dict() for d in detections],
            "people_live": live,
            "people_cumulative": self.cumulative_count,
            "available": True,
        }

    def process(self, frame_base64: str) -> dict:
        """Detect, track, and count on one frame. Returns overlay-ready payload."""
        if not self.available:
            return {"detections": [], "counts": {"live": 0, "cumulative": self._counter.cumulative},
                    "detector": self._detector.name, "degraded": False, "available": False}

        # Graceful degradation: skip frames while we are behind budget.
        if self._skip_remaining > 0:
            self._skip_remaining -= 1
            if self._last_result is not None:
                return {**self._last_result, "degraded": True}

        start = time.monotonic()
        try:
            detections = self._detector.detect(frame_base64)
        except Exception as exc:  # keep the stream alive on inference failure
            logger.error("Detection failed: %s", exc)
            return {"detections": [], "counts": {"live": 0, "cumulative": self._counter.cumulative},
                    "detector": self._detector.name, "degraded": False, "available": True, "error": str(exc)}
        elapsed = time.monotonic() - start

        tracked = self._tracker.update(detections)
        counts = self._counter.update(tracked)

        if elapsed > self._budget_s:
            # Drop roughly enough frames to amortize the overrun.
            self._skip_remaining = min(5, int(elapsed / self._budget_s))
            logger.debug("Detection over budget (%.2fs > %.2fs), skipping %d frame(s)",
                         elapsed, self._budget_s, self._skip_remaining)

        result = {
            "detections": [d.to_dict() for d in tracked],
            "counts": counts,
            "detector": self._detector.name,
            "infer_ms": round(elapsed * 1000, 1),
            "degraded": False,
            "available": True,
        }
        self._last_result = result
        return result


detection_service = DetectionService()
