"use client";

import { useEffect, useState } from "react";
import useSWR from "swr";
import { fetcher } from "@/lib/api";
import { TIER_CONFIG, TIER_COLORS } from "@/lib/constants";
import TierBadge from "@/components/shared/TierBadge";
import type { DashboardSummary } from "@/lib/types";
import {
  PieChart,
  Pie,
  Cell,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from "recharts";

export default function DashboardPage() {
  const { data, error, isLoading } = useSWR<DashboardSummary>(
    "/dashboard/summary",
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
      <div className="bg-amber-50 border border-amber-200 rounded-lg p-6 text-center">
        <p className="text-amber-800 font-medium">No scored data yet</p>
        <p className="text-amber-600 text-sm mt-1">
          Import a CSV and run the pipeline to see results here.
        </p>
      </div>
    );
  }

  const tierData = Object.entries(data.tier_counts).map(([tier, count]) => ({
    name: TIER_CONFIG[tier]?.label || tier,
    value: count,
    color: TIER_COLORS[tier] || "#6b7280",
  }));

  const orgTypeData = Object.entries(data.org_type_breakdown).map(
    ([type, count]) => ({
      name: type,
      count,
    })
  );

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold text-gray-900">Pipeline Dashboard</h1>

      {/* Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {Object.entries(data.tier_counts).map(([tier, count]) => {
          const config = TIER_CONFIG[tier];
          return (
            <div
              key={tier}
              className="bg-white rounded-lg border border-gray-200 p-5"
            >
              <div className="flex items-center justify-between">
                <p className="text-sm text-gray-500">{config?.label || tier}</p>
                <TierBadge tier={tier} />
              </div>
              <p className="text-3xl font-bold mt-2">{count}</p>
              <p className="text-xs text-gray-400 mt-1">organizations</p>
            </div>
          );
        })}
      </div>

      {/* Stats Row */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="bg-white rounded-lg border border-gray-200 p-5">
          <p className="text-sm text-gray-500">Total Organizations</p>
          <p className="text-2xl font-bold mt-1">{data.total_orgs}</p>
        </div>
        <div className="bg-white rounded-lg border border-gray-200 p-5">
          <p className="text-sm text-gray-500">Total Contacts</p>
          <p className="text-2xl font-bold mt-1">{data.total_contacts}</p>
        </div>
        <div className="bg-white rounded-lg border border-gray-200 p-5">
          <p className="text-sm text-gray-500">Avg Composite Score</p>
          <p className="text-2xl font-bold mt-1">{data.avg_composite}</p>
        </div>
      </div>

      {/* Charts Row */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Tier Distribution */}
        <div className="bg-white rounded-lg border border-gray-200 p-5">
          <h3 className="text-sm font-semibold text-gray-700 mb-4">
            Tier Distribution
          </h3>
          <ResponsiveContainer width="100%" height={250}>
            <PieChart>
              <Pie
                data={tierData}
                dataKey="value"
                nameKey="name"
                cx="50%"
                cy="50%"
                outerRadius={90}
                label={({ name, value }) => `${name}: ${value}`}
              >
                {tierData.map((entry, i) => (
                  <Cell key={i} fill={entry.color} />
                ))}
              </Pie>
              <Tooltip />
            </PieChart>
          </ResponsiveContainer>
        </div>

        {/* Org Type Breakdown */}
        <div className="bg-white rounded-lg border border-gray-200 p-5">
          <h3 className="text-sm font-semibold text-gray-700 mb-4">
            By Organization Type
          </h3>
          <ResponsiveContainer width="100%" height={250}>
            <BarChart data={orgTypeData} layout="vertical">
              <XAxis type="number" />
              <YAxis
                type="category"
                dataKey="name"
                width={140}
                tick={{ fontSize: 11 }}
              />
              <Tooltip />
              <Bar dataKey="count" fill="#059669" radius={[0, 4, 4, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Top 10 Prospects */}
      <div className="bg-white rounded-lg border border-gray-200 p-5">
        <h3 className="text-sm font-semibold text-gray-700 mb-4">
          Top 10 Prospects
        </h3>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-gray-200 text-left text-gray-500">
                <th className="pb-2 font-medium">#</th>
                <th className="pb-2 font-medium">Organization</th>
                <th className="pb-2 font-medium">Type</th>
                <th className="pb-2 font-medium text-center">D1</th>
                <th className="pb-2 font-medium text-center">D2</th>
                <th className="pb-2 font-medium text-center">D3</th>
                <th className="pb-2 font-medium text-center">D4</th>
                <th className="pb-2 font-medium text-center">Composite</th>
                <th className="pb-2 font-medium">Tier</th>
              </tr>
            </thead>
            <tbody>
              {data.top_prospects.map((p, i) => (
                <tr
                  key={p.org_id}
                  className="border-b border-gray-100 hover:bg-gray-50"
                >
                  <td className="py-2.5 text-gray-400">{i + 1}</td>
                  <td className="py-2.5 font-medium text-gray-900">
                    {p.org_name}
                  </td>
                  <td className="py-2.5 text-gray-500">{p.org_type}</td>
                  <td className="py-2.5 text-center">
                    {p.d1_sector_fit.toFixed(1)}
                  </td>
                  <td className="py-2.5 text-center">
                    {p.d2_relationship.toFixed(1)}
                  </td>
                  <td className="py-2.5 text-center">
                    {p.d3_halo_value.toFixed(1)}
                  </td>
                  <td className="py-2.5 text-center">
                    {p.d4_emerging_fit.toFixed(1)}
                  </td>
                  <td className="py-2.5 text-center font-bold">
                    {p.composite_score.toFixed(2)}
                  </td>
                  <td className="py-2.5">
                    <TierBadge tier={p.tier} />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
