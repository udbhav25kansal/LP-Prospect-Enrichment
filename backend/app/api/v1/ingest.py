import logging

from fastapi import APIRouter, UploadFile, File, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.schemas.common import IngestResponse
from app.services import ingest_service

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/csv", response_model=IngestResponse)
async def ingest_csv(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
):
    """Upload and ingest a CSV of prospect contacts."""
    content = await file.read()
    file_content = content.decode("utf-8-sig")  # Handle BOM

    result = await ingest_service.ingest_csv(
        db=db,
        file_content=file_content,
        filename=file.filename or "unknown.csv",
    )

    return IngestResponse(**result)
