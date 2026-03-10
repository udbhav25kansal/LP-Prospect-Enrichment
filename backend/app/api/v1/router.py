from fastapi import APIRouter

from app.api.v1 import ingest, pipeline, prospects, dashboard, costs

v1_router = APIRouter()

v1_router.include_router(ingest.router, prefix="/ingest", tags=["Ingest"])
v1_router.include_router(pipeline.router, prefix="/pipeline", tags=["Pipeline"])
v1_router.include_router(prospects.router, prefix="/prospects", tags=["Prospects"])
v1_router.include_router(dashboard.router, prefix="/dashboard", tags=["Dashboard"])
v1_router.include_router(costs.router, prefix="/costs", tags=["Costs"])
