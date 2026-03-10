import asyncio
import logging

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.pipeline_run import PipelineRun
from app.schemas.common import PipelineStatus
from app.services import pipeline_service

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/{run_id}/start", response_model=PipelineStatus)
async def start_pipeline(
    run_id: str,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    """Start the enrichment + scoring pipeline for a run."""
    result = await db.execute(
        select(PipelineRun).where(PipelineRun.id == run_id)
    )
    run = result.scalar_one_or_none()
    if not run:
        raise HTTPException(status_code=404, detail="Pipeline run not found")

    if run.status not in ("pending", "failed"):
        raise HTTPException(
            status_code=400,
            detail=f"Pipeline is already {run.status}",
        )

    # Launch pipeline in background
    background_tasks.add_task(pipeline_service.run_pipeline, run_id)

    return PipelineStatus(
        id=run.id,
        status="starting",
        total_orgs=run.total_orgs,
        processed_orgs=run.processed_orgs,
        failed_orgs=run.failed_orgs,
        source_filename=run.source_filename,
        started_at=run.started_at,
        completed_at=run.completed_at,
    )


@router.get("/{run_id}/status", response_model=PipelineStatus)
async def get_pipeline_status(
    run_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Get the current status of a pipeline run."""
    result = await db.execute(
        select(PipelineRun).where(PipelineRun.id == run_id)
    )
    run = result.scalar_one_or_none()
    if not run:
        raise HTTPException(status_code=404, detail="Pipeline run not found")

    return PipelineStatus(
        id=run.id,
        status=run.status,
        total_orgs=run.total_orgs,
        processed_orgs=run.processed_orgs,
        failed_orgs=run.failed_orgs,
        source_filename=run.source_filename,
        started_at=run.started_at,
        completed_at=run.completed_at,
    )


@router.get("", response_model=list[PipelineStatus])
async def list_pipeline_runs(db: AsyncSession = Depends(get_db)):
    """List all pipeline runs."""
    result = await db.execute(
        select(PipelineRun).order_by(PipelineRun.created_at.desc())
    )
    runs = result.scalars().all()
    return [
        PipelineStatus(
            id=r.id,
            status=r.status,
            total_orgs=r.total_orgs,
            processed_orgs=r.processed_orgs,
            failed_orgs=r.failed_orgs,
            source_filename=r.source_filename,
            started_at=r.started_at,
            completed_at=r.completed_at,
        )
        for r in runs
    ]
