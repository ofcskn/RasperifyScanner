"""Regression tests for API response schemas.

Guards the DetectionItem.bbox contract: the detector and DB persist a bounding
box as a list [x1, y1, x2, y2], so the schema must accept a list. A prior
`Optional[dict]` typing made GET /api/v1/results 500 on every stored detection.
"""
import json
from datetime import datetime

from app.models.schemas import DetectionItem, AnalysisResponse


def test_detection_item_accepts_list_bbox():
    # The exact value from the production 500 traceback.
    item = DetectionItem(object_name="dog", confidence=0.41, bbox=[0.66154, 0.13676, 0.99978, 0.99097])
    assert item.bbox == [0.66154, 0.13676, 0.99978, 0.99097]


def test_detection_item_bbox_optional():
    item = DetectionItem(object_name="person", confidence=0.9, bbox=None)
    assert item.bbox is None


def test_detection_item_roundtrips_from_stored_json():
    # Mirrors results.py: bbox is read back via json.loads(bbox_json).
    stored = json.dumps([0.1, 0.2, 0.3, 0.4])
    item = DetectionItem(object_name="car", confidence=0.8, bbox=json.loads(stored))
    assert item.bbox == [0.1, 0.2, 0.3, 0.4]


def test_analysis_response_embeds_list_bbox():
    resp = AnalysisResponse(
        id=1,
        frame_id="f1",
        provider="onnx-yolo",
        detections=[DetectionItem(object_name="person", confidence=0.95, bbox=[0.0, 0.0, 0.5, 0.5])],
        metrics=[],
        raw_response="",
        created_at=datetime(2026, 1, 1),
    )
    assert resp.detections[0].bbox == [0.0, 0.0, 0.5, 0.5]
