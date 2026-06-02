import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from app.services.ai.base import AnalysisResult, DetectedObject
from app.services.ai.gemini import GeminiProvider
from app.services.ai.openai_provider import OpenAIProvider
from app.services.ai.multi_provider import MultiAIProviderService


MOCK_RESPONSE_JSON = '{"detections": [{"object_name": "cat", "confidence": 0.95, "bbox": null}], "metrics": {"brightness": 0.7}}'


@pytest.mark.asyncio
async def test_gemini_provider_parse():
    provider = GeminiProvider.__new__(GeminiProvider)
    result = provider._parse(MOCK_RESPONSE_JSON)
    assert len(result.detections) == 1
    assert result.detections[0].object_name == "cat"
    assert result.metrics["brightness"] == pytest.approx(0.7)


@pytest.mark.asyncio
async def test_openai_provider_parse():
    provider = OpenAIProvider.__new__(OpenAIProvider)
    result = provider._parse(MOCK_RESPONSE_JSON)
    assert result.detections[0].confidence == pytest.approx(0.95)


@pytest.mark.asyncio
async def test_multi_provider_falls_back_to_openai():
    fake_result = AnalysisResult(provider="openai", raw_response="{}", detections=[], metrics={})
    service = MultiAIProviderService.__new__(MultiAIProviderService)
    gemini_mock = AsyncMock(side_effect=RuntimeError("Gemini down"))
    openai_mock = AsyncMock(return_value=fake_result)
    service._providers = {"gemini": MagicMock(analyze=gemini_mock, name="gemini"),
                          "openai": MagicMock(analyze=openai_mock, name="openai")}
    service._primary = "gemini"
    service._fallback = "openai"
    from app.config.settings import settings
    result = await service.analyze("base64data")
    assert result.provider == "openai"
