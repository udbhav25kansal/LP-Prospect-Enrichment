import logging
import uuid

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.api_cost_log import APICostLog

logger = logging.getLogger(__name__)


async def get_run_cost_summary(db: AsyncSession, run_id: uuid.UUID) -> dict:
    """Get cost summary for a pipeline run."""

    # Total cost
    result = await db.execute(
        select(func.sum(APICostLog.estimated_cost_usd)).where(
            APICostLog.pipeline_run_id == run_id
        )
    )
    total_cost = float(result.scalar_one_or_none() or 0)

    # Cost by provider
    result = await db.execute(
        select(APICostLog.provider, func.sum(APICostLog.estimated_cost_usd))
        .where(APICostLog.pipeline_run_id == run_id)
        .group_by(APICostLog.provider)
    )
    provider_costs = {row[0]: float(row[1]) for row in result.all()}

    # Cost by operation
    result = await db.execute(
        select(APICostLog.operation, func.sum(APICostLog.estimated_cost_usd))
        .where(APICostLog.pipeline_run_id == run_id)
        .group_by(APICostLog.operation)
    )
    operation_costs = {row[0]: float(row[1]) for row in result.all()}

    # Total API calls
    result = await db.execute(
        select(func.count(APICostLog.id)).where(
            APICostLog.pipeline_run_id == run_id
        )
    )
    total_calls = result.scalar_one_or_none() or 0

    # Unique orgs processed
    result = await db.execute(
        select(func.count(func.distinct(APICostLog.organization_id))).where(
            APICostLog.pipeline_run_id == run_id,
            APICostLog.organization_id.is_not(None),
        )
    )
    unique_orgs = result.scalar_one_or_none() or 1

    avg_cost_per_org = total_cost / max(unique_orgs, 1)

    return {
        "run_id": run_id,
        "total_cost_usd": round(total_cost, 4),
        "tavily_cost_usd": round(provider_costs.get("tavily", 0), 4),
        "anthropic_cost_usd": round(provider_costs.get("anthropic", 0), 4),
        "total_api_calls": total_calls,
        "avg_cost_per_org": round(avg_cost_per_org, 4),
        "cost_by_operation": {k: round(v, 4) for k, v in operation_costs.items()},
        "projected_cost_1000": round(avg_cost_per_org * 1000, 2),
    }
