"use client";

import { useEffect, useState } from "react";

// The key identifies a request. Late responses are discarded on change/unmount.
export function useApiResource<T>(
  key: string,
  load: (signal: AbortSignal) => Promise<T>,
) {
  const [result, setResult] = useState<{
    key: string;
    data?: T;
    error?: unknown;
  }>();
  useEffect(() => {
    const controller = new AbortController();
    load(controller.signal).then(
      (data) => {
        if (!controller.signal.aborted) setResult({ key, data });
      },
      (error: unknown) => {
        if (!controller.signal.aborted)
          setResult((previous) => ({ key, error, data: previous?.data }));
      },
    );
    return () => controller.abort();
  }, [key, load]);
  return {
    data: result?.data,
    error: result?.key === key ? result.error : undefined,
    loading: result?.key !== key,
  };
}
