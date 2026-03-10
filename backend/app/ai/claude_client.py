import json
import logging
import time

import anthropic

from app.config import get_settings
from app.core.rate_limiter import TokenBucketRateLimiter
from app.core.retry import async_retry

logger = logging.getLogger(__name__)

settings = get_settings()

_rate_limiter = TokenBucketRateLimiter(
    rate=settings.claude_requests_per_minute, period=60.0
)

_client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)

# Cost constants (Claude Sonnet pricing)
INPUT_COST_PER_TOKEN = 3.0 / 1_000_000   # $3/MTok
OUTPUT_COST_PER_TOKEN = 15.0 / 1_000_000  # $15/MTok


@async_retry(max_retries=2, base_delay=2.0, exceptions=(Exception,))
async def call_claude(
    system_prompt: str,
    user_prompt: str,
    max_tokens: int | None = None,
) -> dict:
    """Call Claude API with rate limiting and retry. Returns parsed response + usage."""
    await _rate_limiter.acquire()

    start = time.monotonic()

    response = await _client.messages.create(
        model=settings.claude_model,
        max_tokens=max_tokens or settings.claude_max_tokens,
        system=system_prompt,
        messages=[{"role": "user", "content": user_prompt}],
    )

    latency = int((time.monotonic() - start) * 1000)
    raw_text = response.content[0].text

    input_tokens = response.usage.input_tokens
    output_tokens = response.usage.output_tokens
    estimated_cost = (
        input_tokens * INPUT_COST_PER_TOKEN + output_tokens * OUTPUT_COST_PER_TOKEN
    )

    logger.info(
        f"Claude call completed in {latency}ms | "
        f"tokens: {input_tokens}in/{output_tokens}out | "
        f"cost: ${estimated_cost:.4f}"
    )

    # Try to parse JSON from response
    parsed_json = None
    try:
        # Handle markdown code blocks
        text = raw_text.strip()
        if text.startswith("```"):
            text = text.split("\n", 1)[1] if "\n" in text else text[3:]
            if text.endswith("```"):
                text = text[:-3].strip()
        parsed_json = json.loads(text)
    except json.JSONDecodeError:
        # Try to find JSON in the response
        try:
            start_idx = raw_text.index("{")
            end_idx = raw_text.rindex("}") + 1
            parsed_json = json.loads(raw_text[start_idx:end_idx])
        except (ValueError, json.JSONDecodeError):
            logger.warning("Failed to parse JSON from Claude response")

    return {
        "raw_text": raw_text,
        "parsed_json": parsed_json,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "estimated_cost_usd": estimated_cost,
        "latency_ms": latency,
    }
