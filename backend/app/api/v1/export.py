import csv
import io
import logging

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy import select, desc, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.organization import Organization
from app.models.contact import Contact
from app.models.enrichment import EnrichmentResult
from app.models.score import Score
from app.models.validation_flag import ValidationFlag

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/csv")
async def export_csv(
    db: AsyncSession = Depends(get_db),
    run_id: str | None = None,
):
    """Export scored prospects as CSV."""

    # Query all scored orgs
    query = (
        select(
            Organization.name,
            Organization.org_type,
            Organization.region,
            Score.d1_sector_fit,
            Score.d1_confidence,
            Score.d1_reasoning,
            Score.d2_relationship,
            Score.d3_halo_value,
            Score.d3_confidence,
            Score.d3_reasoning,
            Score.d4_emerging_fit,
            Score.d4_confidence,
            Score.d4_reasoning,
            Score.composite_score,
            Score.tier,
            Score.check_size_min,
            Score.check_size_max,
            Score.is_lp_not_gp,
            Score.org_type_assessment,
            Score.used_default_scores,
            EnrichmentResult.aum_raw,
            EnrichmentResult.aum_parsed,
            EnrichmentResult.investment_mandates,
            EnrichmentResult.fund_allocations,
            EnrichmentResult.sustainability_focus,
            EnrichmentResult.emerging_manager_evidence,
            EnrichmentResult.is_capital_allocator,
            EnrichmentResult.brand_recognition,
            EnrichmentResult.data_quality,
            EnrichmentResult.key_findings_summary,
            EnrichmentResult.deep_research_enabled,
        )
        .join(Score, Score.organization_id == Organization.id)
        .join(EnrichmentResult, EnrichmentResult.id == Score.enrichment_id)
        .order_by(desc(Score.composite_score))
    )

    if run_id:
        query = query.where(Score.pipeline_run_id == run_id)

    result = await db.execute(query)
    rows = result.all()

    # Build CSV
    output = io.StringIO()
    writer = csv.writer(output)

    # Header
    writer.writerow([
        "Organization",
        "Org Type",
        "Region",
        "Composite Score",
        "Tier",
        "D1 Sector Fit",
        "D1 Confidence",
        "D1 Reasoning",
        "D2 Relationship",
        "D3 Halo Value",
        "D3 Confidence",
        "D3 Reasoning",
        "D4 Emerging Fit",
        "D4 Confidence",
        "D4 Reasoning",
        "AUM",
        "AUM (USD)",
        "Check Size Min",
        "Check Size Max",
        "Is LP",
        "AI Org Type Assessment",
        "Is Capital Allocator",
        "Investment Mandates",
        "Fund Allocations",
        "Sustainability Focus",
        "Emerging Manager Evidence",
        "Brand Recognition",
        "Data Quality",
        "Key Findings",
        "Deep Research",
        "Used Default Scores",
    ])

    # Data rows
    for row in rows:
        mandates = row.investment_mandates
        if isinstance(mandates, list):
            mandates = "; ".join(mandates)
        allocations = row.fund_allocations
        if isinstance(allocations, list):
            allocations = "; ".join(allocations)

        writer.writerow([
            row.name,
            row.org_type,
            row.region or "",
            row.composite_score,
            row.tier,
            row.d1_sector_fit,
            row.d1_confidence or "",
            row.d1_reasoning or "",
            row.d2_relationship,
            row.d3_halo_value,
            row.d3_confidence or "",
            row.d3_reasoning or "",
            row.d4_emerging_fit,
            row.d4_confidence or "",
            row.d4_reasoning or "",
            row.aum_raw or "",
            row.aum_parsed or "",
            row.check_size_min or "",
            row.check_size_max or "",
            "Yes" if row.is_lp_not_gp else "No" if row.is_lp_not_gp is False else "",
            row.org_type_assessment or "",
            "Yes" if row.is_capital_allocator else "No" if row.is_capital_allocator is False else "",
            mandates or "",
            allocations or "",
            row.sustainability_focus or "",
            row.emerging_manager_evidence or "",
            row.brand_recognition or "",
            row.data_quality or "",
            row.key_findings_summary or "",
            "Yes" if row.deep_research_enabled else "No",
            "Yes" if row.used_default_scores else "No",
        ])

    output.seek(0)

    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=prospect_scores.csv"},
    )


@router.get("/json")
async def export_json(
    db: AsyncSession = Depends(get_db),
    run_id: str | None = None,
):
    """Export scored prospects as JSON (for sample output)."""

    query = (
        select(
            Organization.name,
            Organization.org_type,
            Organization.region,
            Score.d1_sector_fit,
            Score.d1_confidence,
            Score.d1_reasoning,
            Score.d2_relationship,
            Score.d3_halo_value,
            Score.d3_confidence,
            Score.d3_reasoning,
            Score.d4_emerging_fit,
            Score.d4_confidence,
            Score.d4_reasoning,
            Score.composite_score,
            Score.tier,
            Score.check_size_min,
            Score.check_size_max,
            Score.is_lp_not_gp,
            Score.org_type_assessment,
            EnrichmentResult.aum_raw,
            EnrichmentResult.aum_parsed,
            EnrichmentResult.investment_mandates,
            EnrichmentResult.fund_allocations,
            EnrichmentResult.sustainability_focus,
            EnrichmentResult.emerging_manager_evidence,
            EnrichmentResult.is_capital_allocator,
            EnrichmentResult.brand_recognition,
            EnrichmentResult.data_quality,
            EnrichmentResult.key_findings_summary,
            EnrichmentResult.deep_research_enabled,
        )
        .join(Score, Score.organization_id == Organization.id)
        .join(EnrichmentResult, EnrichmentResult.id == Score.enrichment_id)
        .order_by(desc(Score.composite_score))
    )

    if run_id:
        query = query.where(Score.pipeline_run_id == run_id)

    result = await db.execute(query)
    rows = result.all()

    prospects = []
    for row in rows:
        prospects.append({
            "organization": row.name,
            "org_type": row.org_type,
            "region": row.region,
            "composite_score": float(row.composite_score),
            "tier": row.tier,
            "scores": {
                "d1_sector_fit": float(row.d1_sector_fit),
                "d1_confidence": row.d1_confidence,
                "d1_reasoning": row.d1_reasoning,
                "d2_relationship": float(row.d2_relationship),
                "d3_halo_value": float(row.d3_halo_value),
                "d3_confidence": row.d3_confidence,
                "d3_reasoning": row.d3_reasoning,
                "d4_emerging_fit": float(row.d4_emerging_fit),
                "d4_confidence": row.d4_confidence,
                "d4_reasoning": row.d4_reasoning,
            },
            "enrichment": {
                "aum": row.aum_raw,
                "aum_usd": row.aum_parsed,
                "check_size_min": row.check_size_min,
                "check_size_max": row.check_size_max,
                "is_lp": row.is_lp_not_gp,
                "is_capital_allocator": row.is_capital_allocator,
                "org_type_assessment": row.org_type_assessment,
                "investment_mandates": row.investment_mandates,
                "fund_allocations": row.fund_allocations,
                "sustainability_focus": row.sustainability_focus,
                "emerging_manager_evidence": row.emerging_manager_evidence,
                "brand_recognition": row.brand_recognition,
                "data_quality": row.data_quality,
                "key_findings": row.key_findings_summary,
                "deep_research": row.deep_research_enabled or False,
            },
        })

    return {"total": len(prospects), "prospects": prospects}
