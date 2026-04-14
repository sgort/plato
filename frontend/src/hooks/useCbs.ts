import { useCallback, useEffect, useState } from "react";
import { fetchCbsDatasets, fetchCbsObservations } from "@/api/client";
import type { CbsDataset, CbsObservation } from "@/types";

interface UseCbsReturn {
  datasets: CbsDataset[];
  selectedCode: string;
  observations: CbsObservation[];
  dataset: CbsDataset | null;
  loading: boolean;
  error: string | null;
  selectDataset: (code: string) => void;
}

export function useCbs(periods = 16): UseCbsReturn {
  const [datasets, setDatasets] = useState<CbsDataset[]>([]);
  const [selectedCode, setSelectedCode] = useState("83474NED");
  const [observations, setObservations] = useState<CbsObservation[]>([]);
  const [dataset, setDataset] = useState<CbsDataset | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Load dataset catalogue once
  useEffect(() => {
    fetchCbsDatasets()
      .then((d) => setDatasets(d.datasets))
      .catch(() => {});
  }, []);

  const loadObservations = useCallback(
    async (code: string) => {
      setLoading(true);
      setError(null);
      try {
        const result = await fetchCbsObservations(code, undefined, periods);
        setObservations(result.observations);
        setDataset(result.dataset);
      } catch (err) {
        setError(err instanceof Error ? err.message : "CBS ophalen mislukt");
      } finally {
        setLoading(false);
      }
    },
    [periods]
  );

  useEffect(() => {
    loadObservations(selectedCode);
  }, [selectedCode, loadObservations]);

  const selectDataset = useCallback((code: string) => {
    setSelectedCode(code);
    setObservations([]);
  }, []);

  return { datasets, selectedCode, observations, dataset, loading, error, selectDataset };
}
