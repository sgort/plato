import { useCallback, useState } from "react";
import { fetchLegislation } from "@/api/client";
import type { LegislationResult } from "@/types";

interface UseLegislationReturn {
  result: LegislationResult | null;
  loading: boolean;
  error: string | null;
  lookup: (ruleIdPath: string) => Promise<void>;
  clear: () => void;
}

export function useLegislation(): UseLegislationReturn {
  const [result, setResult] = useState<LegislationResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const lookup = useCallback(async (ruleIdPath: string) => {
    const trimmed = ruleIdPath.trim();
    if (!trimmed) return;
    setLoading(true);
    setError(null);
    setResult(null);
    try {
      const data = await fetchLegislation(trimmed);
      setResult({ ruleIdPath: trimmed, data });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Ophalen mislukt");
    } finally {
      setLoading(false);
    }
  }, []);

  const clear = useCallback(() => {
    setResult(null);
    setError(null);
  }, []);

  return { result, loading, error, lookup, clear };
}
