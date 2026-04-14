import { useEffect, useState } from "react";
import { fetchTkTypes, fetchObTypes } from "@/api/client";
import { useFeed } from "@/hooks/useFeed";
import { useSavedSearches } from "@/hooks/useSavedSearches";
import { CbsWidget } from "@/components/CbsWidget";
import { FilterChips } from "@/components/FilterChips";
import { FeedList } from "@/components/FeedList";
import { LegislationLookup } from "@/components/LegislationLookup";
import { SavedSearches } from "@/components/SavedSearches";
import { SearchBar } from "@/components/SearchBar";
import { SourceToggle } from "@/components/SourceToggle";
import { ThemeToggle } from "@/components/ThemeToggle";
import type { FeedSource, SearchState } from "@/types";

const INITIAL_SEARCH: SearchState = { q: "", types: [], source: "tk" };
const TYPE_MAP: Record<FeedSource, string[]> = { tk: [], ob: [] };
const THEME_KEY = "dashboard-theme";

function useTheme() {
  const [light, setLight] = useState<boolean>(() => {
    const stored = localStorage.getItem(THEME_KEY);
    if (stored) return stored === "light";
    // Default to system preference
    return window.matchMedia("(prefers-color-scheme: light)").matches;
  });

  useEffect(() => {
    document.documentElement.classList.toggle("light", light);
    localStorage.setItem(THEME_KEY, light ? "light" : "dark");
  }, [light]);

  return { light, toggle: () => setLight((v) => !v) };
}

export default function App() {
  const [search, setSearch] = useState<SearchState>(INITIAL_SEARCH);
  const [typeMap, setTypeMap] = useState<Record<FeedSource, string[]>>(TYPE_MAP);
  const { light, toggle: toggleTheme } = useTheme();

  const { items, total, loading, loadingMore, error, hasMore, loadMore } = useFeed(search);
  const { searches, saving, save, remove } = useSavedSearches();

  useEffect(() => {
    fetchTkTypes().then((d) => setTypeMap((p) => ({ ...p, tk: d.types }))).catch(() => {});
    fetchObTypes().then((d) => setTypeMap((p) => ({ ...p, ob: d.types }))).catch(() => {});
  }, []);

  const availableTypes = typeMap[search.source] ?? [];

  function handleSourceChange(source: FeedSource) {
    setSearch((prev) => ({ ...prev, source, types: [] }));
  }

  function applySearch(query: SearchState) {
    setSearch(query);
  }

  const sourceLabel = search.source === "tk" ? "Tweede Kamer" : "Officiële Bekendmakingen";

  return (
    <div className="flex min-h-screen">
      {/* ── Sidebar ──────────────────────────────────────────────────────── */}
      <aside className="hidden lg:flex w-72 flex-shrink-0 flex-col gap-7
                        border-r border-ink-800 bg-ink-950 px-6 py-8 overflow-y-auto">
        {/* Wordmark + theme toggle */}
        <div className="flex items-start justify-between">
          <div>
            <h1 className="font-display text-2xl font-bold leading-tight text-slate-100">
              Parlementair
              <br />
              <span className="text-amber-500">Dashboard</span>
            </h1>
            <p className="mt-1 text-xs text-slate-600">open data · overheid.nl</p>
          </div>
          <ThemeToggle light={light} onToggle={toggleTheme} />
        </div>

        <div className="border-t border-ink-800" />

        <SourceToggle value={search.source} onChange={handleSourceChange} />

        <div className="border-t border-ink-800" />

        <SavedSearches
          searches={searches}
          currentQuery={search}
          saving={saving}
          onApply={applySearch}
          onSave={save}
          onDelete={remove}
        />

        <div className="border-t border-ink-800" />

        <CbsWidget />

        <div className="border-t border-ink-800" />

        <LegislationLookup />

        <div className="mt-auto pt-4 text-xs text-slate-700 space-y-0.5">
          <p>TK: gegevensmagazijn.tweedekamer.nl</p>
          <p>OB: zoekservice.overheid.nl</p>
          <p>CBS: opendata.cbs.nl</p>
          <p className="pt-1">EUPL-1.2 · open-regels.nl</p>
        </div>
      </aside>

      {/* ── Main ─────────────────────────────────────────────────────────── */}
      <main className="flex-1 flex flex-col min-w-0">
        {/* Top bar */}
        <header className="sticky top-0 z-10 border-b border-ink-800 bg-ink-900/95
                           backdrop-blur-sm px-6 py-4">
          <div className="mx-auto max-w-4xl space-y-3">
            {/* Mobile header */}
            <div className="flex items-center justify-between lg:hidden">
              <span className="font-display text-lg font-bold text-amber-500">Dashboard</span>
              <div className="flex items-center gap-2">
                <span className="text-xs text-slate-500">{sourceLabel}</span>
                <ThemeToggle light={light} onToggle={toggleTheme} />
              </div>
            </div>

            <SearchBar
              value={search.q}
              onChange={(q) => setSearch((prev) => ({ ...prev, q }))}
            />

            <div className="flex items-center gap-3">
              <span className="hidden lg:inline-flex badge bg-ink-800 border border-ink-600 text-slate-400 shrink-0">
                {sourceLabel}
              </span>
              {availableTypes.length > 0 && (
                <FilterChips
                  available={availableTypes}
                  selected={search.types}
                  onChange={(types) => setSearch((prev) => ({ ...prev, types }))}
                />
              )}
            </div>
          </div>
        </header>

        {/* Feed */}
        <div className="flex-1 px-6 py-6">
          <div className="mx-auto max-w-4xl">
            <FeedList
              items={items}
              total={total}
              loading={loading}
              loadingMore={loadingMore}
              error={error}
              hasMore={hasMore}
              onLoadMore={loadMore}
            />
          </div>
        </div>
      </main>
    </div>
  );
}
