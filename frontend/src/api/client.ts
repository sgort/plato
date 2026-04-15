import type {
  CbsDataset,
  CbsResponse,
  FeedResponse,
  LegislationRule,
  SavedSearch,
  SearchState,
} from "@/types";

const BASE = import.meta.env.VITE_API_BASE
  ? `${import.meta.env.VITE_API_BASE}/api`
  : "/api";

async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    credentials: "include",
    cache: "no-store",          // ← add this line
    headers: { "Content-Type": "application/json", ...init?.headers },
    ...init,
  });
  if (!res.ok) {
    const detail = await res.text().catch(() => res.statusText);
    throw new Error(`API ${res.status}: ${detail}`);
  }
  return res.json() as Promise<T>;
}

// ── TK feed ───────────────────────────────────────────────────────────────────

export function fetchTkFeed(state: SearchState, skip = 0, top = 20): Promise<FeedResponse> {
  const params = new URLSearchParams();
  if (state.q) params.set("q", state.q);
  state.types.forEach((t) => params.append("types", t));
  params.set("skip", String(skip));
  params.set("top", String(top));
  return apiFetch<FeedResponse>(`/tk/feed?${params.toString()}`);
}

export function fetchTkTypes(): Promise<{ types: string[] }> {
  return apiFetch<{ types: string[] }>("/tk/types");
}

// ── OB feed ───────────────────────────────────────────────────────────────────

export function fetchObFeed(state: SearchState, skip = 0, top = 20): Promise<FeedResponse> {
  const params = new URLSearchParams();
  if (state.q) params.set("q", state.q);
  state.types.forEach((t) => params.append("types", t));
  params.set("skip", String(skip));
  params.set("top", String(top));
  return apiFetch<FeedResponse>(`/ob/feed?${params.toString()}`);
}

export function fetchObTypes(): Promise<{ types: string[] }> {
  return apiFetch<{ types: string[] }>("/ob/types");
}

// ── Unified feed dispatcher ───────────────────────────────────────────────────

export function fetchFeed(state: SearchState, skip = 0, top = 20): Promise<FeedResponse> {
  return state.source === "ob"
    ? fetchObFeed(state, skip, top)
    : fetchTkFeed(state, skip, top);
}

// ── CBS ───────────────────────────────────────────────────────────────────────

export function fetchCbsDatasets(): Promise<{ datasets: CbsDataset[] }> {
  return apiFetch<{ datasets: CbsDataset[] }>("/cbs/datasets");
}

export function fetchCbsObservations(
  datasetCode: string,
  measure?: string,
  periods = 12
): Promise<CbsResponse> {
  const params = new URLSearchParams({ periods: String(periods) });
  if (measure) params.set("measure", measure);
  return apiFetch<CbsResponse>(`/cbs/dataset/${datasetCode}/observations?${params.toString()}`);
}

// ── Legislation ───────────────────────────────────────────────────────────────

export function fetchLegislation(ruleIdPath: string): Promise<LegislationRule> {
  const encoded = encodeURIComponent(ruleIdPath);
  return apiFetch<LegislationRule>(`/legislation/rule/${encoded}`);
}

// ── Saved searches ────────────────────────────────────────────────────────────

export function fetchSavedSearches(): Promise<SavedSearch[]> {
  return apiFetch<SavedSearch[]>("/searches");
}

export function createSavedSearch(label: string, query: SearchState): Promise<SavedSearch> {
  return apiFetch<SavedSearch>("/searches", {
    method: "POST",
    body: JSON.stringify({ label, query }),
  });
}

export function deleteSavedSearch(id: string): Promise<void> {
  return apiFetch<void>(`/searches/${id}`, { method: "DELETE" });
}
