import asyncio
import logging
import uuid
from datetime import datetime, timezone

from sqlalchemy import select, func, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.core.database import AsyncSessionLocal
from app.models.organization import Organization
from app.models.contact import Contact
from app.models.enrichment import EnrichmentResult
from app.models.score import Score
from app.models.pipeline_run import PipelineRun
from app.services import enrichment_service, scoring_service, validation_service

logger = logging.getLogger(__name__)
settings = get_settings()


async def get_relationship_depth_for_org(
    db: AsyncSession, org_id: uuid.UUID, run_id: uuid.UUID
) -> int:
    """Get max relationship depth across all contacts for an org in this run."""
    result = await db.execute(
        select(func.max(Contact.relationship_depth)).where(
            Contact.organization_id == org_id,
            Contact.pipeline_run_id == run_id,
        )
    )
    return result.scalar_one_or_none() or 4


async def process_single_org(
    org: Organization,
    run_id: uuid.UUID,
    deep_research: bool = False,
) -> dict:
    """Process a single organization: enrich → score → validate."""
    async with AsyncSessionLocal() as db:
        try:
            # Get relationship depth
            rd = await get_relationship_depth_for_org(db, org.id, run_id)

            # Check if already enriched (for resume capability)
            existing = await db.execute(
                select(EnrichmentResult).where(
                    EnrichmentResult.organization_id == org.id,
                    EnrichmentResult.pipeline_run_id == run_id,
                    EnrichmentResult.enrichment_status == "completed",
                )
            )
            enrichment = existing.scalar_one_or_none()

            if not enrichment:
                # Enrich
                enrichment = await enrichment_service.enrich_organization(
                    db=db,
                    org_id=org.id,
                    org_name=org.name,
                    org_type=org.org_type,
                    region=org.region,
                    pipeline_run_id=run_id,
                    deep_research=deep_research,
                )

            if enrichment.enrichment_status != "completed":
                await db.commit()
                return {"org_name": org.name, "status": "enrichment_failed"}

            # Check if already scored (for resume capability)
            existing_score = await db.execute(
                select(Score).where(
                    Score.organization_id == org.id,
                    Score.pipeline_run_id == run_id,
                )
            )
            if existing_score.scalar_one_or_none():
                logger.info(f"Skipping {org.name}: already scored in this run")
                return {
                    "org_name": org.name,
                    "status": "completed",
                    "composite": 0,
                    "tier": "SKIPPED",
                    "flags": 0,
                }

            # Score
            score = await scoring_service.score_organization(
                db=db,
                org_id=org.id,
                org_name=org.name,
                org_type=org.org_type,
                region=org.region,
                enrichment=enrichment,
                relationship_depth=rd,
                pipeline_run_id=run_id,
            )

            # Validate
            flags = await validation_service.validate_scores(
                db=db,
                org=org,
                enrichment=enrichment,
                score=score,
                pipeline_run_id=run_id,
            )

            await db.commit()

            logger.info(
                f"Processed {org.name}: composite={score.composite_score}, "
                f"tier={score.tier}, flags={len(flags)}"
            )

            return {
                "org_name": org.name,
                "status": "completed",
                "composite": float(score.composite_score),
                "tier": score.tier,
                "flags": len(flags),
            }

        except Exception as e:
            logger.error(f"Failed to process {org.name}: {e}")
            await db.rollback()
            return {"org_name": org.name, "status": "failed", "error": str(e)}


async def run_pipeline(run_id: uuid.UUID) -> None:
    """Run the full enrichment + scoring pipeline for a pipeline run."""
    async with AsyncSessionLocal() as db:
        # Get the run
        result = await db.execute(
            select(PipelineRun).where(PipelineRun.id == run_id)
        )
        run = result.scalar_one_or_none()
        if not run:
            logger.error(f"Pipeline run {run_id} not found")
            return

        # Read deep_research flag from config
        config = run.config_snapshot or {}
        deep_research = config.get("deep_research", False)

        # Update status
        run.status = "running"
        run.started_at = datetime.now(timezone.utc)
        await db.commit()

        # Get all orgs for this run
        result = await db.execute(
            select(Organization)
            .join(Contact, Contact.organization_id == Organization.id)
            .where(Contact.pipeline_run_id == run_id)
            .distinct()
        )
        orgs = list(result.scalars().all())
        run.total_orgs = len(orgs)
        await db.commit()

        logger.info(
            f"Pipeline {run_id}: processing {len(orgs)} organizations"
            f"{' (deep research enabled)' if deep_research else ''}"
        )

    # Process with bounded concurrency — progress updates per-org
    concurrency = settings.enrichment_concurrency
    semaphore = asyncio.Semaphore(concurrency)
    processed = 0
    failed = 0
    _progress_lock = asyncio.Lock()

    async def process_with_semaphore(org):
        nonlocal processed, failed
        async with semaphore:
            result = await process_single_org(org, run_id, deep_research=deep_research)

        # Update counters and persist progress after each org
        async with _progress_lock:
            if isinstance(result, Exception):
                failed += 1
                logger.error(f"Task exception for {org.name}: {result}")
            elif isinstance(result, dict):
                if result.get("status") == "completed":
                    processed += 1
                else:
                    failed += 1
            else:
                failed += 1

            # Persist progress to DB so frontend polling sees live updates
            async with AsyncSessionLocal() as db:
                await db.execute(
                    update(PipelineRun)
                    .where(PipelineRun.id == run_id)
                    .values(processed_orgs=processed, failed_orgs=failed)
                )
                await db.commit()

            logger.info(
                f"Pipeline {run_id}: {processed + failed}/{len(orgs)} done — "
                f"processed={processed}, failed={failed}"
            )

        return result

    # Launch all orgs at once — semaphore controls concurrency
    tasks = [process_with_semaphore(org) for org in orgs]
    await asyncio.gather(*tasks, return_exceptions=True)

    # Finalize
    async with AsyncSessionLocal() as db:
        await db.execute(
            update(PipelineRun)
            .where(PipelineRun.id == run_id)
            .values(
                status="completed",
                completed_at=datetime.now(timezone.utc),
                processed_orgs=processed,
                failed_orgs=failed,
            )
        )
        await db.commit()

    logger.info(
        f"Pipeline {run_id} completed: {processed} processed, {failed} failed"
    )
