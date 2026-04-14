// ── Feed ─────────────────────────────────────────────────────────────────────

export type FeedSource = "tk" | "ob";

export interface FeedItem {
  id: string;
  title: string;
  type: string | null;
  number: string | null;
  date: string | null;
  url: string | null;
  source: FeedSource;
  // TK-specific
  vergaderjaar?: string | null;
  // OB-specific
  description?: string | null;
}

export interface FeedResponse {
  items: FeedItem[];
  total: number | null;
  skip: number;
  top: number;
}

// ── Search state ──────────────────────────────────────────────────────────────

export interface SearchState {
  q: string;
  types: string[];
  source: FeedSource;
}

// ── Saved searches ────────────────────────────────────────────────────────────

export interface SavedSearch {
  id: string;
  label: string;
  query: SearchState;
  created_at: string;
}

// ── CBS ───────────────────────────────────────────────────────────────────────

export interface CbsDataset {
  code: string;
  label: string;
  description: string;
  unit: string;
}

export interface CbsObservation {
  period: string;
  value: number | null;
  measure: string;
}

export interface CbsResponse {
  dataset: CbsDataset;
  observations: CbsObservation[];
}

// ── Legislation ───────────────────────────────────────────────────────────────

// cprmv-json is a recursive tree; we type the top level only.
export interface LegislationRule {
  [key: string]: unknown; // predicate URIs as keys
}

export interface LegislationResult {
  ruleIdPath: string;
  data: LegislationRule;
}

