import logging
import uuid
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.ai import claude_client
from app.ai.prompts.scoring_prompt import SCORING_SYSTEM_PROMPT, build_scoring_user_prompt
from app.config import get_settings
from app.models.enrichment import EnrichmentResult
from app.models.score import Score
from app.models.api_cost_log import APICostLog

logger = logging.getLogger(__name__)
settings = get_settings()

# Check size allocation percentages by org type
CHECK_SIZE_ALLOCATIONS = {
    "Pension": (0.005, 0.02),
    "Insurance": (0.005, 0.02),
    "Endowment": (0.01, 0.03),
    "Foundation": (0.01, 0.03),
    "Fund of Funds": (0.02, 0.05),
    "Multi-Family Office": (0.02, 0.05),
    "Single Family Office": (0.03, 0.10),
    "HNWI": (0.03, 0.10),
    "Asset Manager": (0.005, 0.03),
    "RIA/FIA": (0.005, 0.03),
    "Private Capital Firm": (0.005, 0.03),
}


def classify_tier(composite: float) -> str:
    if composite >= settings.tier_priority_close:
        return "PRIORITY CLOSE"
    elif composite >= settings.tier_strong_fit:
        return "STRONG FIT"
    elif composite >= settings.tier_moderate_fit:
        return "MODERATE FIT"
    else:
        return "WEAK FIT"


def estimate_check_size(
    aum_parsed: int | None, org_type: str
) -> tuple[int | None, int | None]:
    """Estimate check size range based on AUM and org type."""
    if not aum_parsed or aum_parsed <= 0:
        return None, None

    alloc_range = CHECK_SIZE_ALLOCATIONS.get(org_type, (0.01, 0.03))
    check_min = int(aum_parsed * alloc_range[0])
    check_max = int(aum_parsed * alloc_range[1])
    return check_min, check_max


async def score_organization(
    db: AsyncSession,
    org_id: uuid.UUID,
    org_name: str,
    org_type: str,
    region: str | None,
    enrichment: EnrichmentResult,
    relationship_depth: int,
    pipeline_run_id: uuid.UUID,
) -> Score:
    """Score a single organization using Claude + enrichment data."""

    used_defaults = False

    # Build enrichment data dict for prompt
    enrichment_data = {
        "aum_raw": enrichment.aum_raw,
        "is_capital_allocator": enrichment.is_capital_allocator,
        "gp_service_provider_signals": enrichment.gp_service_provider_signals,
        "investment_mandates": enrichment.investment_mandates,
        "fund_allocations": enrichment.fund_allocations,
        "sustainability_focus": enrichment.sustainability_focus,
        "emerging_manager_evidence": enrichment.emerging_manager_evidence,
        "brand_recognition": enrichment.brand_recognition,
        "data_quality": enrichment.data_quality,
        "key_findings_summary": enrichment.key_findings_summary,
    }

    # Call Claude for scoring
    try:
        user_prompt = build_scoring_user_prompt(
            org_name=org_name,
            org_type=org_type,
            region=region,
            enrichment_data=enrichment_data,
        )

        claude_response = await claude_client.call_claude(
            system_prompt=SCORING_SYSTEM_PROMPT,
            user_prompt=user_prompt,
        )

        # Log Claude cost
        cost_log = APICostLog(
            id=str(uuid.uuid4()),
            pipeline_run_id=pipeline_run_id,
            organization_id=org_id,
            provider="anthropic",
            operation="scoring",
            input_tokens=claude_response["input_tokens"],
            output_tokens=claude_response["output_tokens"],
            estimated_cost_usd=claude_response["estimated_cost_usd"],
            latency_ms=claude_response["latency_ms"],
        )
        db.add(cost_log)

        parsed = claude_response.get("parsed_json")
        if parsed:
            d1 = float(parsed.get("d1_sector_fit", settings.default_d1_score))
            d3 = float(parsed.get("d3_halo_value", settings.default_d3_score))
            d4 = float(parsed.get("d4_emerging_fit", settings.default_d4_score))

            # Clamp to 1-10
            d1 = max(1.0, min(10.0, d1))
            d3 = max(1.0, min(10.0, d3))
            d4 = max(1.0, min(10.0, d4))

            d1_confidence = parsed.get("d1_confidence", "low")
            d1_reasoning = parsed.get("d1_reasoning", "Score provided by AI without detailed reasoning.")
            d3_confidence = parsed.get("d3_confidence", "low")
            d3_reasoning = parsed.get("d3_reasoning", "Score provided by AI without detailed reasoning.")
            d4_confidence = parsed.get("d4_confidence", "low")
            d4_reasoning = parsed.get("d4_reasoning", "Score provided by AI without detailed reasoning.")
            is_lp = parsed.get("is_lp_not_gp")
            org_type_assessment = parsed.get("org_type_assessment")
        else:
            # Use defaults
            d1 = settings.default_d1_score
            d3 = settings.default_d3_score
            d4 = settings.default_d4_score
            d1_confidence = "low"
            d1_reasoning = "Default score used — AI extraction failed."
            d3_confidence = "low"
            d3_reasoning = "Default score used — AI extraction failed."
            d4_confidence = "low"
            d4_reasoning = "Default score used — AI extraction failed."
            is_lp = None
            org_type_assessment = None
            used_defaults = True

    except Exception as e:
        logger.error(f"Scoring failed for {org_name}: {e}")
        d1 = settings.default_d1_score
        d3 = settings.default_d3_score
        d4 = settings.default_d4_score
        d1_confidence = "low"
        d1_reasoning = f"Default score used — scoring error: {str(e)[:200]}"
        d3_confidence = "low"
        d3_reasoning = f"Default score used — scoring error: {str(e)[:200]}"
        d4_confidence = "low"
        d4_reasoning = f"Default score used — scoring error: {str(e)[:200]}"
        is_lp = None
        org_type_assessment = None
        used_defaults = True

    # D2 from CSV (pre-computed)
    d2 = float(relationship_depth)

    # Composite score
    composite = (
        d1 * settings.d1_weight
        + d2 * settings.d2_weight
        + d3 * settings.d3_weight
        + d4 * settings.d4_weight
    )
    composite = round(composite, 2)

    tier = classify_tier(composite)

    # Check size estimation
    check_min, check_max = estimate_check_size(enrichment.aum_parsed, org_type)

    score = Score(
        id=str(uuid.uuid4()),
        organization_id=org_id,
        pipeline_run_id=pipeline_run_id,
        enrichment_id=enrichment.id,
        d1_sector_fit=d1,
        d1_confidence=d1_confidence,
        d1_reasoning=d1_reasoning,
        d2_relationship=d2,
        d3_halo_value=d3,
        d3_confidence=d3_confidence,
        d3_reasoning=d3_reasoning,
        d4_emerging_fit=d4,
        d4_confidence=d4_confidence,
        d4_reasoning=d4_reasoning,
        composite_score=composite,
        tier=tier,
        check_size_min=check_min,
        check_size_max=check_max,
        is_lp_not_gp=is_lp,
        org_type_assessment=org_type_assessment,
        used_default_scores=used_defaults,
        scored_at=datetime.now(timezone.utc),
    )

    db.add(score)
    return score
