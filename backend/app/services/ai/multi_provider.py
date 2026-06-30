"""MultiAIProviderService — Indirection (GRASP): hides provider selection and retry from callers."""
import asyncio
import hashlib
import logging
import time

from app.config.settings import settings
from app.services.ai.base import AIProvider, AnalysisResult
from app.services.ai.ollama import OllamaProvider

logger = logging.getLogger(__name__)

_CACHE_TTL = 60.0
_RATE_LIMIT_COOLDOWN = 60.0


class MultiAIProviderService:
    def __init__(self) -> None:
        self._providers: dict[str, AIProvider] = {}
        self._order: list[str] = []
        self._build_providers()
        self._cache: dict[str, tuple[float, AnalysisResult]] = {}
        self._rate_limited_until: dict[str, float] = {}

    def _build_providers(self) -> None:
        """Register available providers. Ollama is local-first; cloud is opt-in.

        Cloud providers (Gemini/OpenAI) are only constructed when allow_cloud is
        true AND their API key is present, so a default install never reaches out
        to the network and never imports the cloud SDKs.
        """
        providers: dict[str, AIProvider] = {}
        if settings.ollama_enabled:
            providers["ollama"] = OllamaProvider()
        if settings.allow_cloud and settings.gemini_api_key:
            from app.services.ai.gemini import GeminiProvider
            providers["gemini"] = GeminiProvider()
        if settings.allow_cloud and settings.openai_api_key:
            from app.services.ai.openai_provider import OpenAIProvider
            providers["openai"] = OpenAIProvider()

        if not providers:
            # Keep Ollama registered even if disabled, so errors are actionable
            # rather than a bare "no providers" at call time.
            providers["ollama"] = OllamaProvider()

        # Try the configured primary first, then any remaining providers.
        order = [settings.ai_primary_provider] if settings.ai_primary_provider in providers else []
        order += [name for name in providers if name not in order]

        self._providers = providers
        self._order = order
        logger.info("AI providers registered: %s (order: %s)", list(providers), order)

    def reload(self) -> None:
        """Rebuild providers after a runtime config change (e.g. PATCH /config)."""
        self._build_providers()
        self._cache.clear()

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

        for provider_name in self._order:
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
                    # repr() not str(): httpx timeout exceptions stringify to ''
                    # which produced uninformative "failed: " lines in the logs.
                    detail = str(exc) or repr(exc)
                    logger.warning("Provider %s attempt %d/%d failed: %s — retrying in %.1fs", provider_name, attempt + 1, settings.ai_retry_max, detail, wait)
                    if attempt < settings.ai_retry_max - 1:
                        await asyncio.sleep(wait)
            else:
                remaining = [n for n in self._order if n != provider_name]
                if remaining:
                    logger.error("Provider %s exhausted retries, trying next: %s", provider_name, remaining[0])
                else:
                    logger.error(
                        "Provider %s exhausted retries and no fallback is configured. "
                        "Ensure Ollama is running (systemctl start ollama) or set allow_cloud=true with an API key.",
                        provider_name,
                    )
        raise RuntimeError("All AI providers exhausted")


multi_ai_service = MultiAIProviderService()
