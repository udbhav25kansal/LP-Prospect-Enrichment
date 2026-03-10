"use client";

import { useState, useCallback, useEffect } from "react";
import { uploadCsv, startPipeline, getPipelineStatus } from "@/lib/api";
import type { IngestResponse, PipelineStatus } from "@/lib/types";

export default function ImportPage() {
  const [file, setFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState(false);
  const [ingestResult, setIngestResult] = useState<IngestResponse | null>(null);
  const [pipelineStatus, setPipelineStatus] = useState<PipelineStatus | null>(
    null
  );
  const [error, setError] = useState<string | null>(null);
  const [polling, setPolling] = useState(false);
  const [deepResearch, setDeepResearch] = useState(false);

  const handleUpload = async () => {
    if (!file) return;
    setUploading(true);
    setError(null);

    try {
      const result = (await uploadCsv(file)) as IngestResponse;
      setIngestResult(result);
    } catch (e: any) {
      setError(e.message || "Upload failed");
    } finally {
      setUploading(false);
    }
  };

  const handleStartPipeline = async () => {
    if (!ingestResult) return;
    setError(null);

    try {
      const status = (await startPipeline(
        ingestResult.run_id,
        deepResearch
      )) as PipelineStatus;
      setPipelineStatus(status);
      setPolling(true);
    } catch (e: any) {
      setError(e.message || "Failed to start pipeline");
    }
  };

  // Poll for pipeline status
  useEffect(() => {
    if (!polling || !ingestResult) return;

    const interval = setInterval(async () => {
      try {
        const status = (await getPipelineStatus(
          ingestResult.run_id
        )) as PipelineStatus;
        setPipelineStatus(status);
        if (status.status === "completed" || status.status === "failed") {
          setPolling(false);
        }
      } catch (e) {
        // ignore polling errors
      }
    }, 3000);

    return () => clearInterval(interval);
  }, [polling, ingestResult]);

  const progressPct =
    pipelineStatus && pipelineStatus.total_orgs > 0
      ? Math.round(
          ((pipelineStatus.processed_orgs + pipelineStatus.failed_orgs) /
            pipelineStatus.total_orgs) *
            100
        )
      : 0;

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold text-gray-900">Import Prospects</h1>

      {/* Upload Section */}
      <div className="bg-white rounded-lg border border-gray-200 p-6">
        <h2 className="text-lg font-semibold text-gray-800 mb-4">
          Upload CSV
        </h2>

        <div className="border-2 border-dashed border-gray-300 rounded-lg p-8 text-center">
          <input
            type="file"
            accept=".csv"
            onChange={(e) => setFile(e.target.files?.[0] || null)}
            className="block w-full text-sm text-gray-500 file:mr-4 file:py-2 file:px-4 file:rounded-md file:border-0 file:text-sm file:font-semibold file:bg-emerald-50 file:text-emerald-700 hover:file:bg-emerald-100"
          />

          {file && (
            <div className="mt-4">
              <p className="text-sm text-gray-600">
                Selected: <strong>{file.name}</strong> (
                {(file.size / 1024).toFixed(1)} KB)
              </p>
              <button
                onClick={handleUpload}
                disabled={uploading}
                className="mt-3 px-6 py-2 bg-emerald-600 text-white rounded-md text-sm font-medium hover:bg-emerald-700 disabled:opacity-50"
              >
                {uploading ? "Uploading..." : "Upload & Parse"}
              </button>
            </div>
          )}
        </div>

        {error && (
          <div className="mt-4 p-3 bg-red-50 border border-red-200 rounded-lg text-sm text-red-700">
            {error}
          </div>
        )}
      </div>

      {/* Ingest Results */}
      {ingestResult && (
        <div className="bg-white rounded-lg border border-gray-200 p-6">
          <h2 className="text-lg font-semibold text-gray-800 mb-4">
            Import Results
          </h2>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div>
              <p className="text-sm text-gray-500">Total Contacts</p>
              <p className="text-2xl font-bold">
                {ingestResult.total_contacts}
              </p>
            </div>
            <div>
              <p className="text-sm text-gray-500">Unique Organizations</p>
              <p className="text-2xl font-bold">{ingestResult.unique_orgs}</p>
            </div>
            <div>
              <p className="text-sm text-gray-500">Skipped Rows</p>
              <p className="text-2xl font-bold">{ingestResult.skipped_rows}</p>
            </div>
            <div>
              <p className="text-sm text-gray-500">Duplicate Orgs</p>
              <p className="text-2xl font-bold">
                {ingestResult.duplicate_contacts.length}
              </p>
            </div>
          </div>

          {!pipelineStatus && (
            <div className="mt-6 space-y-4">
              {/* Deep Research Toggle */}
              <div className="flex items-start gap-3 p-4 bg-indigo-50 rounded-lg border border-indigo-200">
                <button
                  type="button"
                  role="switch"
                  aria-checked={deepResearch}
                  onClick={() => setDeepResearch(!deepResearch)}
                  className={`relative inline-flex h-6 w-11 flex-shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 ease-in-out focus:outline-none ${
                    deepResearch ? "bg-indigo-600" : "bg-gray-300"
                  }`}
                >
                  <span
                    className={`pointer-events-none inline-block h-5 w-5 transform rounded-full bg-white shadow ring-0 transition duration-200 ease-in-out ${
                      deepResearch ? "translate-x-5" : "translate-x-0"
                    }`}
                  />
                </button>
                <div>
                  <p className="text-sm font-semibold text-indigo-900">
                    Enable Deep Research Mode
                  </p>
                  <p className="text-xs text-indigo-700 mt-0.5">
                    Uses Gemini AI + Google Search for multi-source, cross-validated research.
                    More thorough and accurate but slower (~2x) and costs more per org.
                    Requires Gemini API key.
                  </p>
                </div>
              </div>

              <button
                onClick={handleStartPipeline}
                className="px-6 py-2.5 bg-emerald-600 text-white rounded-md text-sm font-medium hover:bg-emerald-700"
              >
                {deepResearch
                  ? "Start Deep Research Pipeline"
                  : "Start Enrichment & Scoring Pipeline"}
              </button>
            </div>
          )}
        </div>
      )}

      {/* Pipeline Progress */}
      {pipelineStatus && (
        <div className="bg-white rounded-lg border border-gray-200 p-6">
          <h2 className="text-lg font-semibold text-gray-800 mb-4">
            Pipeline Progress
          </h2>

          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <span className="text-sm text-gray-600">
                Status:{" "}
                <strong className="capitalize">{pipelineStatus.status}</strong>
              </span>
              <span className="text-sm text-gray-600">{progressPct}%</span>
            </div>

            <div className="w-full bg-gray-200 rounded-full h-3">
              <div
                className={`h-3 rounded-full transition-all duration-500 ${
                  pipelineStatus.status === "completed"
                    ? "bg-emerald-500"
                    : pipelineStatus.status === "failed"
                      ? "bg-red-500"
                      : "bg-blue-500"
                }`}
                style={{ width: `${progressPct}%` }}
              />
            </div>

            <div className="grid grid-cols-3 gap-4 text-center">
              <div>
                <p className="text-sm text-gray-500">Total</p>
                <p className="text-xl font-bold">
                  {pipelineStatus.total_orgs}
                </p>
              </div>
              <div>
                <p className="text-sm text-gray-500">Processed</p>
                <p className="text-xl font-bold text-emerald-600">
                  {pipelineStatus.processed_orgs}
                </p>
              </div>
              <div>
                <p className="text-sm text-gray-500">Failed</p>
                <p className="text-xl font-bold text-red-600">
                  {pipelineStatus.failed_orgs}
                </p>
              </div>
            </div>

            {pipelineStatus.status === "completed" && (
              <div className="text-center pt-4">
                <a
                  href="/dashboard"
                  className="px-6 py-2 bg-emerald-600 text-white rounded-md text-sm font-medium hover:bg-emerald-700 inline-block"
                >
                  View Dashboard
                </a>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
