import { useCallback, useEffect, useRef, useState } from "react";
import { fetchFeed } from "@/api/client";
import type { FeedItem, FeedResponse, SearchState } from "@/types";

const PAGE_SIZE = 20;
const DEBOUNCE_MS = 350;

interface UseFeedReturn {
  items: FeedItem[];
  total: number | null;
  loading: boolean;
  loadingMore: boolean;
  error: string | null;
  hasMore: boolean;
  loadMore: () => void;
  refresh: () => void;
}

export function useFeed(search: SearchState): UseFeedReturn {
  const [items, setItems] = useState<FeedItem[]>([]);
  const [total, setTotal] = useState<number | null>(null);
  const [skip, setSkip] = useState(0);
  const [loading, setLoading] = useState(false);
  const [loadingMore, setLoadingMore] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Stable key that triggers a reset — includes source so switching TK↔OB resets
  const searchKey = `${search.source}|${search.q}|${search.types.join(",")}`;

  const doFetch = useCallback(
    async (currentSkip: number, append: boolean) => {
      if (append) setLoadingMore(true);
      else setLoading(true);
      setError(null);

      try {
        const data: FeedResponse = await fetchFeed(search, currentSkip, PAGE_SIZE);
        setItems((prev) => (append ? [...prev, ...data.items] : data.items));
        setTotal(data.total);
        setSkip(currentSkip + data.items.length);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Ophalen mislukt");
      } finally {
        setLoading(false);
        setLoadingMore(false);
      }
    },
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [searchKey]
  );

  useEffect(() => {
    if (timerRef.current) clearTimeout(timerRef.current);
    timerRef.current = setTimeout(() => {
      setItems([]);
      setSkip(0);
      setTotal(null);
      doFetch(0, false);
    }, DEBOUNCE_MS);

    return () => {
      if (timerRef.current) clearTimeout(timerRef.current);
    };
  }, [searchKey, doFetch]);

  const loadMore = useCallback(() => {
    doFetch(skip, true);
  }, [doFetch, skip]);

  const refresh = useCallback(() => {
    setItems([]);
    setSkip(0);
    setTotal(null);
    doFetch(0, false);
  }, [doFetch]);

  const hasMore = total === null ? false : items.length < total;

  return { items, total, loading, loadingMore, error, hasMore, loadMore, refresh };
}
