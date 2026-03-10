from pydantic import BaseModel
from datetime import datetime


class OrmBase(BaseModel):
    model_config = {"from_attributes": True}


class ContactOut(OrmBase):
    id: str
    contact_name: str
    role: str | None
    email: str | None
    contact_status: str | None
    relationship_depth: int


class SourceOut(BaseModel):
    index: int
    title: str
    url: str


class EnrichmentOut(OrmBase):
    aum_raw: str | None
    aum_parsed: int | None
    investment_mandates: list | None
    fund_allocations: list | None
    sustainability_focus: str | None
    emerging_manager_evidence: str | None
    is_capital_allocator: bool | None
    gp_service_provider_signals: list | None
    brand_recognition: str | None
    key_findings_summary: str | None
    data_quality: str | None
    enrichment_status: str
    sources: list[SourceOut] | None = None
    field_citations: dict[str, list[int]] | None = None
    deep_research_enabled: bool | None = False


class ScoreOut(OrmBase):
    id: str
    d1_sector_fit: float
    d1_confidence: str | None
    d1_reasoning: str
    d2_relationship: float
    d3_halo_value: float
    d3_confidence: str | None
    d3_reasoning: str
    d4_emerging_fit: float
    d4_confidence: str | None
    d4_reasoning: str
    composite_score: float
    tier: str
    check_size_min: int | None
    check_size_max: int | None
    is_lp_not_gp: bool | None
    org_type_assessment: str | None
    used_default_scores: bool


class ValidationFlagOut(OrmBase):
    id: str
    flag_type: str
    severity: str
    message: str
    suggested_action: str | None
    resolved: bool


class ProspectSummary(OrmBase):
    org_id: str
    org_name: str
    org_type: str
    region: str | None
    d1_sector_fit: float
    d1_confidence: str | None
    d2_relationship: float
    d3_halo_value: float
    d3_confidence: str | None
    d4_emerging_fit: float
    d4_confidence: str | None
    composite_score: float
    tier: str
    data_quality: str | None
    has_flags: bool
    flag_count: int
    contact_count: int
    check_size_min: int | None = None
    check_size_max: int | None = None
    top_contact_name: str | None = None
    top_contact_role: str | None = None


class ProspectDetail(OrmBase):
    org_id: str
    org_name: str
    org_type: str
    region: str | None
    is_calibration_anchor: bool
    score: ScoreOut
    enrichment: EnrichmentOut
    contacts: list[ContactOut]
    validation_flags: list[ValidationFlagOut]


class ProspectListResponse(BaseModel):
    items: list[ProspectSummary]
    total: int
    page: int
    page_size: int
    total_pages: int


class DashboardSummary(BaseModel):
    total_orgs: int
    total_contacts: int
    tier_counts: dict[str, int]
    avg_composite: float
    org_type_breakdown: dict[str, int]
    score_distribution: list[dict]
    top_prospects: list[ProspectSummary]


class ActivityLogEntry(BaseModel):
    timestamp: str
    org: str
    step: str
    message: str


class PipelineStatus(OrmBase):
    id: str
    status: str
    total_orgs: int
    processed_orgs: int
    failed_orgs: int
    source_filename: str | None
    started_at: datetime | None
    completed_at: datetime | None
    activity_log: list[ActivityLogEntry] = []


class CostSummary(BaseModel):
    run_id: str
    total_cost_usd: float
    tavily_cost_usd: float
    anthropic_cost_usd: float
    gemini_cost_usd: float = 0.0
    total_api_calls: int
    avg_cost_per_org: float
    cost_by_operation: dict[str, float]
    projected_cost_1000: float


class IngestResponse(BaseModel):
    run_id: str
    total_contacts: int
    unique_orgs: int
    skipped_rows: int
    duplicate_contacts: list[str]
