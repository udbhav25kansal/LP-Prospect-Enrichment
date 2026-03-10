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
) -> EnrichmentResult:
    """Enrich a single organization using Tavily search + Claude extraction."""

    enrichment = EnrichmentResult(
        id=str(uuid.uuid4()),
        organization_id=org_id,
        pipeline_run_id=pipeline_run_id,
        enrichment_status="pending",
    )

    try:
        # Step 1: Tavily web search
        search_results = await tavily_client.search_organization(org_name, org_type)

        enrichment.search_queries_used = search_results["queries_used"]
        enrichment.tavily_raw_results = search_results["results"]

        # Log Tavily costs
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

        # Step 2: Claude extraction
        user_prompt = build_extraction_user_prompt(
            org_name=org_name,
            org_type=org_type,
            region=region,
            search_results=search_results["results"],
        )

        claude_response = await claude_client.call_claude(
            system_prompt=EXTRACTION_SYSTEM_PROMPT,
            user_prompt=user_prompt,
        )

        enrichment.claude_raw_response = claude_response["raw_text"]

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

        # Step 3: Parse extraction results
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
        else:
            enrichment.data_quality = "low"
            enrichment.key_findings_summary = (
                "Failed to parse structured data from AI extraction."
            )
            logger.warning(f"Failed to parse Claude extraction for {org_name}")

        enrichment.enrichment_status = "completed"
        enrichment.enriched_at = datetime.now(timezone.utc)

    except Exception as e:
        logger.error(f"Enrichment failed for {org_name}: {e}")
        enrichment.enrichment_status = "failed"
        enrichment.error_message = str(e)
        enrichment.data_quality = "low"

    db.add(enrichment)
    return enrichment
