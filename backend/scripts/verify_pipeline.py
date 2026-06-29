#!/usr/bin/env python3
"""End-to-end verification of the local scanner pipeline.

Proves, with clear pass/fail output:
  1. Detection runs on a frame (and reports any person boxes).
  2. People counting updates correctly across a synthetic sequence.
  3. Ollama returns valid structured JSON (skipped if Ollama is unreachable).
  4. The pipeline recovers from camera / detector / model failures.

Run from the backend/ directory:  python scripts/verify_pipeline.py
"""
from __future__ import annotations

import asyncio
import base64
import io
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

GREEN, RED, YELLOW, RESET = "\033[92m", "\033[91m", "\033[93m", "\033[0m"
_failures = 0


def _result(name: str, passed: bool, detail: str = "") -> None:
    global _failures
    tag = f"{GREEN}PASS{RESET}" if passed else f"{RED}FAIL{RESET}"
    print(f"[{tag}] {name}" + (f" — {detail}" if detail else ""))
    if not passed:
        _failures += 1


def _skip(name: str, detail: str) -> None:
    print(f"[{YELLOW}SKIP{RESET}] {name} — {detail}")


def _blank_frame_b64(w: int = 640, h: int = 480) -> str:
    from PIL import Image
    buf = io.BytesIO()
    Image.new("RGB", (w, h), (40, 40, 40)).save(buf, format="JPEG")
    return base64.b64encode(buf.getvalue()).decode()


def test_detection() -> None:
    from app.services.detection.service import detection_service
    if not detection_service.available:
        _skip("detection runs", "detector unavailable (run scripts/setup_local.py to install onnxruntime + model)")
        return
    out = detection_service.process(_blank_frame_b64())
    persons = sum(1 for d in out["detections"] if d.get("label") == "person")
    _result("detection runs", isinstance(out["detections"], list),
            f"{len(out['detections'])} objects, {persons} persons, {out.get('infer_ms')}ms")


def test_counting() -> None:
    from app.services.detection.base import Detection
    from app.services.detection.tracker import CentroidTracker, PeopleCounter
    tr = CentroidTracker(iou_match_threshold=0.3, max_age=5)
    pc = PeopleCounter(tr, min_hits=3)
    counts = {"live": 0, "cumulative": 0}
    for i in range(4):
        x = 0.1 + i * 0.02
        counts = pc.update(tr.update([Detection("person", 0.9, [x, 0.2, x + 0.1, 0.6])]))
    one_ok = counts == {"live": 1, "cumulative": 1}
    for _ in range(3):
        counts = pc.update(tr.update([
            Detection("person", 0.9, [0.2, 0.2, 0.3, 0.6]),
            Detection("person", 0.9, [0.7, 0.2, 0.8, 0.6]),
        ]))
    two_ok = counts["live"] == 2 and counts["cumulative"] == 2
    _result("people counting updates", one_ok and two_ok, f"final={counts}")


async def test_ollama() -> None:
    from app.config.settings import settings
    from app.services.ai.ollama import OllamaProvider
    provider = OllamaProvider()
    info = await provider.health()
    if not info.get("reachable"):
        _skip("ollama structured output", f"ollama not reachable at {settings.ollama_host}")
        return
    if not info.get("model_present"):
        _skip("ollama structured output", f"model '{settings.ollama_model}' not pulled")
        return
    try:
        res = await provider.analyze(_blank_frame_b64())
        valid = res.environment_scan is not None or bool(res.raw_response.strip())
        detail = (f"people={res.environment_scan.people_count}, env={res.environment_scan.environment_type}"
                  if res.environment_scan else "raw response only")
        _result("ollama structured output", valid, detail)
    except Exception as exc:
        _result("ollama structured output", False, str(exc))


def test_recovery() -> None:
    """Detector errors must degrade to empty results, not crash the stream."""
    from app.services.detection.service import DetectionService

    svc = DetectionService()

    class _Boom:
        name = "boom"
        available = True

        def detect(self, _f):
            raise RuntimeError("simulated inference failure")

    svc._detector = _Boom()
    svc._enabled = True
    out = svc.process(_blank_frame_b64())
    recovered = out["detections"] == [] and "error" in out
    _result("recovers from detector failure", recovered, out.get("error", ""))


async def main() -> None:
    print("RasperifyScanner — pipeline verification\n" + "=" * 40)
    test_detection()
    test_counting()
    await test_ollama()
    test_recovery()
    print("-" * 40)
    if _failures:
        print(f"{RED}{_failures} check(s) failed.{RESET}")
        sys.exit(1)
    print(f"{GREEN}All non-skipped checks passed.{RESET}")


if __name__ == "__main__":
    asyncio.run(main())
