"""OpenAIProvider — concrete AIProvider using OpenAI GPT-4o Vision."""
import json
import re

from openai import AsyncOpenAI

from app.config.settings import settings
from app.services.ai.base import AIProvider, AnalysisResult, DetectedObject, EnvironmentScan
from app.services.ai.prompts import ENVIRONMENT_SCAN_PROMPT


class OpenAIProvider(AIProvider):
    def __init__(self) -> None:
        self._client = AsyncOpenAI(api_key=settings.openai_api_key)

    @property
    def name(self) -> str:
        return "openai"

    async def analyze(self, frame_base64: str, prompt: str | None = None) -> AnalysisResult:
        response = await self._client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt or ENVIRONMENT_SCAN_PROMPT},
                        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{frame_base64}"}},
                    ],
                }
            ],
            max_tokens=1024,
        )
        raw = response.choices[0].message.content or ""
        return self._parse(raw)

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
