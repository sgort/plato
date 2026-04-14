import { useState } from "react";
import { useLegislation } from "@/hooks/useLegislation";

// ── CPRMV field URIs (shortened for display) ──────────────────────────────────

const CPRMV = "https://standaarden.open-regels.nl/standards/cprmv/0.4.0/#";
const ID_URI = `${CPRMV}id`;
const DEF_URI = `${CPRMV}definition`;
const PART_URI = `${CPRMV}hasPart`;

function RuleNode({ node, depth = 0 }: { node: Record<string, unknown>; depth?: number }) {
  const [expanded, setExpanded] = useState(depth < 2);

  const id = node[ID_URI] as string | undefined;
  const def = node[DEF_URI] as string | undefined;
  const parts = node[PART_URI] as Record<string, Record<string, unknown>> | undefined;
  const hasParts = parts && Object.keys(parts).length > 0;

  return (
    <div className={`${depth > 0 ? "ml-3 border-l border-ink-700 pl-3" : ""}`}>
      {id && (
        <button
          onClick={() => hasParts && setExpanded((v) => !v)}
          className={`flex w-full items-start gap-1.5 text-left ${hasParts ? "cursor-pointer" : "cursor-default"}`}
        >
          {hasParts && (
            <svg
              className={`mt-0.5 h-3 w-3 flex-shrink-0 text-slate-500 transition-transform ${expanded ? "" : "-rotate-90"}`}
              fill="none"
              stroke="currentColor"
              strokeWidth={2}
              viewBox="0 0 24 24"
            >
              <path strokeLinecap="round" strokeLinejoin="round" d="m19 9-7 7-7-7" />
            </svg>
          )}
          {!hasParts && <span className="mt-1 h-3 w-3 flex-shrink-0" />}
          <span className="font-mono text-xs font-semibold text-amber-400">{id}</span>
        </button>
      )}
      {def && (
        <p className="mt-1 text-xs leading-relaxed text-slate-300 line-clamp-4">{def}</p>
      )}
      {hasParts && expanded && (
        <div className="mt-2 space-y-3">
          {Object.entries(parts!).map(([key, child]) => (
            <RuleNode key={key} node={child as Record<string, unknown>} depth={depth + 1} />
          ))}
        </div>
      )}
    </div>
  );
}

// ── Widget ────────────────────────────────────────────────────────────────────

const EXAMPLES = ["BWBR0002225", "BWBR0015703, Artikel 20", "CVDR712517"];

export function LegislationLookup() {
  const [open, setOpen] = useState(false);
  const [input, setInput] = useState("");
  const { result, loading, error, lookup, clear } = useLegislation();

  function handleSubmit() {
    if (!input.trim()) return;
    lookup(input.trim());
  }

  return (
    <section>
      <button
        className="mb-3 flex w-full items-center justify-between text-left"
        onClick={() => setOpen((v) => !v)}
      >
        <h2 className="text-xs font-semibold uppercase tracking-widest text-slate-500">
          Wetgeving opzoeken
        </h2>
        <svg
          className={`h-3.5 w-3.5 text-slate-600 transition-transform duration-200 ${open ? "" : "-rotate-90"}`}
          fill="none"
          stroke="currentColor"
          strokeWidth={2}
          viewBox="0 0 24 24"
        >
          <path strokeLinecap="round" strokeLinejoin="round" d="m19 9-7 7-7-7" />
        </svg>
      </button>

      {open && (
        <div className="animate-fade-in space-y-3">
          {/* Input row */}
          <div className="flex gap-2">
            <input
              className="input-base py-1.5 text-xs"
              placeholder="BWB-ID of CVDR-ID…"
              value={input}
              onChange={(e) => {
                setInput(e.target.value);
                if (result) clear();
              }}
              onKeyDown={(e) => e.key === "Enter" && handleSubmit()}
            />
            <button
              onClick={handleSubmit}
              disabled={loading || !input.trim()}
              className="flex-shrink-0 rounded-lg bg-ink-700 px-3 py-1.5 text-xs text-slate-300
                         transition-all hover:bg-ink-600 disabled:opacity-40"
            >
              {loading ? (
                <div className="h-3.5 w-3.5 animate-spin rounded-full border-2 border-amber-500 border-t-transparent" />
              ) : (
                "→"
              )}
            </button>
          </div>

          {/* Example chips */}
          {!result && !loading && (
            <div className="flex flex-wrap gap-1">
              {EXAMPLES.map((ex) => (
                <button
                  key={ex}
                  onClick={() => {
                    setInput(ex);
                    lookup(ex);
                  }}
                  className="rounded border border-ink-600 bg-ink-800 px-2 py-0.5 font-mono
                             text-xs text-slate-500 hover:border-ink-500 hover:text-slate-300
                             transition-colors"
                >
                  {ex}
                </button>
              ))}
            </div>
          )}

          {/* Error */}
          {error && (
            <p className="text-xs text-red-400">{error}</p>
          )}

          {/* Result */}
          {result && (
            <div className="max-h-72 overflow-y-auto rounded-lg border border-ink-700
                            bg-ink-800/40 p-3 space-y-2 animate-fade-in">
              <div className="flex items-center justify-between mb-2">
                <span className="font-mono text-xs text-slate-500">{result.ruleIdPath}</span>
                <button
                  onClick={clear}
                  className="text-slate-600 hover:text-slate-400"
                >
                  <svg className="h-3.5 w-3.5" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
                  </svg>
                </button>
              </div>
              <RuleNode node={result.data as Record<string, unknown>} depth={0} />
            </div>
          )}
        </div>
      )}
    </section>
  );
}
