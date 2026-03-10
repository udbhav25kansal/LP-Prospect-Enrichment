"""Initial schema

Revision ID: 001
Revises:
Create Date: 2024-01-01 00:00:00.000000
"""

from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # pipeline_runs
    op.create_table(
        "pipeline_runs",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("started_at", sa.DateTime(timezone=True)),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("total_orgs", sa.Integer, nullable=False, server_default="0"),
        sa.Column("processed_orgs", sa.Integer, nullable=False, server_default="0"),
        sa.Column("failed_orgs", sa.Integer, nullable=False, server_default="0"),
        sa.Column("source_filename", sa.String(255)),
        sa.Column("config_snapshot", JSONB),
        sa.Column("error_message", sa.Text),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )

    # organizations
    op.create_table(
        "organizations",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(500), nullable=False),
        sa.Column("name_normalized", sa.String(500), nullable=False, unique=True),
        sa.Column("org_type", sa.String(100), nullable=False),
        sa.Column("region", sa.String(100)),
        sa.Column(
            "is_calibration_anchor",
            sa.Boolean,
            nullable=False,
            server_default="false",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index("idx_org_name_norm", "organizations", ["name_normalized"])
    op.create_index("idx_org_type", "organizations", ["org_type"])

    # contacts
    op.create_table(
        "contacts",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "organization_id",
            UUID(as_uuid=True),
            sa.ForeignKey("organizations.id"),
            nullable=False,
        ),
        sa.Column(
            "pipeline_run_id", UUID(as_uuid=True), sa.ForeignKey("pipeline_runs.id")
        ),
        sa.Column("contact_name", sa.String(500), nullable=False),
        sa.Column("role", sa.String(500)),
        sa.Column("email", sa.String(500)),
        sa.Column("contact_status", sa.String(50)),
        sa.Column("relationship_depth", sa.Integer, nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index("idx_contact_org", "contacts", ["organization_id"])

    # enrichment_results
    op.create_table(
        "enrichment_results",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "organization_id",
            UUID(as_uuid=True),
            sa.ForeignKey("organizations.id"),
            nullable=False,
        ),
        sa.Column(
            "pipeline_run_id",
            UUID(as_uuid=True),
            sa.ForeignKey("pipeline_runs.id"),
            nullable=False,
        ),
        sa.Column("aum_raw", sa.String(200)),
        sa.Column("aum_parsed", sa.BigInteger),
        sa.Column("investment_mandates", JSONB),
        sa.Column("fund_allocations", JSONB),
        sa.Column("sustainability_focus", sa.Text),
        sa.Column("emerging_manager_evidence", sa.Text),
        sa.Column("is_capital_allocator", sa.Boolean),
        sa.Column("gp_service_provider_signals", JSONB),
        sa.Column("brand_recognition", sa.String(20)),
        sa.Column("key_findings_summary", sa.Text),
        sa.Column("tavily_raw_results", JSONB),
        sa.Column("claude_raw_response", sa.Text),
        sa.Column("search_queries_used", JSONB),
        sa.Column(
            "enrichment_status",
            sa.String(20),
            nullable=False,
            server_default="pending",
        ),
        sa.Column("data_quality", sa.String(10)),
        sa.Column("error_message", sa.Text),
        sa.Column("enriched_at", sa.DateTime(timezone=True)),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index("idx_enrich_org", "enrichment_results", ["organization_id"])
    op.create_index("idx_enrich_run", "enrichment_results", ["pipeline_run_id"])

    # scores
    op.create_table(
        "scores",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "organization_id",
            UUID(as_uuid=True),
            sa.ForeignKey("organizations.id"),
            nullable=False,
        ),
        sa.Column(
            "pipeline_run_id",
            UUID(as_uuid=True),
            sa.ForeignKey("pipeline_runs.id"),
            nullable=False,
        ),
        sa.Column(
            "enrichment_id",
            UUID(as_uuid=True),
            sa.ForeignKey("enrichment_results.id"),
            nullable=False,
        ),
        sa.Column("d1_sector_fit", sa.Numeric(3, 1), nullable=False),
        sa.Column("d1_confidence", sa.String(10)),
        sa.Column("d1_reasoning", sa.Text, nullable=False),
        sa.Column("d2_relationship", sa.Numeric(3, 1), nullable=False),
        sa.Column("d3_halo_value", sa.Numeric(3, 1), nullable=False),
        sa.Column("d3_confidence", sa.String(10)),
        sa.Column("d3_reasoning", sa.Text, nullable=False),
        sa.Column("d4_emerging_fit", sa.Numeric(3, 1), nullable=False),
        sa.Column("d4_confidence", sa.String(10)),
        sa.Column("d4_reasoning", sa.Text, nullable=False),
        sa.Column("composite_score", sa.Numeric(4, 2), nullable=False),
        sa.Column("tier", sa.String(20), nullable=False),
        sa.Column("check_size_min", sa.BigInteger),
        sa.Column("check_size_max", sa.BigInteger),
        sa.Column("is_lp_not_gp", sa.Boolean),
        sa.Column("org_type_assessment", sa.String(100)),
        sa.Column(
            "used_default_scores",
            sa.Boolean,
            nullable=False,
            server_default="false",
        ),
        sa.Column("scored_at", sa.DateTime(timezone=True)),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index("idx_score_org", "scores", ["organization_id"])
    op.create_index("idx_score_run", "scores", ["pipeline_run_id"])
    op.create_index("idx_score_tier", "scores", ["tier"])
    op.create_index(
        "idx_score_composite", "scores", [sa.text("composite_score DESC")]
    )

    # validation_flags
    op.create_table(
        "validation_flags",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "organization_id",
            UUID(as_uuid=True),
            sa.ForeignKey("organizations.id"),
            nullable=False,
        ),
        sa.Column(
            "score_id",
            UUID(as_uuid=True),
            sa.ForeignKey("scores.id"),
            nullable=False,
        ),
        sa.Column(
            "pipeline_run_id",
            UUID(as_uuid=True),
            sa.ForeignKey("pipeline_runs.id"),
            nullable=False,
        ),
        sa.Column("flag_type", sa.String(50), nullable=False),
        sa.Column("severity", sa.String(10), nullable=False),
        sa.Column("message", sa.Text, nullable=False),
        sa.Column("suggested_action", sa.Text),
        sa.Column("resolved", sa.Boolean, nullable=False, server_default="false"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index("idx_vf_org", "validation_flags", ["organization_id"])
    op.create_index("idx_vf_run", "validation_flags", ["pipeline_run_id"])

    # api_cost_logs
    op.create_table(
        "api_cost_logs",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "pipeline_run_id",
            UUID(as_uuid=True),
            sa.ForeignKey("pipeline_runs.id"),
            nullable=False,
        ),
        sa.Column(
            "organization_id", UUID(as_uuid=True), sa.ForeignKey("organizations.id")
        ),
        sa.Column("provider", sa.String(20), nullable=False),
        sa.Column("operation", sa.String(50), nullable=False),
        sa.Column("input_tokens", sa.Integer),
        sa.Column("output_tokens", sa.Integer),
        sa.Column("search_credits", sa.Integer),
        sa.Column("estimated_cost_usd", sa.Numeric(10, 6), nullable=False),
        sa.Column("latency_ms", sa.Integer),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index("idx_cost_run", "api_cost_logs", ["pipeline_run_id"])


def downgrade() -> None:
    op.drop_table("api_cost_logs")
    op.drop_table("validation_flags")
    op.drop_table("scores")
    op.drop_table("enrichment_results")
    op.drop_table("contacts")
    op.drop_table("organizations")
    op.drop_table("pipeline_runs")
