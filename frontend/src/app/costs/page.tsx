"use client";

import { useState, useEffect } from "react";
import { listPipelineRuns, getCosts } from "@/lib/api";
import type { PipelineStatus, CostSummary } from "@/lib/types";

export default function CostsPage() {
  const [runs, setRuns] = useState<PipelineStatus[]>([]);
  const [selectedRun, setSelectedRun] = useState<string | null>(null);
  const [costs, setCosts] = useState<CostSummary | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    listPipelineRuns()
      .then((data: any) => {
        setRuns(data);
        if (data.length > 0) {
          setSelectedRun(data[0].id);
        }
      })
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    if (!selectedRun) return;
    getCosts(selectedRun).then((data: any) => setCosts(data));
  }, [selectedRun]);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-emerald-600" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold text-gray-900">Cost Analysis</h1>

      {runs.length === 0 ? (
        <div className="bg-amber-50 border border-amber-200 rounded-lg p-6 text-center">
          <p className="text-amber-800">
            No pipeline runs yet. Import and process prospects first.
          </p>
        </div>
      ) : (
        <>
          {/* Run Selector */}
          <div className="bg-white rounded-lg border border-gray-200 p-4">
            <label className="text-sm text-gray-500 font-medium">
              Pipeline Run
            </label>
            <select
              value={selectedRun || ""}
              onChange={(e) => setSelectedRun(e.target.value)}
              className="ml-3 px-3 py-1.5 border border-gray-300 rounded-md text-sm"
            >
              {runs.map((r) => (
                <option key={r.id} value={r.id}>
                  {r.source_filename || "Unknown"} — {r.status} (
                  {r.processed_orgs} orgs)
                </option>
              ))}
            </select>
          </div>

          {costs && (
            <>
              {/* Cost Summary Cards */}
              <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
                <div className="bg-white rounded-lg border border-gray-200 p-5">
                  <p className="text-sm text-gray-500">Total Cost</p>
                  <p className="text-2xl font-bold text-gray-900">
                    ${costs.total_cost_usd.toFixed(2)}
                  </p>
                </div>
                <div className="bg-white rounded-lg border border-gray-200 p-5">
                  <p className="text-sm text-gray-500">Tavily (Search)</p>
                  <p className="text-2xl font-bold text-blue-600">
                    ${costs.tavily_cost_usd.toFixed(2)}
                  </p>
                </div>
                <div className="bg-white rounded-lg border border-gray-200 p-5">
                  <p className="text-sm text-gray-500">Anthropic (AI)</p>
                  <p className="text-2xl font-bold text-purple-600">
                    ${costs.anthropic_cost_usd.toFixed(2)}
                  </p>
                </div>
                <div className="bg-white rounded-lg border border-gray-200 p-5">
                  <p className="text-sm text-gray-500">Cost per Org</p>
                  <p className="text-2xl font-bold text-gray-900">
                    ${costs.avg_cost_per_org.toFixed(3)}
                  </p>
                </div>
              </div>

              {/* Details */}
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                {/* Cost by Operation */}
                <div className="bg-white rounded-lg border border-gray-200 p-5">
                  <h3 className="text-sm font-semibold text-gray-700 mb-4">
                    Cost by Operation
                  </h3>
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="border-b border-gray-200 text-left text-gray-500">
                        <th className="pb-2 font-medium">Operation</th>
                        <th className="pb-2 font-medium text-right">Cost</th>
                      </tr>
                    </thead>
                    <tbody>
                      {Object.entries(costs.cost_by_operation).map(
                        ([op, cost]) => (
                          <tr key={op} className="border-b border-gray-100">
                            <td className="py-2 capitalize">{op}</td>
                            <td className="py-2 text-right font-mono">
                              ${cost.toFixed(4)}
                            </td>
                          </tr>
                        )
                      )}
                    </tbody>
                  </table>
                </div>

                {/* Projections */}
                <div className="bg-white rounded-lg border border-gray-200 p-5">
                  <h3 className="text-sm font-semibold text-gray-700 mb-4">
                    Cost Projections
                  </h3>
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="border-b border-gray-200 text-left text-gray-500">
                        <th className="pb-2 font-medium">Scale</th>
                        <th className="pb-2 font-medium text-right">
                          Est. Cost
                        </th>
                      </tr>
                    </thead>
                    <tbody>
                      {[100, 500, 1000, 5000].map((n) => (
                        <tr key={n} className="border-b border-gray-100">
                          <td className="py-2">{n.toLocaleString()} orgs</td>
                          <td className="py-2 text-right font-mono">
                            ${(costs.avg_cost_per_org * n).toFixed(2)}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>

              {/* Metadata */}
              <div className="bg-white rounded-lg border border-gray-200 p-5">
                <div className="flex gap-8 text-sm text-gray-500">
                  <span>Total API Calls: {costs.total_api_calls}</span>
                  <span>
                    Projected cost at 1,000 orgs: $
                    {costs.projected_cost_1000.toFixed(2)}
                  </span>
                </div>
              </div>
            </>
          )}
        </>
      )}
    </div>
  );
}
