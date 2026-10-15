import { useCallback, useEffect, useRef, useState } from 'react';
import { ApiError } from '../services/api';

export interface AsyncState<T> {
  data: T | null;
  error: ApiError | Error | null;
  loading: boolean;
  reload: () => void;
}

/** Runs `fn` on mount and whenever `deps` change. Ignores results of superseded calls. */
export function useAsync<T>(fn: () => Promise<T>, deps: unknown[] = []): AsyncState<T> {
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState<ApiError | Error | null>(null);
  const [loading, setLoading] = useState(true);
  const [tick, setTick] = useState(0);
  const latest = useRef(0);

  useEffect(() => {
    const id = ++latest.current;
    setLoading(true);
    fn()
      .then((d) => {
        if (id === latest.current) {
          setData(d);
          setError(null);
        }
      })
      .catch((e: Error) => {
        if (id === latest.current) setError(e);
      })
      .finally(() => {
        if (id === latest.current) setLoading(false);
      });
    return () => {
      latest.current++;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [...deps, tick]);

  const reload = useCallback(() => setTick((t) => t + 1), []);
  return { data, error, loading, reload };
}

export function useDebounced<T>(value: T, ms = 300): T {
  const [v, setV] = useState(value);
  useEffect(() => {
    const t = setTimeout(() => setV(value), ms);
    return () => clearTimeout(t);
  }, [value, ms]);
  return v;
}
