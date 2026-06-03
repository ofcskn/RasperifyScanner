"""GeminiProvider — concrete AIProvider using Google Gemini Vision."""
import base64
import json
import re

from google import genai
from google.genai import types

from app.config.settings import settings
from app.services.ai.base import AIProvider, AnalysisResult, DetectedObject, EnvironmentScan
from app.services.ai.prompts import ENVIRONMENT_SCAN_PROMPT

_MODEL = "gemini-1.5-flash"


class GeminiProvider(AIProvider):
    def __init__(self) -> None:
        self._client = genai.Client(api_key=settings.gemini_api_key)

    @property
    def name(self) -> str:
        return "gemini"

    async def analyze(self, frame_base64: str, prompt: str | None = None) -> AnalysisResult:
        image_part = types.Part.from_bytes(
            data=base64.b64decode(frame_base64),
            mime_type="image/jpeg",
        )
        response = await self._client.aio.models.generate_content(
            model=_MODEL,
            contents=[prompt or ENVIRONMENT_SCAN_PROMPT, image_part],
        )
        return self._parse(response.text)

    def _parse(self, raw: str) -> AnalysisResult:
        environment_scan = None
        try:
            clean = re.sub(r"```(?:json)?", "", raw).strip().rstrip("`")
            data = json.loads(clean)
            detections = [
                DetectedObject(
                    object_name=d.get("object_name", "unknown"),
                    confidence=float(d.get("confidence", 0.0)),
                    bbox=d.get("bbox"),
                )
                for d in data.get("detections", [])
            ]
            metrics = {k: float(v) for k, v in data.get("metrics", {}).items()}
            if "people_count" in data:
                environment_scan = EnvironmentScan(
                    people_count=int(data.get("people_count", 0)),
                    environment_type=str(data.get("environment_type", "unknown")),
                    crowd_density=str(data.get("crowd_density", "unknown")),
                    ambient_conditions=data.get("ambient_conditions", {}),
                    notable_observations=list(data.get("notable_observations", [])),
                )
        except Exception:
            detections, metrics = [], {}
        return AnalysisResult(
            provider=self.name,
            raw_response=raw,
            detections=detections,
            metrics=metrics,
            environment_scan=environment_scan,
        )
