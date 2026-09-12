"use client";

import { createContext, useCallback, useContext, useState } from "react";
import { api } from "@/lib/api";
import { useApiResource } from "@/lib/use-api-resource";
import type { Oshi, Stats } from "@/lib/types";
import { Sidebar } from "./sidebar";
import { OshiForm } from "./oshi-form";

interface AppData {
  oshi: Oshi[];
  stats?: Stats;
  loading: boolean;
  error?: unknown;
  revision: number;
  refresh: () => void;
  openOshiForm: (oshi?: Oshi) => void;
}
const Context = createContext<AppData | null>(null);
export function useAppData() {
  const value = useContext(Context);
  if (!value) throw new Error("AppShell is required");
  return value;
}

export function AppShell({ children }: { children: React.ReactNode }) {
  const [revision, setRevision] = useState(0);
  const [form, setForm] = useState<{ oshi?: Oshi } | null>(null);
  const load = useCallback(async (signal: AbortSignal) => {
    const [oshi, stats] = await Promise.all([
      api.getOshi(signal),
      api.getStats(signal),
    ]);
    return { oshi, stats };
  }, []);
  const resource = useApiResource(`shared-${revision}`, load);
  const refresh = useCallback(() => setRevision((value) => value + 1), []);
  const value: AppData = {
    oshi: resource.data?.oshi ?? [],
    stats: resource.data?.stats,
    loading: resource.loading,
    error: resource.error,
    revision,
    refresh,
    openOshiForm: (oshi) => setForm({ oshi }),
  };
  return (
    <Context value={value}>
      <a className="skip-link" href="#main-content">
        Skip to content
      </a>
      <div className="app-shell">
        <Sidebar />
        <main id="main-content" className="main-content" tabIndex={-1}>
          {children}
        </main>
      </div>
      {form && (
        <OshiForm
          oshi={form.oshi}
          onClose={() => setForm(null)}
          onSaved={() => {
            setForm(null);
            refresh();
          }}
        />
      )}
    </Context>
  );
}
