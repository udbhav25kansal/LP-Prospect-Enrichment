import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.pipeline_run import PipelineRun
from app.schemas.common import CostSummary
from app.services import cost_service

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/{run_id}", response_model=CostSummary)
async def get_costs(
    run_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Get cost breakdown for a pipeline run."""
    result = await db.execute(
        select(PipelineRun).where(PipelineRun.id == run_id)
    )
    run = result.scalar_one_or_none()
    if not run:
        raise HTTPException(status_code=404, detail="Pipeline run not found")

    summary = await cost_service.get_run_cost_summary(db, run_id)
    return CostSummary(**summary)
