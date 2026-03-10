"use client";

import { useState } from "react";
import useSWR from "swr";
import Link from "next/link";
import { fetcher, exportCsvUrl } from "@/lib/api";
import { ORG_TYPES } from "@/lib/constants";
import TierBadge from "@/components/shared/TierBadge";
import type { ProspectListResponse } from "@/lib/types";
import { clsx } from "clsx";

const SORT_OPTIONS = [
  { value: "composite_score", label: "Composite Score" },
  { value: "d1_sector_fit", label: "Sector Fit" },
  { value: "d2_relationship", label: "Relationship" },
  { value: "d3_halo_value", label: "Halo Value" },
  { value: "d4_emerging_fit", label: "Emerging Fit" },
  { value: "org_name", label: "Name" },
];

const TIERS = ["PRIORITY CLOSE", "STRONG FIT", "MODERATE FIT", "WEAK FIT"];

export default function ProspectsPage() {
  const [page, setPage] = useState(1);
  const [sort, setSort] = useState("composite_score");
  const [order, setOrder] = useState("desc");
  const [tierFilter, setTierFilter] = useState("");
  const [orgTypeFilter, setOrgTypeFilter] = useState("");
  const [search, setSearch] = useState("");
  const [searchInput, setSearchInput] = useState("");

  const params = new URLSearchParams({
    page: String(page),
    page_size: "25",
    sort,
    order,
  });
  if (tierFilter) params.set("tier", tierFilter);
  if (orgTypeFilter) params.set("org_type", orgTypeFilter);
  if (search) params.set("search", search);

  const { data, error, isLoading } = useSWR<ProspectListResponse>(
    `/prospects?${params.toString()}`,
    fetcher
  );

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    setSearch(searchInput);
    setPage(1);
  };

  const toggleSort = (col: string) => {
    if (sort === col) {
      setOrder(order === "desc" ? "asc" : "desc");
    } else {
      setSort(col);
      setOrder("desc");
    }
    setPage(1);
  };

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-gray-900">Prospect Pipeline</h1>
        <a
          href={exportCsvUrl()}
          download
          className="px-4 py-2 bg-emerald-600 text-white rounded-md text-sm font-medium hover:bg-emerald-700 transition-colors"
        >
          Export CSV
        </a>
      </div>

      {/* Filters */}
      <div className="bg-white rounded-lg border border-gray-200 p-4">
        <div className="flex flex-wrap gap-3 items-end">
          {/* Search */}
          <form onSubmit={handleSearch} className="flex gap-2">
            <input
              type="text"
              placeholder="Search org name..."
              value={searchInput}
              onChange={(e) => setSearchInput(e.target.value)}
              className="px-3 py-1.5 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500"
            />
            <button
              type="submit"
              className="px-3 py-1.5 bg-emerald-600 text-white rounded-md text-sm hover:bg-emerald-700"
            >
              Search
            </button>
          </form>

          {/* Tier Filter */}
          <select
            value={tierFilter}
            onChange={(e) => {
              setTierFilter(e.target.value);
              setPage(1);
            }}
            className="px-3 py-1.5 border border-gray-300 rounded-md text-sm"
          >
            <option value="">All Tiers</option>
            {TIERS.map((t) => (
              <option key={t} value={t}>
                {t}
              </option>
            ))}
          </select>

          {/* Org Type Filter */}
          <select
            value={orgTypeFilter}
            onChange={(e) => {
              setOrgTypeFilter(e.target.value);
              setPage(1);
            }}
            className="px-3 py-1.5 border border-gray-300 rounded-md text-sm"
          >
            <option value="">All Types</option>
            {ORG_TYPES.map((t) => (
              <option key={t} value={t}>
                {t}
              </option>
            ))}
          </select>

          {/* Sort */}
          <select
            value={sort}
            onChange={(e) => {
              setSort(e.target.value);
              setPage(1);
            }}
            className="px-3 py-1.5 border border-gray-300 rounded-md text-sm"
          >
            {SORT_OPTIONS.map((s) => (
              <option key={s.value} value={s.value}>
                Sort: {s.label}
              </option>
            ))}
          </select>

          <button
            onClick={() => setOrder(order === "desc" ? "asc" : "desc")}
            className="px-3 py-1.5 border border-gray-300 rounded-md text-sm hover:bg-gray-50"
          >
            {order === "desc" ? "Desc" : "Asc"}
          </button>

          {/* Clear */}
          {(tierFilter || orgTypeFilter || search) && (
            <button
              onClick={() => {
                setTierFilter("");
                setOrgTypeFilter("");
                setSearch("");
                setSearchInput("");
                setPage(1);
              }}
              className="px-3 py-1.5 text-sm text-gray-500 hover:text-gray-700"
            >
              Clear Filters
            </button>
          )}
        </div>
      </div>

      {/* Table */}
      <div className="bg-white rounded-lg border border-gray-200 overflow-hidden">
        {isLoading ? (
          <div className="flex items-center justify-center h-32">
            <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-emerald-600" />
          </div>
        ) : error || !data ? (
          <div className="p-6 text-center text-gray-500">
            No prospects found. Import a CSV and run the pipeline first.
          </div>
        ) : (
          <>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="bg-gray-50 border-b border-gray-200 text-left">
                    <th className="px-4 py-3 font-medium text-gray-500">
                      Organization
                    </th>
                    <th className="px-4 py-3 font-medium text-gray-500">
                      Type
                    </th>
                    <th
                      className="px-3 py-3 font-medium text-gray-500 text-center cursor-pointer hover:text-gray-700"
                      onClick={() => toggleSort("d1_sector_fit")}
                    >
                      D1{sort === "d1_sector_fit" ? (order === "desc" ? " v" : " ^") : ""}
                    </th>
                    <th
                      className="px-3 py-3 font-medium text-gray-500 text-center cursor-pointer hover:text-gray-700"
                      onClick={() => toggleSort("d2_relationship")}
                    >
                      D2{sort === "d2_relationship" ? (order === "desc" ? " v" : " ^") : ""}
                    </th>
                    <th
                      className="px-3 py-3 font-medium text-gray-500 text-center cursor-pointer hover:text-gray-700"
                      onClick={() => toggleSort("d3_halo_value")}
                    >
                      D3{sort === "d3_halo_value" ? (order === "desc" ? " v" : " ^") : ""}
                    </th>
                    <th
                      className="px-3 py-3 font-medium text-gray-500 text-center cursor-pointer hover:text-gray-700"
                      onClick={() => toggleSort("d4_emerging_fit")}
                    >
                      D4{sort === "d4_emerging_fit" ? (order === "desc" ? " v" : " ^") : ""}
                    </th>
                    <th
                      className="px-3 py-3 font-medium text-gray-500 text-center cursor-pointer hover:text-gray-700"
                      onClick={() => toggleSort("composite_score")}
                    >
                      Composite{sort === "composite_score" ? (order === "desc" ? " v" : " ^") : ""}
                    </th>
                    <th className="px-4 py-3 font-medium text-gray-500">
                      Tier
                    </th>
                    <th className="px-3 py-3 font-medium text-gray-500 text-center">
                      Flags
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {data.items.map((p) => (
                    <tr
                      key={p.org_id}
                      className="border-b border-gray-100 hover:bg-gray-50 cursor-pointer"
                    >
                      <td className="px-4 py-3">
                        <Link
                          href={`/prospects/${p.org_id}`}
                          className="font-medium text-gray-900 hover:text-emerald-600"
                        >
                          {p.org_name}
                        </Link>
                        {p.top_contact_name && (
                          <p className="text-xs text-gray-400 mt-0.5">
                            {p.top_contact_name}
                            {p.top_contact_role && ` - ${p.top_contact_role}`}
                          </p>
                        )}
                      </td>
                      <td className="px-4 py-3 text-gray-500 text-xs">
                        {p.org_type}
                      </td>
                      <td className="px-3 py-3 text-center font-mono">
                        {p.d1_sector_fit.toFixed(1)}
                      </td>
                      <td className="px-3 py-3 text-center font-mono">
                        {p.d2_relationship.toFixed(1)}
                      </td>
                      <td className="px-3 py-3 text-center font-mono">
                        {p.d3_halo_value.toFixed(1)}
                      </td>
                      <td className="px-3 py-3 text-center font-mono">
                        {p.d4_emerging_fit.toFixed(1)}
                      </td>
                      <td className="px-3 py-3 text-center font-mono font-bold">
                        {p.composite_score.toFixed(2)}
                      </td>
                      <td className="px-4 py-3">
                        <TierBadge tier={p.tier} />
                      </td>
                      <td className="px-3 py-3 text-center">
                        {p.flag_count > 0 && (
                          <span className="inline-flex items-center justify-center w-5 h-5 rounded-full bg-red-100 text-red-700 text-xs font-bold">
                            {p.flag_count}
                          </span>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            {/* Pagination */}
            <div className="flex items-center justify-between px-4 py-3 border-t border-gray-200">
              <p className="text-sm text-gray-500">
                Showing {(data.page - 1) * data.page_size + 1}-
                {Math.min(data.page * data.page_size, data.total)} of{" "}
                {data.total}
              </p>
              <div className="flex gap-2">
                <button
                  onClick={() => setPage(Math.max(1, page - 1))}
                  disabled={page === 1}
                  className="px-3 py-1 text-sm border border-gray-300 rounded-md disabled:opacity-50 hover:bg-gray-50"
                >
                  Previous
                </button>
                <button
                  onClick={() => setPage(page + 1)}
                  disabled={page >= data.total_pages}
                  className="px-3 py-1 text-sm border border-gray-300 rounded-md disabled:opacity-50 hover:bg-gray-50"
                >
                  Next
                </button>
              </div>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
