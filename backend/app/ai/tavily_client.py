import logging
import time
from tavily import AsyncTavilyClient

from app.config import get_settings
from app.core.rate_limiter import TokenBucketRateLimiter
from app.core.retry import async_retry

logger = logging.getLogger(__name__)

settings = get_settings()

_rate_limiter = TokenBucketRateLimiter(
    rate=settings.tavily_requests_per_minute, period=60.0
)


def build_investment_query(org_name: str, org_type: str) -> str:
    """Build org-type-aware investment profile search query."""
    if org_type in ("Foundation", "Endowment", "Pension"):
        return (
            f'"{org_name}" investment portfolio allocations '
            f"private credit private debt fund commitments AUM"
        )
    elif org_type in ("Single Family Office", "Multi-Family Office", "HNWI"):
        return (
            f'"{org_name}" family office investments '
            f"fund allocations alternative investments portfolio"
        )
    elif org_type == "Fund of Funds":
        return (
            f'"{org_name}" fund of funds portfolio '
            f"manager selection alternative investments commitments"
        )
    elif org_type in ("RIA/FIA", "Asset Manager", "Private Capital Firm"):
        return (
            f'"{org_name}" investment advisory asset management '
            f"fund allocations OR origination OR lending"
        )
    elif org_type == "Insurance":
        return (
            f'"{org_name}" insurance investment portfolio '
            f"alternative investments private credit allocations"
        )
    else:
        return (
            f'"{org_name}" investment portfolio allocations '
            f"alternative investments private credit"
        )


def build_sustainability_query(org_name: str) -> str:
    """Build ESG/sustainability search query."""
    return (
        f'"{org_name}" ESG sustainability impact investing '
        f"climate responsible investing"
    )


def build_emerging_manager_query(org_name: str) -> str:
    """Build emerging manager search query."""
    return (
        f'"{org_name}" emerging manager program '
        f"first-time fund commitment new manager allocation"
    )


# --- Complementary Intelligence Queries (for Deep Research mode) ---

def build_linkedin_query(org_name: str) -> str:
    """Build LinkedIn-focused query for investment team profiles."""
    return (
        f'site:linkedin.com "{org_name}" '
        f"CIO OR \"Chief Investment\" OR \"portfolio manager\" OR \"investment director\" "
        f"OR \"head of alternatives\""
    )


def build_regulatory_query(org_name: str, org_type: str) -> str:
    """Build SEC/regulatory filings query."""
    if org_type in ("Foundation", "Endowment"):
        return (
            f'"{org_name}" site:sec.gov OR site:irs.gov OR "990-PF" OR "form ADV" '
            f"investment portfolio filings"
        )
    return (
        f'"{org_name}" site:sec.gov OR "form ADV" OR "13F" '
        f"regulatory filing investment"
    )


def build_news_press_query(org_name: str) -> str:
    """Build press releases and news query."""
    return (
        f'"{org_name}" fund commitment OR allocation OR investment OR appointed '
        f"site:prnewswire.com OR site:businesswire.com OR site:reuters.com OR site:bloomberg.com"
    )


def build_industry_niche_query(org_name: str) -> str:
    """Build niche industry publication query (PitchBook, Preqin, Institutional Investor, etc.)."""
    return (
        f'"{org_name}" '
        f"site:pitchbook.com OR site:preqin.com OR site:institutionalinvestor.com "
        f"OR site:pionline.com OR site:ai-cio.com OR site:swfinstitute.org"
    )


@async_retry(max_retries=4, base_delay=5.0, exceptions=(Exception,))
async def search(query: str, include_linkedin: bool = False) -> dict:
    """Execute a single Tavily search with rate limiting and retry."""
    await _rate_limiter.acquire()

    client = AsyncTavilyClient(api_key=settings.tavily_api_key)
    start = time.monotonic()

    exclude = ["glassdoor.com", "indeed.com"]
    if not include_linkedin:
        exclude.append("linkedin.com")

    try:
        result = await client.search(
            query=query,
            search_depth="advanced",
            max_results=5,
            include_answer=True,
            include_raw_content=False,
            exclude_domains=exclude,
        )
    except Exception as e:
        logger.error(f"Tavily search error for query '{query[:60]}...': {type(e).__name__}: {e}")
        raise

    latency = int((time.monotonic() - start) * 1000)
    logger.info(f"Tavily search completed in {latency}ms: {query[:80]}...")

    return {
        "query": query,
        "answer": result.get("answer", ""),
        "results": [
            {
                "title": r.get("title", ""),
                "url": r.get("url", ""),
                "content": r.get("content", ""),
                "score": r.get("score", 0),
            }
            for r in result.get("results", [])
        ],
        "latency_ms": latency,
    }


async def search_organization(org_name: str, org_type: str) -> dict:
    """Run 3 targeted searches for an organization in parallel."""
    import asyncio

    q1 = build_investment_query(org_name, org_type)
    q2 = build_sustainability_query(org_name)
    q3 = build_emerging_manager_query(org_name)

    # Run all 3 searches in parallel
    r1, r2, r3 = await asyncio.gather(
        search(q1), search(q2), search(q3), return_exceptions=True
    )

    queries_used = [q1, q2, q3]
    all_results = {}
    search_credits = 0

    for key, result in [("investment_profile", r1), ("sustainability", r2), ("emerging_manager", r3)]:
        if not isinstance(result, Exception):
            all_results[key] = result
            search_credits += 1

    return {
        "queries_used": queries_used,
        "results": all_results,
        "search_credits": search_credits,
        "total_latency_ms": max(
            (r.get("latency_ms", 0) for r in all_results.values()), default=0
        ),
    }


async def search_complementary_intelligence(org_name: str, org_type: str) -> dict:
    """Run complementary intelligence searches (for Deep Research mode).

    These searches target sources that Gemini/Google Search can't access well:
    LinkedIn profiles, SEC filings, press releases, niche industry publications.
    """
    import asyncio

    q1 = build_linkedin_query(org_name)
    q2 = build_regulatory_query(org_name, org_type)
    q3 = build_news_press_query(org_name)
    q4 = build_industry_niche_query(org_name)

    # Run all 4 searches in parallel
    r1, r2, r3, r4 = await asyncio.gather(
        search(q1, include_linkedin=True),
        search(q2),
        search(q3),
        search(q4),
        return_exceptions=True,
    )

    queries_used = [q1, q2, q3, q4]
    all_results = {}
    search_credits = 0

    for key, result in [
        ("linkedin_profiles", r1),
        ("regulatory_filings", r2),
        ("press_releases", r3),
        ("industry_publications", r4),
    ]:
        if not isinstance(result, Exception):
            all_results[key] = result
            search_credits += 1

    return {
        "queries_used": queries_used,
        "results": all_results,
        "search_credits": search_credits,
        "total_latency_ms": max(
            (r.get("latency_ms", 0) for r in all_results.values()), default=0
        ),
    }
