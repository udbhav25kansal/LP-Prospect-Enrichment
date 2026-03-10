import logging
from math import ceil

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func, case, desc, asc
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.organization import Organization
from app.models.contact import Contact
from app.models.enrichment import EnrichmentResult
from app.models.score import Score
from app.models.validation_flag import ValidationFlag
from app.schemas.common import (
    ProspectSummary,
    ProspectDetail,
    ProspectListResponse,
    ContactOut,
    EnrichmentOut,
    ScoreOut,
    ValidationFlagOut,
)

logger = logging.getLogger(__name__)
router = APIRouter()

# Sortable columns mapping
SORT_COLUMNS = {
    "org_name": Organization.name,
    "org_type": Organization.org_type,
    "d1_sector_fit": Score.d1_sector_fit,
    "d2_relationship": Score.d2_relationship,
    "d3_halo_value": Score.d3_halo_value,
    "d4_emerging_fit": Score.d4_emerging_fit,
    "composite_score": Score.composite_score,
    "tier": Score.tier,
}


@router.get("", response_model=ProspectListResponse)
async def list_prospects(
    db: AsyncSession = Depends(get_db),
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
    sort: str = Query("composite_score"),
    order: str = Query("desc"),
    tier: str | None = None,
    org_type: str | None = None,
    region: str | None = None,
    search: str | None = None,
    has_flags: bool | None = None,
    run_id: str | None = None,
):
    """List scored prospects with pagination, sorting, and filtering."""

    # Base query: join org + score
    base = (
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
        .join(
            EnrichmentResult,
            EnrichmentResult.id == Score.enrichment_id,
        )
    )

    # Apply filters
    if run_id:
        base = base.where(Score.pipeline_run_id == run_id)
    if tier:
        tiers = [t.strip() for t in tier.split(",")]
        base = base.where(Score.tier.in_(tiers))
    if org_type:
        types = [t.strip() for t in org_type.split(",")]
        base = base.where(Organization.org_type.in_(types))
    if region:
        base = base.where(Organization.region == region)
    if search:
        base = base.where(Organization.name.ilike(f"%{search}%"))

    # Count total
    count_q = select(func.count()).select_from(base.subquery())
    total = (await db.execute(count_q)).scalar_one()

    # Sort
    sort_col = SORT_COLUMNS.get(sort, Score.composite_score)
    if order == "asc":
        base = base.order_by(asc(sort_col))
    else:
        base = base.order_by(desc(sort_col))

    # Paginate
    offset = (page - 1) * page_size
    base = base.offset(offset).limit(page_size)

    result = await db.execute(base)
    rows = result.all()

    # Build response with flag counts and contact info
    items = []
    for row in rows:
        org_id = row.org_id

        # Get flag count
        flag_count_q = select(func.count(ValidationFlag.id)).where(
            ValidationFlag.organization_id == org_id
        )
        if run_id:
            flag_count_q = flag_count_q.where(
                ValidationFlag.pipeline_run_id == run_id
            )
        flag_count = (await db.execute(flag_count_q)).scalar_one()

        # Get contact count and top contact
        contact_q = (
            select(Contact.contact_name, Contact.role, func.count().over().label("cnt"))
            .where(Contact.organization_id == org_id)
            .order_by(Contact.relationship_depth.desc())
            .limit(1)
        )
        contact_result = await db.execute(contact_q)
        contact_row = contact_result.first()

        contact_count_q = select(func.count(Contact.id)).where(
            Contact.organization_id == org_id
        )
        contact_count = (await db.execute(contact_count_q)).scalar_one()

        # Apply has_flags filter
        if has_flags is True and flag_count == 0:
            total -= 1
            continue
        if has_flags is False and flag_count > 0:
            total -= 1
            continue

        items.append(
            ProspectSummary(
                org_id=org_id,
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
                top_contact_name=contact_row.contact_name if contact_row else None,
                top_contact_role=contact_row.role if contact_row else None,
            )
        )

    return ProspectListResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=ceil(total / page_size) if total > 0 else 0,
    )


@router.get("/{org_id}", response_model=ProspectDetail)
async def get_prospect_detail(
    org_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Get full detail for a single organization."""
    # Get org
    result = await db.execute(
        select(Organization).where(Organization.id == org_id)
    )
    org = result.scalar_one_or_none()
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")

    # Get latest score
    result = await db.execute(
        select(Score)
        .where(Score.organization_id == org_id)
        .order_by(Score.created_at.desc())
        .limit(1)
    )
    score = result.scalar_one_or_none()
    if not score:
        raise HTTPException(status_code=404, detail="No scores found for this org")

    # Get enrichment
    result = await db.execute(
        select(EnrichmentResult).where(EnrichmentResult.id == score.enrichment_id)
    )
    enrichment = result.scalar_one_or_none()

    # Get contacts
    result = await db.execute(
        select(Contact)
        .where(Contact.organization_id == org_id)
        .order_by(Contact.relationship_depth.desc())
    )
    contacts = result.scalars().all()

    # Get validation flags
    result = await db.execute(
        select(ValidationFlag).where(ValidationFlag.score_id == score.id)
    )
    flags = result.scalars().all()

    return ProspectDetail(
        org_id=org.id,
        org_name=org.name,
        org_type=org.org_type,
        region=org.region,
        is_calibration_anchor=org.is_calibration_anchor,
        score=ScoreOut(
            id=score.id,
            d1_sector_fit=float(score.d1_sector_fit),
            d1_confidence=score.d1_confidence,
            d1_reasoning=score.d1_reasoning,
            d2_relationship=float(score.d2_relationship),
            d3_halo_value=float(score.d3_halo_value),
            d3_confidence=score.d3_confidence,
            d3_reasoning=score.d3_reasoning,
            d4_emerging_fit=float(score.d4_emerging_fit),
            d4_confidence=score.d4_confidence,
            d4_reasoning=score.d4_reasoning,
            composite_score=float(score.composite_score),
            tier=score.tier,
            check_size_min=score.check_size_min,
            check_size_max=score.check_size_max,
            is_lp_not_gp=score.is_lp_not_gp,
            org_type_assessment=score.org_type_assessment,
            used_default_scores=score.used_default_scores,
        ),
        enrichment=EnrichmentOut(
            aum_raw=enrichment.aum_raw if enrichment else None,
            aum_parsed=enrichment.aum_parsed if enrichment else None,
            investment_mandates=enrichment.investment_mandates if enrichment else None,
            fund_allocations=enrichment.fund_allocations if enrichment else None,
            sustainability_focus=enrichment.sustainability_focus if enrichment else None,
            emerging_manager_evidence=enrichment.emerging_manager_evidence if enrichment else None,
            is_capital_allocator=enrichment.is_capital_allocator if enrichment else None,
            gp_service_provider_signals=enrichment.gp_service_provider_signals if enrichment else None,
            brand_recognition=enrichment.brand_recognition if enrichment else None,
            key_findings_summary=enrichment.key_findings_summary if enrichment else None,
            data_quality=enrichment.data_quality if enrichment else None,
            enrichment_status=enrichment.enrichment_status if enrichment else "unknown",
        ),
        contacts=[
            ContactOut(
                id=c.id,
                contact_name=c.contact_name,
                role=c.role,
                email=c.email,
                contact_status=c.contact_status,
                relationship_depth=c.relationship_depth,
            )
            for c in contacts
        ],
        validation_flags=[
            ValidationFlagOut(
                id=f.id,
                flag_type=f.flag_type,
                severity=f.severity,
                message=f.message,
                suggested_action=f.suggested_action,
                resolved=f.resolved,
            )
            for f in flags
        ],
    )
