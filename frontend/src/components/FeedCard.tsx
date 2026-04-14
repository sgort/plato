import { formatDistanceToNow, parseISO } from "date-fns";
import { nl } from "date-fns/locale";
import type { FeedItem } from "@/types";

// TK document type colours
const TK_DOT: Record<string, string> = {
  Motie:           "bg-violet-500",
  Amendement:      "bg-blue-500",
  Brief:           "bg-teal-500",
  Kamervraag:      "bg-orange-500",
  Antwoord:        "bg-orange-400",
  Verslag:         "bg-slate-400",
  Rapport:         "bg-green-500",
  Vergaderverslag: "bg-pink-500",
  Besluitenlijst:  "bg-cyan-500",
};

// OB publication type colours
const OB_DOT: Record<string, string> = {
  Staatsblad:                      "bg-red-500",
  Staatscourant:                   "bg-amber-500",
  Tractatenblad:                   "bg-indigo-500",
  Kamerstuk:                       "bg-violet-400",
  "Blad gemeenschappelijke regeling": "bg-lime-500",
};

function dotColor(item: FeedItem): string {
  if (item.source === "ob") return OB_DOT[item.type ?? ""] ?? "bg-amber-600";
  return TK_DOT[item.type ?? ""] ?? "bg-slate-500";
}

function relativeDate(iso: string | null): string {
  if (!iso) return "—";
  try {
    return formatDistanceToNow(parseISO(iso), { addSuffix: true, locale: nl });
  } catch {
    return iso.slice(0, 10);
  }
}

function absoluteDate(iso: string | null): string {
  if (!iso) return "";
  return iso.slice(0, 10);
}

interface Props {
  item: FeedItem;
}

export function FeedCard({ item }: Props) {
  const dot = dotColor(item);

  return (
    <article
      className="group animate-slide-in relative flex gap-4 rounded-xl border border-ink-700
                 bg-ink-800/60 px-5 py-4 transition-all duration-150
                 hover:border-ink-600 hover:bg-ink-800"
    >
      {/* Source/type indicator */}
      <div className="mt-1.5 flex-shrink-0">
        <span className={`block h-2 w-2 rounded-full ${dot}`} />
      </div>

      <div className="min-w-0 flex-1">
        {/* Header row */}
        <div className="mb-1.5 flex items-start justify-between gap-3">
          <h3 className="font-sans text-sm font-medium leading-snug text-slate-100 line-clamp-2">
            {item.title}
          </h3>
          {item.url && (
            <a
              href={item.url}
              target="_blank"
              rel="noopener noreferrer"
              className="flex-shrink-0 text-slate-600 transition-colors hover:text-amber-500"
              title="Open bron"
            >
              <svg
                className="h-4 w-4"
                fill="none"
                stroke="currentColor"
                strokeWidth={1.75}
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  d="M13.5 6H5.25A2.25 2.25 0 0 0 3 8.25v10.5A2.25 2.25 0 0 0 5.25 21h10.5A2.25 2.25 0 0 0 18 18.75V10.5m-10.5 6L21 3m0 0h-5.25M21 3v5.25"
                />
              </svg>
            </a>
          )}
        </div>

        {/* OB description preview */}
        {item.source === "ob" && item.description && (
          <p className="mb-1.5 text-xs leading-relaxed text-slate-500 line-clamp-2">
            {item.description}
          </p>
        )}

        {/* Meta row */}
        <div className="flex flex-wrap items-center gap-x-3 gap-y-1">
          {item.type && (
            <span className="badge bg-ink-700 text-slate-400 border border-ink-600">
              {item.type}
            </span>
          )}
          {item.source === "tk" && item.vergaderjaar && (
            <span className="font-mono text-xs text-slate-600">{item.vergaderjaar}</span>
          )}
          {item.number && (
            <span className="font-mono text-xs text-slate-500">{item.number}</span>
          )}
          <time
            className="ml-auto font-mono text-xs text-slate-500"
            dateTime={item.date ?? ""}
            title={absoluteDate(item.date)}
          >
            {relativeDate(item.date)}
          </time>
        </div>
      </div>
    </article>
  );
}
