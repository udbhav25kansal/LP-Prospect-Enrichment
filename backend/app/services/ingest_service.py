import csv
import io
import logging
import re
import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.organization import Organization
from app.models.contact import Contact
from app.models.pipeline_run import PipelineRun

logger = logging.getLogger(__name__)

# Known aliases for org deduplication
ORG_ALIASES = {
    "pbucc": "pension boards united church of christ",
}

# Suffixes to strip during normalization
STRIP_SUFFIXES = [
    r",?\s*llc$",
    r",?\s*inc\.?$",
    r",?\s*lp$",
    r",?\s*ltd\.?$",
    r",?\s*corp\.?$",
]

# Calibration anchor org names (normalized)
CALIBRATION_ANCHORS = {
    "the rockefeller foundation",
    "pension boards united church of christ",
    "inherent group",
    "meridian capital group",
}


def normalize_org_name(name: str) -> str:
    """Normalize organization name for deduplication."""
    normalized = name.lower().strip()

    # Check alias table first
    if normalized in ORG_ALIASES:
        normalized = ORG_ALIASES[normalized]

    # Strip common suffixes
    for pattern in STRIP_SUFFIXES:
        normalized = re.sub(pattern, "", normalized).strip()

    return normalized


def is_calibration_anchor(name_normalized: str) -> bool:
    """Check if this org is a calibration anchor."""
    return name_normalized in CALIBRATION_ANCHORS


async def ingest_csv(
    db: AsyncSession, file_content: str, filename: str
) -> dict:
    """Parse CSV content, deduplicate orgs, create records."""
    # Create pipeline run
    run = PipelineRun(
        id=str(uuid.uuid4()),
        status="pending",
        source_filename=filename,
        started_at=datetime.now(timezone.utc),
    )
    db.add(run)

    reader = csv.DictReader(io.StringIO(file_content))

    orgs_map: dict[str, dict] = {}  # normalized_name -> org data
    contacts_data: list[dict] = []
    skipped_rows = 0
    duplicate_org_names: list[str] = []

    for row_num, row in enumerate(reader, start=2):
        contact_name = (row.get("Contact Name") or "").strip()

        # Skip empty rows
        if not contact_name:
            skipped_rows += 1
            logger.info(f"Skipping empty row {row_num}")
            continue

        org_name = (row.get("Organization") or "").strip()
        org_type = (row.get("Org Type") or "").strip()
        role = (row.get("Role") or "").strip() or None
        email = (row.get("Email") or "").strip() or None
        region = (row.get("Region") or "").strip() or None
        contact_status = (row.get("Contact Status") or "").strip() or None

        # Parse relationship depth
        rd_raw = (row.get("Relationship Depth") or "").strip()
        try:
            relationship_depth = int(rd_raw)
        except (ValueError, TypeError):
            relationship_depth = 4  # default
            logger.warning(
                f"Row {row_num}: Invalid Relationship Depth '{rd_raw}', defaulting to 4"
            )

        # Normalize org name for dedup
        name_normalized = normalize_org_name(org_name)

        if name_normalized in orgs_map:
            duplicate_org_names.append(org_name)
            # Use the more specific org_type if current is more specific
            existing = orgs_map[name_normalized]
            # For PBUCC case: prefer "Pension" over "Endowment"
            if org_type == "Pension" and existing["org_type"] == "Endowment":
                existing["org_type"] = "Pension"
                existing["name"] = org_name  # use full name
        else:
            orgs_map[name_normalized] = {
                "name": org_name,
                "name_normalized": name_normalized,
                "org_type": org_type,
                "region": region,
                "is_calibration_anchor": is_calibration_anchor(name_normalized),
            }

        contacts_data.append(
            {
                "org_normalized": name_normalized,
                "contact_name": contact_name,
                "role": role,
                "email": email,
                "contact_status": contact_status,
                "relationship_depth": relationship_depth,
            }
        )

    # Create Organization records (upsert)
    org_id_map: dict[str, str] = {}

    for norm_name, org_data in orgs_map.items():
        # Check if org already exists
        result = await db.execute(
            select(Organization).where(Organization.name_normalized == norm_name)
        )
        existing_org = result.scalar_one_or_none()

        if existing_org:
            org_id_map[norm_name] = existing_org.id
        else:
            org_id = str(uuid.uuid4())
            org = Organization(
                id=org_id,
                name=org_data["name"],
                name_normalized=org_data["name_normalized"],
                org_type=org_data["org_type"],
                region=org_data["region"],
                is_calibration_anchor=org_data["is_calibration_anchor"],
            )
            db.add(org)
            org_id_map[norm_name] = org_id

    # Create Contact records
    for contact_data in contacts_data:
        org_id = org_id_map[contact_data["org_normalized"]]
        contact = Contact(
            id=str(uuid.uuid4()),
            organization_id=org_id,
            pipeline_run_id=run.id,
            contact_name=contact_data["contact_name"],
            role=contact_data["role"],
            email=contact_data["email"],
            contact_status=contact_data["contact_status"],
            relationship_depth=contact_data["relationship_depth"],
        )
        db.add(contact)

    run.total_orgs = len(orgs_map)
    await db.commit()

    logger.info(
        f"Ingested {len(contacts_data)} contacts across {len(orgs_map)} orgs "
        f"(skipped {skipped_rows} rows, {len(duplicate_org_names)} duplicate contacts)"
    )

    return {
        "run_id": run.id,
        "total_contacts": len(contacts_data),
        "unique_orgs": len(orgs_map),
        "skipped_rows": skipped_rows,
        "duplicate_contacts": duplicate_org_names,
    }
