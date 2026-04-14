import type { FeedSource } from "@/types";

const SOURCES: { id: FeedSource; label: string; sublabel: string }[] = [
  { id: "tk", label: "Tweede Kamer", sublabel: "moties · brieven · vragen" },
  { id: "ob", label: "Officiële Bekendmakingen", sublabel: "Staatsblad · Staatscourant" },
];

interface Props {
  value: FeedSource;
  onChange: (source: FeedSource) => void;
}

export function SourceToggle({ value, onChange }: Props) {
  return (
    <div className="flex flex-col gap-1.5">
      <p className="text-xs font-semibold uppercase tracking-widest text-slate-500 mb-1">
        Bron
      </p>
      {SOURCES.map((s) => {
        const active = value === s.id;
        return (
          <button
            key={s.id}
            onClick={() => onChange(s.id)}
            className={`
              group flex items-start gap-3 rounded-lg border px-3 py-2.5 text-left
              transition-all duration-150
              ${
                active
                  ? "border-amber-500/60 bg-amber-500/10"
                  : "border-ink-700 bg-ink-800/40 hover:border-ink-600 hover:bg-ink-800"
              }
            `}
          >
            {/* Radio dot */}
            <span className="mt-0.5 flex h-4 w-4 flex-shrink-0 items-center justify-center rounded-full border-2 transition-colors
              ${active ? 'border-amber-500' : 'border-ink-600 group-hover:border-slate-500'}">
              {active && (
                <span className="h-2 w-2 rounded-full bg-amber-500" />
              )}
            </span>
            <span>
              <span className={`block text-sm font-medium ${active ? "text-amber-400" : "text-slate-300"}`}>
                {s.label}
              </span>
              <span className="block text-xs text-slate-500">{s.sublabel}</span>
            </span>
          </button>
        );
      })}
    </div>
  );
}
