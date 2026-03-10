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


@async_retry(max_retries=2, base_delay=2.0, exceptions=(Exception,))
async def search(query: str) -> dict:
    """Execute a single Tavily search with rate limiting and retry."""
    await _rate_limiter.acquire()

    client = AsyncTavilyClient(api_key=settings.tavily_api_key)
    start = time.monotonic()

    result = await client.search(
        query=query,
        search_depth="advanced",
        max_results=5,
        include_answer=True,
        include_raw_content=False,
        exclude_domains=["linkedin.com", "glassdoor.com", "indeed.com"],
    )

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
    """Run 2-3 targeted searches for an organization."""
    queries_used = []
    all_results = {}

    # Query 1: Investment Profile (always)
    q1 = build_investment_query(org_name, org_type)
    queries_used.append(q1)
    r1 = await search(q1)
    all_results["investment_profile"] = r1

    # Query 2: Sustainability (always)
    q2 = build_sustainability_query(org_name)
    queries_used.append(q2)
    r2 = await search(q2)
    all_results["sustainability"] = r2

    # Query 3: Emerging Manager (conditional — only if Q1 had >= 3 results)
    search_credits = 2
    if len(r1.get("results", [])) >= 3:
        q3 = build_emerging_manager_query(org_name)
        queries_used.append(q3)
        r3 = await search(q3)
        all_results["emerging_manager"] = r3
        search_credits = 3

    return {
        "queries_used": queries_used,
        "results": all_results,
        "search_credits": search_credits,
        "total_latency_ms": sum(
            r.get("latency_ms", 0) for r in all_results.values()
        ),
    }
