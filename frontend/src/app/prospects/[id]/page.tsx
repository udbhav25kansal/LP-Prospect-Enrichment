"use client";

import useSWR from "swr";
import Link from "next/link";
import { useParams } from "next/navigation";
import { fetcher } from "@/lib/api";
import { DIMENSION_LABELS, SEVERITY_CONFIG } from "@/lib/constants";
import { formatCheckSize } from "@/lib/utils";
import TierBadge from "@/components/shared/TierBadge";
import ScoreBar from "@/components/shared/ScoreBar";
import type { ProspectDetail, Enrichment, Source } from "@/lib/types";
import { clsx } from "clsx";

/** Small superscript citation badge that links to the source URL */
function CitationBadge({ source }: { source: Source }) {
  return (
    <a
      href={source.url}
      target="_blank"
      rel="noopener noreferrer"
      title={`${source.title}\n${source.url}`}
      className="inline-flex items-center justify-center w-4 h-4 ml-0.5 text-[9px] font-bold text-emerald-700 bg-emerald-100 rounded hover:bg-emerald-200 transition-colors cursor-pointer align-super no-underline"
    >
      {source.index}
    </a>
  );
}

/** Render citation badges for a field */
function Citations({
  fieldName,
  enrichment,
}: {
  fieldName: string;
  enrichment: Enrichment;
}) {
  const indices = enrichment.field_citations?.[fieldName];
  if (!indices || indices.length === 0 || !enrichment.sources) return null;

  const sourceMap = new Map(enrichment.sources.map((s) => [s.index, s]));

  return (
    <span className="inline-flex gap-0.5 ml-1">
      {indices.map((idx) => {
        const source = sourceMap.get(idx);
        return source ? <CitationBadge key={idx} source={source} /> : null;
      })}
    </span>
  );
}

export default function ProspectDetailPage() {
  const { id } = useParams<{ id: string }>();
  const { data, error, isLoading } = useSWR<ProspectDetail>(
    `/prospects/${id}`,
    fetcher
  );

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-emerald-600" />
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="p-6 text-center text-gray-500">Prospect not found.</div>
    );
  }

  const { score, enrichment, contacts, validation_flags } = data;

  return (
    <div className="space-y-6">
      {/* Breadcrumb + Header */}
      <div>
        <Link
          href="/prospects"
          className="text-sm text-gray-500 hover:text-gray-700"
        >
          &larr; Back to Prospects
        </Link>
        <div className="flex items-center gap-4 mt-2">
          <h1 className="text-2xl font-bold text-gray-900">{data.org_name}</h1>
          <TierBadge tier={score.tier} />
          {data.is_calibration_anchor && (
            <span className="text-xs bg-purple-100 text-purple-700 px-2 py-0.5 rounded-full font-medium">
              Calibration Anchor
            </span>
          )}
          {enrichment.deep_research_enabled && (
            <span className="text-xs bg-indigo-100 text-indigo-700 px-2 py-0.5 rounded-full font-medium">
              Deep Research
            </span>
          )}
        </div>
        <div className="flex gap-4 mt-1 text-sm text-gray-500">
          <span>{data.org_type}</span>
          {data.region && <span>{data.region}</span>}
          {enrichment.aum_raw && (
            <span>
              AUM: {enrichment.aum_raw}
              <Citations fieldName="aum" enrichment={enrichment} />
            </span>
          )}
        </div>
      </div>

      {/* Composite Score Hero */}
      <div className="bg-white rounded-lg border border-gray-200 p-6">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold text-gray-800">
            Composite Score
          </h2>
          <span className="text-4xl font-bold text-gray-900">
            {score.composite_score.toFixed(2)}
          </span>
        </div>

        <div className="space-y-3">
          <ScoreBar
            score={score.d1_sector_fit}
            label={DIMENSION_LABELS.d1.name}
            weight={DIMENSION_LABELS.d1.weight}
            confidence={score.d1_confidence}
          />
          <ScoreBar
            score={score.d2_relationship}
            label={DIMENSION_LABELS.d2.name}
            weight={DIMENSION_LABELS.d2.weight}
          />
          <ScoreBar
            score={score.d3_halo_value}
            label={DIMENSION_LABELS.d3.name}
            weight={DIMENSION_LABELS.d3.weight}
            confidence={score.d3_confidence}
          />
          <ScoreBar
            score={score.d4_emerging_fit}
            label={DIMENSION_LABELS.d4.name}
            weight={DIMENSION_LABELS.d4.weight}
            confidence={score.d4_confidence}
          />
        </div>

        {score.check_size_min && score.check_size_max && (
          <div className="mt-4 pt-4 border-t border-gray-200">
            <p className="text-sm text-gray-500">Estimated Check Size</p>
            <p className="text-lg font-semibold">
              {formatCheckSize(score.check_size_min, score.check_size_max)}
            </p>
          </div>
        )}
      </div>

      {/* Dimension Reasoning */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        {[
          {
            dim: "D1: Sector & Mandate Fit",
            score: score.d1_sector_fit,
            reasoning: score.d1_reasoning,
            confidence: score.d1_confidence,
          },
          {
            dim: "D3: Halo & Strategic Value",
            score: score.d3_halo_value,
            reasoning: score.d3_reasoning,
            confidence: score.d3_confidence,
          },
          {
            dim: "D4: Emerging Manager Fit",
            score: score.d4_emerging_fit,
            reasoning: score.d4_reasoning,
            confidence: score.d4_confidence,
          },
        ].map((d) => (
          <div
            key={d.dim}
            className="bg-white rounded-lg border border-gray-200 p-5"
          >
            <div className="flex items-center justify-between mb-2">
              <h3 className="text-sm font-semibold text-gray-700">{d.dim}</h3>
              <span className="text-2xl font-bold">{d.score.toFixed(1)}</span>
            </div>
            {d.confidence && (
              <p
                className={clsx(
                  "text-xs mb-2",
                  d.confidence === "high" && "text-green-600",
                  d.confidence === "medium" && "text-amber-600",
                  d.confidence === "low" && "text-red-500"
                )}
              >
                Confidence: {d.confidence}
              </p>
            )}
            <p className="text-sm text-gray-600">{d.reasoning}</p>
          </div>
        ))}
      </div>

      {/* Enrichment Evidence */}
      <div className="bg-white rounded-lg border border-gray-200 p-5">
        <h2 className="text-lg font-semibold text-gray-800 mb-4">
          Enrichment Evidence
        </h2>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <p className="text-xs text-gray-500 font-medium">
              Investment Mandates
              <Citations
                fieldName="investment_mandates"
                enrichment={enrichment}
              />
            </p>
            <div className="flex flex-wrap gap-1 mt-1">
              {enrichment.investment_mandates?.length ? (
                enrichment.investment_mandates.map((m, i) => (
                  <span
                    key={i}
                    className="px-2 py-0.5 bg-blue-50 text-blue-700 text-xs rounded-full"
                  >
                    {m}
                  </span>
                ))
              ) : (
                <span className="text-sm text-gray-400">None identified</span>
              )}
            </div>
          </div>

          <div>
            <p className="text-xs text-gray-500 font-medium">
              Fund Allocations
              <Citations
                fieldName="fund_allocations"
                enrichment={enrichment}
              />
            </p>
            <div className="flex flex-wrap gap-1 mt-1">
              {enrichment.fund_allocations?.length ? (
                enrichment.fund_allocations.map((a, i) => (
                  <span
                    key={i}
                    className="px-2 py-0.5 bg-green-50 text-green-700 text-xs rounded-full"
                  >
                    {a}
                  </span>
                ))
              ) : (
                <span className="text-sm text-gray-400">None identified</span>
              )}
            </div>
          </div>

          <div>
            <p className="text-xs text-gray-500 font-medium">
              Sustainability Focus
              <Citations
                fieldName="sustainability_focus"
                enrichment={enrichment}
              />
            </p>
            <p className="text-sm text-gray-700 mt-1">
              {enrichment.sustainability_focus || "No evidence found"}
            </p>
          </div>

          <div>
            <p className="text-xs text-gray-500 font-medium">
              Emerging Manager Evidence
              <Citations
                fieldName="emerging_manager_evidence"
                enrichment={enrichment}
              />
            </p>
            <p className="text-sm text-gray-700 mt-1">
              {enrichment.emerging_manager_evidence || "No evidence found"}
            </p>
          </div>

          <div className="md:col-span-2">
            <p className="text-xs text-gray-500 font-medium">
              Key Findings
              <Citations
                fieldName="key_findings_summary"
                enrichment={enrichment}
              />
            </p>
            <p className="text-sm text-gray-700 mt-1">
              {enrichment.key_findings_summary || "N/A"}
            </p>
          </div>

          {enrichment.gp_service_provider_signals &&
            enrichment.gp_service_provider_signals.length > 0 && (
              <div className="md:col-span-2">
                <p className="text-xs text-red-500 font-medium">
                  GP/Service Provider Signals
                  <Citations
                    fieldName="gp_service_provider_signals"
                    enrichment={enrichment}
                  />
                </p>
                <ul className="text-sm text-red-700 mt-1 list-disc list-inside">
                  {enrichment.gp_service_provider_signals.map((s, i) => (
                    <li key={i}>{s}</li>
                  ))}
                </ul>
              </div>
            )}

          <div>
            <p className="text-xs text-gray-500 font-medium">
              LP Assessment
              <Citations
                fieldName="is_capital_allocator"
                enrichment={enrichment}
              />
            </p>
            <p className="text-sm text-gray-700 mt-1">
              {score.is_lp_not_gp === true
                ? "Confirmed LP"
                : score.is_lp_not_gp === false
                  ? "Not an LP (GP/Service Provider)"
                  : "Unknown"}
            </p>
          </div>

          <div>
            <p className="text-xs text-gray-500 font-medium">
              AI Org Type Assessment
            </p>
            <p className="text-sm text-gray-700 mt-1">
              {score.org_type_assessment || "N/A"}
            </p>
          </div>
        </div>

        {/* Sources */}
        {enrichment.sources && enrichment.sources.length > 0 && (
          <div className="mt-6 pt-4 border-t border-gray-200">
            <h3 className="text-sm font-semibold text-gray-700 mb-2">
              Sources ({enrichment.sources.length})
            </h3>
            <div className="space-y-1">
              {enrichment.sources.map((s) => (
                <div key={s.index} className="flex items-start gap-2 text-xs">
                  <span className="inline-flex items-center justify-center w-5 h-5 text-[10px] font-bold text-emerald-700 bg-emerald-100 rounded flex-shrink-0 mt-0.5">
                    {s.index}
                  </span>
                  <div className="min-w-0">
                    <a
                      href={s.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-emerald-600 hover:underline font-medium truncate block"
                    >
                      {s.title || s.url}
                    </a>
                    <span className="text-gray-400 truncate block">
                      {s.url}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* Validation Flags */}
      {validation_flags.length > 0 && (
        <div className="bg-white rounded-lg border border-gray-200 p-5">
          <h2 className="text-lg font-semibold text-gray-800 mb-4">
            Validation Flags ({validation_flags.length})
          </h2>
          <div className="space-y-3">
            {validation_flags.map((f) => {
              const sev = SEVERITY_CONFIG[f.severity] || SEVERITY_CONFIG.info;
              return (
                <div
                  key={f.id}
                  className={clsx(
                    "p-3 rounded-lg border",
                    sev.bg,
                    `border-${f.severity === "error" ? "red" : f.severity === "warning" ? "amber" : "blue"}-200`
                  )}
                >
                  <div className="flex items-center gap-2">
                    <span
                      className={clsx(
                        "text-xs font-bold px-1.5 py-0.5 rounded",
                        sev.text
                      )}
                    >
                      {f.severity.toUpperCase()}
                    </span>
                    <span className="text-xs font-mono text-gray-500">
                      {f.flag_type}
                    </span>
                  </div>
                  <p className={clsx("text-sm mt-1", sev.text)}>{f.message}</p>
                  {f.suggested_action && (
                    <p className="text-xs text-gray-600 mt-1">
                      Suggestion: {f.suggested_action}
                    </p>
                  )}
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Contacts */}
      <div className="bg-white rounded-lg border border-gray-200 p-5">
        <h2 className="text-lg font-semibold text-gray-800 mb-4">
          Contacts ({contacts.length})
        </h2>
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-gray-200 text-left text-gray-500">
              <th className="pb-2 font-medium">Name</th>
              <th className="pb-2 font-medium">Role</th>
              <th className="pb-2 font-medium">Email</th>
              <th className="pb-2 font-medium">Status</th>
              <th className="pb-2 font-medium text-center">Rel. Depth</th>
            </tr>
          </thead>
          <tbody>
            {contacts.map((c) => (
              <tr key={c.id} className="border-b border-gray-100">
                <td className="py-2 font-medium text-gray-900">
                  {c.contact_name}
                </td>
                <td className="py-2 text-gray-500">{c.role || "-"}</td>
                <td className="py-2 text-gray-500">
                  {c.email ? (
                    <a
                      href={`mailto:${c.email}`}
                      className="text-emerald-600 hover:underline"
                    >
                      {c.email}
                    </a>
                  ) : (
                    "-"
                  )}
                </td>
                <td className="py-2 text-gray-500">
                  {c.contact_status || "-"}
                </td>
                <td className="py-2 text-center font-mono">
                  {c.relationship_depth}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
