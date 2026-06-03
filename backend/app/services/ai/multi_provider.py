"""MultiAIProviderService — Indirection (GRASP): hides provider selection and retry from callers."""
import asyncio
import hashlib
import logging
import time

from app.config.settings import settings
from app.services.ai.base import AIProvider, AnalysisResult
from app.services.ai.gemini import GeminiProvider
from app.services.ai.openai_provider import OpenAIProvider

logger = logging.getLogger(__name__)

_CACHE_TTL = 60.0
_RATE_LIMIT_COOLDOWN = 60.0


class MultiAIProviderService:
    def __init__(self) -> None:
        self._providers: dict[str, AIProvider] = {
            "gemini": GeminiProvider(),
            "openai": OpenAIProvider(),
        }
        self._primary = settings.ai_primary_provider
        self._fallback = "openai" if self._primary == "gemini" else "gemini"
        self._cache: dict[str, tuple[float, AnalysisResult]] = {}
        self._rate_limited_until: dict[str, float] = {}

    def _cache_key(self, frame_base64: str, prompt: str | None) -> str:
        h = hashlib.sha256((frame_base64[:512] + str(prompt)).encode()).hexdigest()[:16]
        return h

    def _get_cached(self, key: str) -> AnalysisResult | None:
        entry = self._cache.get(key)
        if entry and (time.monotonic() - entry[0]) < _CACHE_TTL:
            return entry[1]
        return None

    @staticmethod
    def _is_rate_limited(exc: Exception) -> bool:
        msg = str(exc)
        return "429" in msg or "RESOURCE_EXHAUSTED" in msg or "RateLimitError" in type(exc).__name__

    async def analyze(self, frame_base64: str, prompt: str | None = None) -> AnalysisResult:
        key = self._cache_key(frame_base64, prompt)
        cached = self._get_cached(key)
        if cached:
            logger.debug("AI cache hit for key %s", key)
            return cached

        for provider_name in (self._primary, self._fallback):
            cooldown_until = self._rate_limited_until.get(provider_name, 0)
            if time.monotonic() < cooldown_until:
                remaining = cooldown_until - time.monotonic()
                logger.warning("Provider %s in rate-limit cooldown for %.0fs, skipping", provider_name, remaining)
                continue

            provider = self._providers[provider_name]
            for attempt in range(settings.ai_retry_max):
                try:
                    result = await provider.analyze(frame_base64, prompt)
                    self._cache[key] = (time.monotonic(), result)
                    return result
                except Exception as exc:
                    if self._is_rate_limited(exc):
                        self._rate_limited_until[provider_name] = time.monotonic() + _RATE_LIMIT_COOLDOWN
                        logger.warning(
                            "Provider %s rate-limited (429), cooling down for %.0fs", provider_name, _RATE_LIMIT_COOLDOWN
                        )
                        break
                    wait = settings.ai_retry_backoff_base ** attempt
                    logger.warning("Provider %s attempt %d failed: %s — retrying in %.1fs", provider_name, attempt + 1, exc, wait)
                    if attempt < settings.ai_retry_max - 1:
                        await asyncio.sleep(wait)
            else:
                logger.error("Provider %s exhausted retries, switching to fallback", provider_name)
        raise RuntimeError("All AI providers exhausted")


multi_ai_service = MultiAIProviderService()
