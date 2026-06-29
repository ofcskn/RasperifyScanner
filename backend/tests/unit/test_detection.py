"""Unit tests for Stage-1 detection: tracking/counting, graceful degradation,
and the Ollama provider's tolerant JSON parsing."""
import json

from app.services.detection.base import Detection
from app.services.detection.tracker import CentroidTracker, PeopleCounter, _iou
from app.services.detection.service import DetectionService
from app.services.ai.ollama import OllamaProvider


def _person(x: float) -> Detection:
    return Detection(label="person", confidence=0.9, bbox=[x, 0.2, x + 0.1, 0.6])


def test_iou_basic():
    assert _iou([0, 0, 1, 1], [0, 0, 1, 1]) == 1.0
    assert _iou([0, 0, 1, 1], [2, 2, 3, 3]) == 0.0


def test_tracker_keeps_stable_id_for_moving_person():
    tr = CentroidTracker(iou_match_threshold=0.3, max_age=5)
    ids = []
    for i in range(5):
        tracked = tr.update([_person(0.1 + i * 0.02)])
        ids.append(tracked[0].track_id)
    assert len(set(ids)) == 1  # same person, same id across frames


def test_counter_debounces_then_counts_unique():
    tr = CentroidTracker(iou_match_threshold=0.3, max_age=5)
    pc = PeopleCounter(tr, min_hits=3)
    counts = {"live": 0, "cumulative": 0}
    for i in range(4):
        counts = pc.update(tr.update([_person(0.1 + i * 0.02)]))
    assert counts == {"live": 1, "cumulative": 1}

    for _ in range(3):
        counts = pc.update(tr.update([
            Detection("person", 0.9, [0.2, 0.2, 0.3, 0.6]),
            Detection("person", 0.9, [0.7, 0.2, 0.8, 0.6]),
        ]))
    assert counts["live"] == 2
    assert counts["cumulative"] == 2


def test_single_frame_blip_not_counted():
    """A person seen for fewer than min_hits frames must not be counted."""
    tr = CentroidTracker(max_age=5)
    pc = PeopleCounter(tr, min_hits=3)
    counts = pc.update(tr.update([_person(0.1)]))  # one frame only
    assert counts == {"live": 1, "cumulative": 0}


def test_service_recovers_from_detector_failure():
    svc = DetectionService()

    class _Boom:
        name = "boom"
        available = True

        def detect(self, _f):
            raise RuntimeError("inference boom")

    svc._detector = _Boom()
    svc._enabled = True
    out = svc.process("ZmFrZQ==")
    assert out["detections"] == []
    assert "error" in out


def test_service_unavailable_returns_empty():
    svc = DetectionService()
    svc._enabled = False
    out = svc.process("ZmFrZQ==")
    assert out["available"] is False
    assert out["detections"] == []


def test_ollama_parse_tolerates_prose_and_fences():
    provider = OllamaProvider()
    payload = {
        "people_count": 3,
        "environment_type": "office",
        "crowd_density": "sparse",
        "ambient_conditions": {"lighting": "normal", "estimated_time": "day"},
        "notable_observations": ["a laptop"],
        "metrics": {"brightness": 0.6},
    }
    messy = "Here you go:\n```json\n" + json.dumps(payload) + "\n```\nthanks"
    res = provider._parse(messy)
    assert res.provider == "ollama"
    assert res.environment_scan is not None
    assert res.environment_scan.people_count == 3
    assert res.environment_scan.environment_type == "office"
    assert res.metrics["brightness"] == 0.6


def test_ollama_parse_handles_garbage_gracefully():
    provider = OllamaProvider()
    res = provider._parse("not json at all")
    assert res.provider == "ollama"
    assert res.environment_scan is None
    assert res.detections == []
