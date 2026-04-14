import { useState } from "react";
import type { SavedSearch, SearchState } from "@/types";

interface Props {
  searches: SavedSearch[];
  currentQuery: SearchState;
  saving: boolean;
  onApply: (query: SearchState) => void;
  onSave: (label: string, query: SearchState) => Promise<void>;
  onDelete: (id: string) => Promise<void>;
}

export function SavedSearches({ searches, currentQuery, saving, onApply, onSave, onDelete }: Props) {
  const [label, setLabel] = useState("");
  const [showForm, setShowForm] = useState(false);
  const [deletingId, setDeletingId] = useState<string | null>(null);

  const hasQuery = Boolean(currentQuery.q || currentQuery.types.length > 0);

  async function handleSave() {
    const trimmed = label.trim();
    if (!trimmed || !hasQuery) return;
    await onSave(trimmed, currentQuery);
    setLabel("");
    setShowForm(false);
  }

  async function handleDelete(id: string) {
    setDeletingId(id);
    try {
      await onDelete(id);
    } finally {
      setDeletingId(null);
    }
  }

  return (
    <section>
      <div className="mb-3 flex items-center justify-between">
        <h2 className="text-xs font-semibold uppercase tracking-widest text-slate-500">
          Opgeslagen zoekopdrachten
        </h2>
        {hasQuery && (
          <button
            className="btn-ghost text-amber-500 hover:text-amber-400"
            onClick={() => setShowForm((v) => !v)}
          >
            {showForm ? "Annuleer" : "+ Opslaan"}
          </button>
        )}
      </div>

      {/* Save form */}
      {showForm && (
        <div className="mb-3 flex gap-2 animate-fade-in">
          <input
            className="input-base py-1.5 text-xs"
            placeholder="Naam…"
            value={label}
            onChange={(e) => setLabel(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && handleSave()}
            autoFocus
          />
          <button
            onClick={handleSave}
            disabled={saving || !label.trim()}
            className="flex-shrink-0 rounded-lg bg-amber-500 px-3 py-1.5 text-xs font-semibold
                       text-ink-900 transition-opacity hover:opacity-90 disabled:opacity-40"
          >
            {saving ? "…" : "OK"}
          </button>
        </div>
      )}

      {/* List */}
      {searches.length === 0 ? (
        <p className="text-xs text-slate-600 italic">
          {hasQuery ? "Sla je huidige zoekopdracht op via + Opslaan." : "Nog geen opgeslagen zoekopdrachten."}
        </p>
      ) : (
        <ul className="space-y-1">
          {searches.map((s) => (
            <li
              key={s.id}
              className="group flex items-center gap-2 rounded-lg px-2 py-1.5 transition-colors hover:bg-ink-800"
            >
              <button
                className="min-w-0 flex-1 text-left text-sm text-slate-300 hover:text-slate-100 truncate"
                onClick={() => onApply(s.query)}
              >
                {s.label}
                {s.query.types.length > 0 && (
                  <span className="ml-2 font-mono text-xs text-slate-600">
                    {s.query.types.join(", ")}
                  </span>
                )}
              </button>
              <button
                onClick={() => handleDelete(s.id)}
                disabled={deletingId === s.id}
                className="flex-shrink-0 opacity-0 group-hover:opacity-100 transition-opacity
                           text-slate-600 hover:text-red-400 disabled:opacity-30"
                title="Verwijder"
              >
                <svg className="h-3.5 w-3.5" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
