export interface ProspectSummary {
  org_id: string;
  org_name: string;
  org_type: string;
  region: string | null;
  d1_sector_fit: number;
  d1_confidence: string | null;
  d2_relationship: number;
  d3_halo_value: number;
  d3_confidence: string | null;
  d4_emerging_fit: number;
  d4_confidence: string | null;
  composite_score: number;
  tier: string;
  data_quality: string | null;
  has_flags: boolean;
  flag_count: number;
  contact_count: number;
  check_size_min: number | null;
  check_size_max: number | null;
  top_contact_name: string | null;
  top_contact_role: string | null;
}

export interface ProspectListResponse {
  items: ProspectSummary[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export interface Contact {
  id: string;
  contact_name: string;
  role: string | null;
  email: string | null;
  contact_status: string | null;
  relationship_depth: number;
}

export interface Source {
  index: number;
  title: string;
  url: string;
}

export interface Enrichment {
  aum_raw: string | null;
  aum_parsed: number | null;
  investment_mandates: string[] | null;
  fund_allocations: string[] | null;
  sustainability_focus: string | null;
  emerging_manager_evidence: string | null;
  is_capital_allocator: boolean | null;
  gp_service_provider_signals: string[] | null;
  brand_recognition: string | null;
  key_findings_summary: string | null;
  data_quality: string | null;
  enrichment_status: string;
  sources: Source[] | null;
  field_citations: Record<string, number[]> | null;
  deep_research_enabled: boolean | null;
}

export interface Score {
  id: string;
  d1_sector_fit: number;
  d1_confidence: string | null;
  d1_reasoning: string;
  d2_relationship: number;
  d3_halo_value: number;
  d3_confidence: string | null;
  d3_reasoning: string;
  d4_emerging_fit: number;
  d4_confidence: string | null;
  d4_reasoning: string;
  composite_score: number;
  tier: string;
  check_size_min: number | null;
  check_size_max: number | null;
  is_lp_not_gp: boolean | null;
  org_type_assessment: string | null;
  used_default_scores: boolean;
}

export interface ValidationFlag {
  id: string;
  flag_type: string;
  severity: string;
  message: string;
  suggested_action: string | null;
  resolved: boolean;
}

export interface ProspectDetail {
  org_id: string;
  org_name: string;
  org_type: string;
  region: string | null;
  is_calibration_anchor: boolean;
  score: Score;
  enrichment: Enrichment;
  contacts: Contact[];
  validation_flags: ValidationFlag[];
}

export interface DashboardSummary {
  total_orgs: number;
  total_contacts: number;
  tier_counts: Record<string, number>;
  avg_composite: number;
  org_type_breakdown: Record<string, number>;
  score_distribution: { range: string; count: number }[];
  top_prospects: ProspectSummary[];
}

export interface ActivityLogEntry {
  timestamp: string;
  org: string;
  step: string;
  message: string;
}

export interface PipelineStatus {
  id: string;
  status: string;
  total_orgs: number;
  processed_orgs: number;
  failed_orgs: number;
  source_filename: string | null;
  started_at: string | null;
  completed_at: string | null;
  activity_log: ActivityLogEntry[];
}

export interface CostSummary {
  run_id: string;
  total_cost_usd: number;
  tavily_cost_usd: number;
  anthropic_cost_usd: number;
  total_api_calls: number;
  avg_cost_per_org: number;
  cost_by_operation: Record<string, number>;
  projected_cost_1000: number;
}

export interface IngestResponse {
  run_id: string;
  total_contacts: number;
  unique_orgs: number;
  skipped_rows: number;
  duplicate_contacts: string[];
}
