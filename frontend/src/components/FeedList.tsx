import { useRef } from "react";
import { FeedCard } from "./FeedCard";
import type { FeedItem } from "@/types";

interface Props {
  items: FeedItem[];
  total: number | null;
  loading: boolean;
  loadingMore: boolean;
  error: string | null;
  hasMore: boolean;
  onLoadMore: () => void;
}

function Skeleton() {
  return (
    <div className="animate-pulse flex gap-4 rounded-xl border border-ink-700 bg-ink-800/40 px-5 py-4">
      <div className="mt-1.5 h-2 w-2 flex-shrink-0 rounded-full bg-ink-600" />
      <div className="flex-1 space-y-2">
        <div className="h-3.5 w-4/5 rounded bg-ink-700" />
        <div className="h-3 w-2/5 rounded bg-ink-700" />
      </div>
    </div>
  );
}

export function FeedList({ items, total, loading, loadingMore, error, hasMore, onLoadMore }: Props) {
  const sentinelRef = useRef<HTMLDivElement>(null);

  if (loading) {
    return (
      <div className="space-y-2">
        {Array.from({ length: 8 }).map((_, i) => (
          <Skeleton key={i} />
        ))}
      </div>
    );
  }

  if (error) {
    return (
      <div className="rounded-xl border border-red-800/50 bg-red-900/20 px-5 py-6 text-center">
        <p className="text-sm text-red-400">{error}</p>
        <p className="mt-1 text-xs text-slate-500">Controleer of de API bereikbaar is.</p>
      </div>
    );
  }

  if (items.length === 0) {
    return (
      <div className="rounded-xl border border-ink-700 bg-ink-800/40 px-5 py-12 text-center">
        <p className="text-sm text-slate-400">Geen documenten gevonden.</p>
        <p className="mt-1 text-xs text-slate-500">Pas de zoekterm of filters aan.</p>
      </div>
    );
  }

  return (
    <div className="space-y-2">
      {/* Result count */}
      {total !== null && (
        <p className="pb-1 text-xs text-slate-500 font-mono">
          {total.toLocaleString("nl-NL")} resultaten · {items.length} geladen
        </p>
      )}

      {/* Cards */}
      {items.map((item) => (
        <FeedCard key={item.id} item={item} />
      ))}

      {/* Load more */}
      <div ref={sentinelRef} className="pt-2">
        {loadingMore ? (
          <div className="space-y-2">
            {Array.from({ length: 3 }).map((_, i) => (
              <Skeleton key={i} />
            ))}
          </div>
        ) : hasMore ? (
          <button
            onClick={onLoadMore}
            className="w-full rounded-xl border border-ink-700 bg-ink-800/40 py-3
                       text-sm text-slate-400 transition-all hover:border-amber-500/50
                       hover:text-amber-400 hover:bg-ink-800"
          >
            Meer laden
          </button>
        ) : (
          <p className="text-center text-xs text-slate-600 py-2">Einde van resultaten</p>
        )}
      </div>
    </div>
  );
}
