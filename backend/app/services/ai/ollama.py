"""OllamaProvider — concrete AIProvider using a local Ollama vision model.

Talks to the Ollama HTTP API (default http://localhost:11434) with httpx — no extra
dependency. Uses /api/chat with format="json" so even small models (moondream/llava)
return parseable JSON; a tolerant parser then coerces the result into the shared
EnvironmentScan dataclass. Nothing leaves the device.
"""
from __future__ import annotations

import json
import re

import httpx

from app.config.settings import settings
from app.services.ai.base import AIProvider, AnalysisResult, DetectedObject, EnvironmentScan
from app.services.ai.prompts import OLLAMA_ENVIRONMENT_SCAN_PROMPT


class OllamaProvider(AIProvider):
    def __init__(self) -> None:
        self._host = settings.ollama_host.rstrip("/")
        self._model = settings.ollama_model
        self._timeout = settings.ollama_timeout_seconds

    @property
    def name(self) -> str:
        return "ollama"

    @property
    def model(self) -> str:
        return self._model

    def set_model(self, model: str) -> None:
        self._model = model

    async def health(self) -> dict:
        """Report reachability and whether the configured model is pulled."""
        info = {"reachable": False, "model_present": False, "model": self._model, "host": self._host}
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get(f"{self._host}/api/tags")
                resp.raise_for_status()
                info["reachable"] = True
                names = [m.get("name", "") for m in resp.json().get("models", [])]
                base = self._model.split(":")[0]
                info["model_present"] = any(n == self._model or n.split(":")[0] == base for n in names)
        except Exception as exc:
            info["error"] = str(exc)
        return info

    async def analyze(self, frame_base64: str, prompt: str | None = None) -> AnalysisResult:
        payload = {
            "model": self._model,
            "messages": [
                {
                    "role": "user",
                    "content": prompt or OLLAMA_ENVIRONMENT_SCAN_PROMPT,
                    "images": [frame_base64],
                }
            ],
            "stream": False,
            "format": "json",
            "options": {"temperature": 0.0},
        }
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            resp = await client.post(f"{self._host}/api/chat", json=payload)
            resp.raise_for_status()
            data = resp.json()
        raw = (data.get("message") or {}).get("content", "") or ""
        if not raw.strip():
            raise ValueError("Ollama returned an empty response")
        return self._parse(raw)

    def _parse(self, raw: str) -> AnalysisResult:
        environment_scan = None
        detections: list[DetectedObject] = []
        metrics: dict[str, float] = {}
        try:
            data = _extract_json(raw)
            detections = [
                DetectedObject(
                    object_name=d.get("object_name", "unknown"),
                    confidence=float(d.get("confidence", 0.0)),
                    bbox=d.get("bbox"),
                )
                for d in data.get("detections", [])
                if isinstance(d, dict)
            ]
            metrics = {k: float(v) for k, v in data.get("metrics", {}).items() if _is_number(v)}
            if "people_count" in data:
                environment_scan = EnvironmentScan(
                    people_count=int(data.get("people_count", 0) or 0),
                    environment_type=str(data.get("environment_type", "unknown")),
                    crowd_density=str(data.get("crowd_density", "unknown")),
                    ambient_conditions=data.get("ambient_conditions", {}) or {},
                    notable_observations=[str(o) for o in (data.get("notable_observations") or [])],
                )
        except Exception:
            # Leave the structured fields empty but keep raw_response for debugging.
            pass
        return AnalysisResult(
            provider=self.name,
            raw_response=raw,
            detections=detections,
            metrics=metrics,
            environment_scan=environment_scan,
        )


def _is_number(v) -> bool:
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def _extract_json(raw: str) -> dict:
    """Tolerant JSON extraction for imperfect small-model output."""
    clean = re.sub(r"```(?:json)?", "", raw).strip().rstrip("`")
    try:
        return json.loads(clean)
    except json.JSONDecodeError:
        # Fall back to the first {...} block in the text.
        match = re.search(r"\{.*\}", clean, re.DOTALL)
        if match:
            return json.loads(match.group(0))
        raise


ollama_provider = OllamaProvider()
