"use client";
import { useCallback, useEffect, useState } from "react";
import { errorMessage } from "@/lib/format";
export function useResource<T>(key: string, loader: () => Promise<T>) {
  const [version, setVersion] = useState(0);
  const [state, setState] = useState<{ key: string; data: T | null; error: string | null; loading: boolean }>({ key, data: null, error: null, loading: true });
  const reload = useCallback(() => setVersion((v) => v + 1), []);
  useEffect(() => {
    let active = true;
    Promise.resolve().then(async () => {
      if (!active) return;
      setState((previous) => ({ key, data: previous.key === key ? previous.data : null, error: null, loading: true }));
      try { const data = await loader(); if (active) setState({ key, data, error: null, loading: false }); }
      catch (error) { if (active) setState((previous) => ({ key, data: previous.key === key ? previous.data : null, error: errorMessage(error), loading: false })); }
    });
    return () => { active = false; };
  }, [key, loader, version]);
  return { data: state.key === key ? state.data : null, error: state.key === key ? state.error : null, loading: state.key !== key || state.loading, reload };
}
