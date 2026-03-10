import asyncio
import logging
import uuid
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.ai import tavily_client, claude_client
from app.ai.prompts.extraction_prompt import (
    EXTRACTION_SYSTEM_PROMPT,
    build_extraction_user_prompt,
)
from app.models.enrichment import EnrichmentResult
from app.models.api_cost_log import APICostLog

logger = logging.getLogger(__name__)

# Tavily cost per advanced search
TAVILY_COST_PER_SEARCH = 0.01


async def enrich_organization(
    db: AsyncSession,
    org_id: uuid.UUID,
    org_name: str,
    org_type: str,
    region: str | None,
    pipeline_run_id: uuid.UUID,
    deep_research: bool = False,
) -> EnrichmentResult:
    """Enrich a single organization.

    Standard mode: Tavily (general search) → Claude extraction
    Deep research:  Gemini (primary investment research) + Tavily (complementary
                    intelligence: LinkedIn, SEC, press, niche) in parallel → Claude extraction
    """

    enrichment = EnrichmentResult(
        id=str(uuid.uuid4()),
        organization_id=org_id,
        pipeline_run_id=pipeline_run_id,
        enrichment_status="pending",
        deep_research_enabled=deep_research,
    )

    try:
        if deep_research:
            await _enrich_deep_research(
                db, enrichment, org_id, org_name, org_type, region, pipeline_run_id
            )
        else:
            await _enrich_standard(
                db, enrichment, org_id, org_name, org_type, region, pipeline_run_id
            )

        enrichment.enrichment_status = "completed"
        enrichment.enriched_at = datetime.now(timezone.utc)

    except Exception as e:
        logger.error(f"Enrichment failed for {org_name}: {e}")
        enrichment.enrichment_status = "failed"
        enrichment.error_message = str(e)
        enrichment.data_quality = "low"

    db.add(enrichment)
    return enrichment


async def _enrich_standard(
    db: AsyncSession,
    enrichment: EnrichmentResult,
    org_id: str,
    org_name: str,
    org_type: str,
    region: str | None,
    pipeline_run_id: str,
) -> None:
    """Standard mode: Tavily general search → Claude extraction."""

    # Step 1: Tavily web search (general investment queries)
    search_results = await tavily_client.search_organization(org_name, org_type)

    enrichment.search_queries_used = search_results["queries_used"]
    enrichment.tavily_raw_results = search_results["results"]

    _log_tavily_cost(db, pipeline_run_id, org_id, search_results)

    # Step 2: Claude extraction with citations
    await _run_claude_extraction(
        db, enrichment, org_name, org_type, region, pipeline_run_id, org_id,
        tavily_results=search_results["results"],
        deep_research_text=None,
        deep_research_sources=None,
    )


async def _enrich_deep_research(
    db: AsyncSession,
    enrichment: EnrichmentResult,
    org_id: str,
    org_name: str,
    org_type: str,
    region: str | None,
    pipeline_run_id: str,
) -> None:
    """Deep research: Gemini (primary) + Tavily (complementary) in parallel → Claude extraction.

    Gemini: Deep investment research via Google Search grounding
            (AUM, mandates, allocations, ESG, emerging manager)
    Tavily: Complementary intelligence that Google can't access well
            (LinkedIn profiles, SEC filings, press releases, niche industry pubs)
    """
    from app.ai import gemini_client

    # Build a brief context hint for Gemini based on what we know from the CRM
    context_hint = (
        f"We are researching {org_name}, classified as a '{org_type}' in our CRM"
        f"{f', based in {region}' if region else ''}. "
        f"We need to determine if this organization is a capital allocator (LP) that invests "
        f"in external fund managers, find their AUM, investment mandates, fund allocations, "
        f"sustainability/ESG focus, and any emerging manager programs."
    )

    # Run Gemini and Tavily in PARALLEL — they search for different things
    gemini_task = asyncio.create_task(
        _run_gemini_research(org_name, org_type, context_hint)
    )
    tavily_task = asyncio.create_task(
        tavily_client.search_complementary_intelligence(org_name, org_type)
    )

    # Wait for both to complete
    gemini_response, tavily_complementary = await asyncio.gather(
        gemini_task, tavily_task, return_exceptions=True
    )

    # Handle Gemini results
    deep_research_text = None
    deep_research_sources = None

    if isinstance(gemini_response, Exception):
        logger.warning(f"Gemini deep research failed for {org_name}: {gemini_response}")
    else:
        deep_research_text = gemini_response.get("research_text", "")
        deep_research_sources = gemini_response.get("grounding_sources", [])
        enrichment.gemini_raw_response = gemini_response

        # Log Gemini costs
        gemini_cost_log = APICostLog(
            id=str(uuid.uuid4()),
            pipeline_run_id=pipeline_run_id,
            organization_id=org_id,
            provider="google",
            operation="deep_research",
            input_tokens=gemini_response.get("input_tokens", 0),
            output_tokens=gemini_response.get("output_tokens", 0),
            estimated_cost_usd=gemini_response.get("estimated_cost_usd", 0),
            latency_ms=gemini_response.get("latency_ms", 0),
        )
        db.add(gemini_cost_log)
        logger.info(
            f"Gemini deep research for {org_name}: "
            f"{len(deep_research_sources)} grounding sources"
        )

    # Handle Tavily complementary results
    tavily_results = {}
    if isinstance(tavily_complementary, Exception):
        logger.warning(f"Tavily complementary search failed for {org_name}: {tavily_complementary}")
    else:
        tavily_results = tavily_complementary["results"]
        enrichment.search_queries_used = tavily_complementary["queries_used"]
        enrichment.tavily_raw_results = tavily_results

        _log_tavily_cost(db, pipeline_run_id, org_id, tavily_complementary)
        logger.info(
            f"Tavily complementary for {org_name}: "
            f"{tavily_complementary['search_credits']} searches "
            f"(LinkedIn, SEC, press, niche)"
        )

    # Step 2: Claude extraction — receives BOTH Gemini research AND Tavily complementary
    await _run_claude_extraction(
        db, enrichment, org_name, org_type, region, pipeline_run_id, org_id,
        tavily_results=tavily_results,
        deep_research_text=deep_research_text,
        deep_research_sources=deep_research_sources,
    )


async def _run_gemini_research(
    org_name: str, org_type: str, context_hint: str | None = None
) -> dict:
    """Run Gemini grounded research (isolated for parallel execution)."""
    from app.ai import gemini_client

    return await gemini_client.grounded_research(
        org_name=org_name,
        org_type=org_type,
        tavily_summary=context_hint,
    )


async def _run_claude_extraction(
    db: AsyncSession,
    enrichment: EnrichmentResult,
    org_name: str,
    org_type: str,
    region: str | None,
    pipeline_run_id: str,
    org_id: str,
    tavily_results: dict,
    deep_research_text: str | None,
    deep_research_sources: list | None,
) -> None:
    """Run Claude extraction with numbered sources and citation tracking."""

    user_prompt, sources_list = build_extraction_user_prompt(
        org_name=org_name,
        org_type=org_type,
        region=region,
        search_results=tavily_results,
        deep_research_text=deep_research_text,
        deep_research_sources=deep_research_sources,
    )

    claude_response = await claude_client.call_claude(
        system_prompt=EXTRACTION_SYSTEM_PROMPT,
        user_prompt=user_prompt,
    )

    enrichment.claude_raw_response = claude_response["raw_text"]
    enrichment.sources = sources_list

    # Log Claude costs
    claude_cost_log = APICostLog(
        id=str(uuid.uuid4()),
        pipeline_run_id=pipeline_run_id,
        organization_id=org_id,
        provider="anthropic",
        operation="extraction",
        input_tokens=claude_response["input_tokens"],
        output_tokens=claude_response["output_tokens"],
        estimated_cost_usd=claude_response["estimated_cost_usd"],
        latency_ms=claude_response["latency_ms"],
    )
    db.add(claude_cost_log)

    # Parse extraction results + citations
    parsed = claude_response.get("parsed_json")
    if parsed:
        enrichment.aum_raw = parsed.get("aum")
        enrichment.aum_parsed = parsed.get("aum_parsed_usd")
        enrichment.is_capital_allocator = parsed.get("is_capital_allocator")
        enrichment.gp_service_provider_signals = parsed.get(
            "gp_service_provider_signals"
        )
        enrichment.investment_mandates = parsed.get("investment_mandates")
        enrichment.fund_allocations = parsed.get("fund_allocations")
        enrichment.sustainability_focus = parsed.get("sustainability_focus")
        enrichment.emerging_manager_evidence = parsed.get(
            "emerging_manager_evidence"
        )
        enrichment.brand_recognition = parsed.get("brand_recognition")
        enrichment.data_quality = parsed.get("data_quality")
        enrichment.key_findings_summary = parsed.get("key_findings_summary")

        # Extract citation indices into field_citations
        field_citations = {}
        for key in list(parsed.keys()):
            if key.endswith("_source_indices"):
                base_field = key.replace("_source_indices", "")
                indices = parsed[key]
                if isinstance(indices, list):
                    field_citations[base_field] = indices
        enrichment.field_citations = field_citations
    else:
        enrichment.data_quality = "low"
        enrichment.key_findings_summary = (
            "Failed to parse structured data from AI extraction."
        )
        logger.warning(f"Failed to parse Claude extraction for {org_name}")


def _log_tavily_cost(
    db: AsyncSession,
    pipeline_run_id: str,
    org_id: str,
    search_results: dict,
) -> None:
    """Log Tavily API costs."""
    tavily_cost_log = APICostLog(
        id=str(uuid.uuid4()),
        pipeline_run_id=pipeline_run_id,
        organization_id=org_id,
        provider="tavily",
        operation="search",
        search_credits=search_results["search_credits"],
        estimated_cost_usd=search_results["search_credits"] * TAVILY_COST_PER_SEARCH,
        latency_ms=search_results["total_latency_ms"],
    )
    db.add(tavily_cost_log)
