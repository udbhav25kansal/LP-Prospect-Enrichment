import logging
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.organization import Organization
from app.models.enrichment import EnrichmentResult
from app.models.score import Score
from app.models.validation_flag import ValidationFlag

logger = logging.getLogger(__name__)

# Calibration anchors: normalized name -> expected scores
CALIBRATION_ANCHORS = {
    "the rockefeller foundation": {"d1": 9, "d3": 9, "d4": 8},
    "pension boards united church of christ": {"d1": 8, "d3": 6, "d4": 8},
    "inherent group": {"d1": 8, "d3": 3, "d4": 5},
    "meridian capital group": {"d1": 1, "d3": 3, "d4": 1},
}

INSTITUTIONAL_TYPES = {"Foundation", "Endowment", "Pension"}


def _create_flag(
    org_id: uuid.UUID,
    score_id: uuid.UUID,
    run_id: uuid.UUID,
    flag_type: str,
    severity: str,
    message: str,
    suggested_action: str | None = None,
) -> ValidationFlag:
    return ValidationFlag(
        id=str(uuid.uuid4()),
        organization_id=org_id,
        score_id=score_id,
        pipeline_run_id=run_id,
        flag_type=flag_type,
        severity=severity,
        message=message,
        suggested_action=suggested_action,
    )


async def validate_scores(
    db: AsyncSession,
    org: Organization,
    enrichment: EnrichmentResult,
    score: Score,
    pipeline_run_id: uuid.UUID,
) -> list[ValidationFlag]:
    """Run all validators on a scored organization. Returns created flags."""
    flags = []

    # 1. GP_HIGH_SCORE: non-LP scoring high on sector fit
    if enrichment.is_capital_allocator is False and float(score.d1_sector_fit) >= 6:
        gp_signals = enrichment.gp_service_provider_signals or []
        flags.append(
            _create_flag(
                org.id,
                score.id,
                pipeline_run_id,
                "GP_HIGH_SCORE",
                "error",
                f"{org.name} appears to be a GP/service provider but scored "
                f"D1={score.d1_sector_fit}. GP signals: {', '.join(gp_signals)}",
                "Review enrichment data. Consider overriding D1 to 1-2.",
            )
        )

    # 2. LP_LOW_SCORE: institutional type scoring very low
    if org.org_type in INSTITUTIONAL_TYPES and float(score.d1_sector_fit) <= 3:
        flags.append(
            _create_flag(
                org.id,
                score.id,
                pipeline_run_id,
                "LP_LOW_SCORE",
                "warning",
                f"{org.name} is a {org.org_type} but scored D1={score.d1_sector_fit}. "
                f"Institutional LPs almost always allocate externally.",
                "Check if enrichment data was sparse. May need manual research.",
            )
        )

    # 3. ORG_TYPE_MISMATCH: CRM vs enrichment type mismatch
    if score.org_type_assessment:
        assessed = score.org_type_assessment.strip().lower()
        csv_type = org.org_type.strip().lower()
        if assessed != csv_type and assessed not in csv_type and csv_type not in assessed:
            flags.append(
                _create_flag(
                    org.id,
                    score.id,
                    pipeline_run_id,
                    "ORG_TYPE_MISMATCH",
                    "warning",
                    f'CRM lists {org.name} as "{org.org_type}" but enrichment '
                    f'suggests "{score.org_type_assessment}".',
                    "Verify org type in CRM. May affect scoring accuracy.",
                )
            )

    # 4. CALIBRATION_DRIFT: check anchors
    name_norm = org.name_normalized
    if name_norm in CALIBRATION_ANCHORS:
        expected = CALIBRATION_ANCHORS[name_norm]
        dimension_map = {
            "d1": float(score.d1_sector_fit),
            "d3": float(score.d3_halo_value),
            "d4": float(score.d4_emerging_fit),
        }
        for dim, expected_val in expected.items():
            actual = dimension_map[dim]
            if abs(actual - expected_val) > 2:
                dim_labels = {"d1": "Sector Fit", "d3": "Halo Value", "d4": "Emerging Fit"}
                flags.append(
                    _create_flag(
                        org.id,
                        score.id,
                        pipeline_run_id,
                        "CALIBRATION_DRIFT",
                        "error",
                        f"{org.name} {dim_labels[dim]} expected ~{expected_val}, "
                        f"got {actual}. Drift={actual - expected_val:+.1f}.",
                        "Scoring prompt may need recalibration.",
                    )
                )

    # 5. LOW_DATA_QUALITY
    if enrichment.data_quality == "low":
        flags.append(
            _create_flag(
                org.id,
                score.id,
                pipeline_run_id,
                "LOW_DATA_QUALITY",
                "info",
                f"Limited public information found for {org.name}. Scores may be unreliable.",
                "Consider manual research for this prospect.",
            )
        )

    # 6. DEFAULT_SCORES_USED
    if score.used_default_scores:
        flags.append(
            _create_flag(
                org.id,
                score.id,
                pipeline_run_id,
                "DEFAULT_SCORES_USED",
                "info",
                f"One or more dimensions used default scores for {org.name} "
                f"due to insufficient enrichment data.",
                "Enrichment may have failed or returned no results. Verify manually.",
            )
        )

    # Persist flags
    for flag in flags:
        db.add(flag)

    if flags:
        logger.info(
            f"Validation for {org.name}: {len(flags)} flag(s) — "
            f"{[f.flag_type for f in flags]}"
        )

    return flags
