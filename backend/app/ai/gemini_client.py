import logging
import time

from google import genai
from google.genai import types

from app.config import get_settings
from app.core.rate_limiter import TokenBucketRateLimiter
from app.core.retry import async_retry
from app.ai.prompts.deep_research_prompt import (
    DEEP_RESEARCH_SYSTEM_PROMPT,
    build_deep_research_prompt,
)

logger = logging.getLogger(__name__)

settings = get_settings()

_rate_limiter = TokenBucketRateLimiter(
    rate=settings.gemini_requests_per_minute, period=60.0
)

# Gemini pricing (per 1M tokens, approximate for 2.5 Pro)
GEMINI_INPUT_COST_PER_1M = 1.25
GEMINI_OUTPUT_COST_PER_1M = 10.00


@async_retry(max_retries=2, base_delay=3.0, exceptions=(Exception,))
async def grounded_research(
    org_name: str,
    org_type: str,
    tavily_summary: str,
) -> dict:
    """Conduct deep grounded research on an organization using Gemini + Google Search.

    Returns dict with: research_text, grounding_sources, input_tokens, output_tokens,
    estimated_cost_usd, latency_ms
    """
    await _rate_limiter.acquire()

    client = genai.Client(api_key=settings.gemini_api_key)

    user_prompt = build_deep_research_prompt(org_name, org_type, tavily_summary)

    start = time.monotonic()

    response = await client.aio.models.generate_content(
        model=settings.gemini_model,
        contents=user_prompt,
        config=types.GenerateContentConfig(
            system_instruction=DEEP_RESEARCH_SYSTEM_PROMPT,
            tools=[types.Tool(google_search=types.GoogleSearch())],
            temperature=0.2,
        ),
    )

    latency = int((time.monotonic() - start) * 1000)

    # Extract research text
    research_text = response.text or ""

    # Extract grounding sources from metadata
    grounding_sources = []
    if response.candidates:
        candidate = response.candidates[0]
        grounding_meta = getattr(candidate, "grounding_metadata", None)
        if grounding_meta:
            chunks = getattr(grounding_meta, "grounding_chunks", []) or []
            for chunk in chunks:
                web = getattr(chunk, "web", None)
                if web:
                    grounding_sources.append({
                        "title": getattr(web, "title", "") or "",
                        "url": getattr(web, "uri", "") or "",
                    })

    # Token usage
    usage = getattr(response, "usage_metadata", None)
    input_tokens = getattr(usage, "prompt_token_count", 0) or 0 if usage else 0
    output_tokens = getattr(usage, "candidates_token_count", 0) or 0 if usage else 0

    estimated_cost = (
        (input_tokens / 1_000_000) * GEMINI_INPUT_COST_PER_1M
        + (output_tokens / 1_000_000) * GEMINI_OUTPUT_COST_PER_1M
    )

    logger.info(
        f"Gemini deep research for {org_name}: {len(grounding_sources)} sources, "
        f"{input_tokens}+{output_tokens} tokens, {latency}ms"
    )

    return {
        "research_text": research_text,
        "grounding_sources": grounding_sources,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "estimated_cost_usd": round(estimated_cost, 6),
        "latency_ms": latency,
    }
