"use client";

import { createContext, useCallback, useContext, useState } from "react";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { api } from "@/lib/api";
import { useApiResource } from "@/lib/use-api-resource";
import type { Oshi, Stats } from "@/lib/types";
import { Sidebar } from "./sidebar";
import { OshiForm } from "./oshi-form";
import { DiscoverOshi } from "./discover-oshi";

interface AppData {
  oshi: Oshi[];
  stats?: Stats;
  loading: boolean;
  error?: unknown;
  revision: number;
  refresh: () => void;
  openOshiForm: (oshi?: Oshi) => void;
  oshiRemoved: (id: number) => void;
}
const Context = createContext<AppData | null>(null);
export function useAppData() {
  const value = useContext(Context);
  if (!value) throw new Error("AppShell is required");
  return value;
}

export function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const params = useSearchParams();
  const router = useRouter();
  const [revision, setRevision] = useState(0);
  const [form, setForm] = useState<Oshi | null>(null);
  const [discover, setDiscover] = useState(false);
  const [manualName, setManualName] = useState<string | null>(null);
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
    openOshiForm: (oshi) => (oshi ? setForm(oshi) : setDiscover(true)),
    oshiRemoved: (id) => {
      // Apply only a confirmed deletion, then reconcile counts and feed with the API.
      resource.updateData((data) => ({
        ...data,
        oshi: data.oshi.filter((item) => item.id !== id),
      }));
      if (Number(params.get("oshi")) === id) {
        const next = new URLSearchParams(params);
        next.delete("oshi");
        router.replace(`${pathname}${next.size ? `?${next}` : ""}`, {
          scroll: false,
        });
      }
      refresh();
    },
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
      {discover && manualName === null && (
        <DiscoverOshi
          onClose={() => setDiscover(false)}
          onManual={setManualName}
          onTracked={(oshi) => {
            resource.updateData((data) => ({
              ...data,
              oshi: [
                ...data.oshi.filter((item) => item.id !== oshi.id),
                oshi,
              ].sort((a, b) => b.priority - a.priority || a.id - b.id),
            }));
            refresh();
          }}
        />
      )}
      {(form || manualName !== null) && (
        <OshiForm
          oshi={form ?? undefined}
          initialName={manualName ?? ""}
          onClose={() => {
            setForm(null);
            setManualName(null);
          }}
          onSaved={() => {
            setForm(null);
            setManualName(null);
            setDiscover(false);
            refresh();
          }}
        />
      )}
    </Context>
  );
}
