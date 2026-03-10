import logging

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, func, case
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.organization import Organization
from app.models.contact import Contact
from app.models.score import Score
from app.models.enrichment import EnrichmentResult
from app.models.validation_flag import ValidationFlag
from app.schemas.common import DashboardSummary, ProspectSummary

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/summary", response_model=DashboardSummary)
async def get_dashboard_summary(
    db: AsyncSession = Depends(get_db),
    run_id: str | None = None,
):
    """Get dashboard summary data."""

    score_filter = []
    if run_id:
        score_filter.append(Score.pipeline_run_id == run_id)

    # Tier counts
    tier_q = (
        select(Score.tier, func.count(Score.id))
        .where(*score_filter)
        .group_by(Score.tier)
    )
    tier_result = await db.execute(tier_q)
    tier_counts = {row[0]: row[1] for row in tier_result.all()}

    # Ensure all tiers present
    for t in ["PRIORITY CLOSE", "STRONG FIT", "MODERATE FIT", "WEAK FIT"]:
        tier_counts.setdefault(t, 0)

    # Average composite
    avg_q = select(func.avg(Score.composite_score)).where(*score_filter)
    avg_result = await db.execute(avg_q)
    avg_composite = float(avg_result.scalar_one_or_none() or 0)

    # Total orgs and contacts
    total_orgs = sum(tier_counts.values())

    contact_q = select(func.count(Contact.id))
    total_contacts = (await db.execute(contact_q)).scalar_one()

    # Org type breakdown
    type_q = (
        select(Organization.org_type, func.count(Organization.id))
        .join(Score, Score.organization_id == Organization.id)
        .where(*score_filter)
        .group_by(Organization.org_type)
    )
    type_result = await db.execute(type_q)
    org_type_breakdown = {row[0]: row[1] for row in type_result.all()}

    # Score distribution (buckets of 1.0)
    score_dist = []
    for low in range(1, 11):
        high = low + 1
        count_q = (
            select(func.count(Score.id))
            .where(
                Score.composite_score >= low,
                Score.composite_score < high,
                *score_filter,
            )
        )
        count = (await db.execute(count_q)).scalar_one()
        score_dist.append({"range": f"{low}-{high}", "count": count})

    # Top 10 prospects
    top_q = (
        select(
            Organization.id.label("org_id"),
            Organization.name.label("org_name"),
            Organization.org_type.label("org_type"),
            Organization.region.label("region"),
            Score.d1_sector_fit,
            Score.d1_confidence,
            Score.d2_relationship,
            Score.d3_halo_value,
            Score.d3_confidence,
            Score.d4_emerging_fit,
            Score.d4_confidence,
            Score.composite_score,
            Score.tier,
            Score.check_size_min,
            Score.check_size_max,
            EnrichmentResult.data_quality,
        )
        .join(Score, Score.organization_id == Organization.id)
        .join(EnrichmentResult, EnrichmentResult.id == Score.enrichment_id)
        .where(*score_filter)
        .order_by(Score.composite_score.desc())
        .limit(10)
    )
    top_result = await db.execute(top_q)
    top_rows = top_result.all()

    top_prospects = []
    for row in top_rows:
        flag_count_q = select(func.count(ValidationFlag.id)).where(
            ValidationFlag.organization_id == row.org_id
        )
        flag_count = (await db.execute(flag_count_q)).scalar_one()

        contact_count_q = select(func.count(Contact.id)).where(
            Contact.organization_id == row.org_id
        )
        contact_count = (await db.execute(contact_count_q)).scalar_one()

        top_prospects.append(
            ProspectSummary(
                org_id=row.org_id,
                org_name=row.org_name,
                org_type=row.org_type,
                region=row.region,
                d1_sector_fit=float(row.d1_sector_fit),
                d1_confidence=row.d1_confidence,
                d2_relationship=float(row.d2_relationship),
                d3_halo_value=float(row.d3_halo_value),
                d3_confidence=row.d3_confidence,
                d4_emerging_fit=float(row.d4_emerging_fit),
                d4_confidence=row.d4_confidence,
                composite_score=float(row.composite_score),
                tier=row.tier,
                data_quality=row.data_quality,
                has_flags=flag_count > 0,
                flag_count=flag_count,
                contact_count=contact_count,
                check_size_min=row.check_size_min,
                check_size_max=row.check_size_max,
            )
        )

    return DashboardSummary(
        total_orgs=total_orgs,
        total_contacts=total_contacts,
        tier_counts=tier_counts,
        avg_composite=round(avg_composite, 2),
        org_type_breakdown=org_type_breakdown,
        score_distribution=score_dist,
        top_prospects=top_prospects,
    )
