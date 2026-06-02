"""GeminiProvider — concrete AIProvider using Google Gemini Vision."""
import base64
import json
import re

from google import genai
from google.genai import types

from app.config.settings import settings
from app.services.ai.base import AIProvider, AnalysisResult, DetectedObject

_DEFAULT_PROMPT = (
    "Analyze this image. Return JSON with keys: "
    "'detections' (array of {object_name, confidence 0-1, bbox {x,y,w,h} or null}) and "
    "'metrics' (object of string->float, e.g. brightness, sharpness). "
    "Return ONLY valid JSON."
)

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
            contents=[prompt or _DEFAULT_PROMPT, image_part],
        )
        return self._parse(response.text)

    def _parse(self, raw: str) -> AnalysisResult:
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
        except Exception:
            detections, metrics = [], {}
        return AnalysisResult(provider=self.name, raw_response=raw, detections=detections, metrics=metrics)
