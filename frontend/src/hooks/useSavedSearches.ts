import { useCallback, useEffect, useState } from "react";
import {
  createSavedSearch,
  deleteSavedSearch,
  fetchSavedSearches,
} from "@/api/client";
import type { SavedSearch, SearchState } from "@/types";

interface UseSavedSearchesReturn {
  searches: SavedSearch[];
  saving: boolean;
  save: (label: string, query: SearchState) => Promise<void>;
  remove: (id: string) => Promise<void>;
}

export function useSavedSearches(): UseSavedSearchesReturn {
  const [searches, setSearches] = useState<SavedSearch[]>([]);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    fetchSavedSearches()
      .then(setSearches)
      .catch(() => {
        // Session cookie will be set on first write; silent fail on first load is fine
      });
  }, []);

  const save = useCallback(async (label: string, query: SearchState) => {
    setSaving(true);
    try {
      const created = await createSavedSearch(label, query);
      setSearches((prev) => [created, ...prev]);
    } finally {
      setSaving(false);
    }
  }, []);

  const remove = useCallback(async (id: string) => {
    await deleteSavedSearch(id);
    setSearches((prev) => prev.filter((s) => s.id !== id));
  }, []);

  return { searches, saving, save, remove };
}
