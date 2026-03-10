const API_BASE = "/api/v1";

async function fetchApi<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { "Content-Type": "application/json", ...options?.headers },
    ...options,
  });
  if (!res.ok) {
    const error = await res.text();
    throw new Error(`API Error ${res.status}: ${error}`);
  }
  return res.json();
}

export async function uploadCsv(file: File) {
  const formData = new FormData();
  formData.append("file", file);
  const res = await fetch(`${API_BASE}/ingest/csv`, {
    method: "POST",
    body: formData,
  });
  if (!res.ok) throw new Error(`Upload failed: ${res.status}`);
  return res.json();
}

export async function startPipeline(runId: string) {
  return fetchApi(`/pipeline/${runId}/start`, { method: "POST" });
}

export async function getPipelineStatus(runId: string) {
  return fetchApi(`/pipeline/${runId}/status`);
}

export async function listPipelineRuns() {
  return fetchApi("/pipeline");
}

export async function getProspects(params: Record<string, string>) {
  const qs = new URLSearchParams(params).toString();
  return fetchApi(`/prospects?${qs}`);
}

export async function getProspectDetail(orgId: string) {
  return fetchApi(`/prospects/${orgId}`);
}

export async function getDashboardSummary(runId?: string) {
  const qs = runId ? `?run_id=${runId}` : "";
  return fetchApi(`/dashboard/summary${qs}`);
}

export async function getCosts(runId: string) {
  return fetchApi(`/costs/${runId}`);
}

export const fetcher = (url: string) =>
  fetch(`${API_BASE}${url}`).then((res) => {
    if (!res.ok) throw new Error(`${res.status}`);
    return res.json();
  });
