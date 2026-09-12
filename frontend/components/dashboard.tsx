"use client";

import { useCallback, useRef, useState } from "react";
import { api, describeError } from "@/lib/api";
import { matchesSearch } from "@/lib/display";
import { useApiResource } from "@/lib/use-api-resource";
import { useFeedFilters } from "@/lib/use-feed-filters";
import type { FeedFilters, Update, UpdateStatus } from "@/lib/types";
import { useAppData } from "./app-shell";
import { CategoryFilters, FeedHeader } from "./feed-header";
import { EmptyState, ErrorState, FeedSkeleton } from "./feedback";
import { UpdateCard } from "./update-card";
import { UpdateDrawer } from "./update-drawer";

const PAGE_SIZE = 50;

function UpdateFeed({
  filters,
  search,
  open,
  changeStatus,
  busy,
  reset,
}: {
  filters: FeedFilters;
  search: string;
  open: (id: number) => void;
  changeStatus: (update: Update, status: UpdateStatus) => void;
  busy: boolean;
  reset: () => void;
}) {
  const { oshi, revision, refresh, error: sharedError } = useAppData();
  const [pages, setPages] = useState(1);
  const { oshi: oshiId, category, status, min_score } = filters;
  const load = useCallback(
    async (signal: AbortSignal) => {
      const batches = await Promise.all(
        Array.from({ length: pages }, (_, page) =>
          api.getUpdates(
            { oshi: oshiId, category, status, min_score },
            signal,
            PAGE_SIZE,
            page * PAGE_SIZE,
          ),
        ),
      );
      const unique = [
        ...new Map(
          batches.flat().map((update) => [update.id, update]),
        ).values(),
      ];
      unique.sort(
        (a, b) =>
          b.relevance_score - a.relevance_score ||
          b.created_at.localeCompare(a.created_at) ||
          b.id - a.id,
      );
      return {
        updates: unique,
        more: batches[batches.length - 1].length === PAGE_SIZE,
      };
    },
    [oshiId, category, status, min_score, pages],
  );
  const resource = useApiResource(
    `feed-${revision}-${pages}-${JSON.stringify(filters)}`,
    load,
  );
  if (sharedError) return <ErrorState error={sharedError} retry={refresh} />;
  if (resource.error)
    return <ErrorState error={resource.error} retry={refresh} />;
  if (resource.loading) return <FeedSkeleton />;
  const data = resource.data;
  const visible = (data?.updates ?? []).filter((update) =>
    matchesSearch(update, oshi, search),
  );
  return (
    <>
      <div className="feed-caption" aria-live="polite">
        <span>
          {visible.length} {visible.length === 1 ? "update" : "updates"}
          {search ? " matching your search" : " for you"}
        </span>
        <span>Highest relevance first</span>
      </div>
      {search && data?.more && (
        <p className="help-text search-note">
          Searching {data.updates.length} loaded updates. Load more to expand
          your search.
        </p>
      )}
      {visible.length ? (
        <div className="update-feed">
          {visible.map((update) => (
            <UpdateCard
              key={update.id}
              update={update}
              oshi={oshi}
              open={() => open(update.id)}
              changeStatus={(status) => changeStatus(update, status)}
              busy={busy}
            />
          ))}
        </div>
      ) : (
        <EmptyState
          title={
            search
              ? "No matches in your loaded updates"
              : "Nothing here just yet"
          }
          action={
            <button className="button" onClick={reset}>
              Clear filters & search
            </button>
          }
        >
          {search
            ? "Try another title, source, or oshi name."
            : "Try a different oshi or category, or refresh your feed."}
        </EmptyState>
      )}
      {data?.more && (
        <div className="load-more">
          <button
            className="button"
            onClick={() => setPages((value) => value + 1)}
          >
            Load more updates
          </button>
        </div>
      )}
      {Boolean(visible.length) && !data?.more && (
        <p className="feed-end">You’re all caught up with this view.</p>
      )}
    </>
  );
}

export function Dashboard() {
  const { filters, setFilters } = useFeedFilters();
  const { oshi, stats, loading, revision, refresh } = useAppData();
  const [search, setSearch] = useState("");
  const [selected, setSelected] = useState<number | null>(null);
  const [busy, setBusy] = useState(false);
  const mutationLock = useRef(false);
  const [mutationError, setMutationError] = useState("");
  const [notice, setNotice] = useState("");
  async function changeStatus(update: Update, status: UpdateStatus) {
    if (mutationLock.current || update.status === status) return;
    mutationLock.current = true;
    setBusy(true);
    setMutationError("");
    setNotice("");
    try {
      await api.setStatus(update.id, status);
      setNotice(`Update marked as ${status.toLowerCase()}.`);
      refresh();
    } catch (error) {
      setMutationError(describeError(error));
    } finally {
      mutationLock.current = false;
      setBusy(false);
    }
  }
  const selectedOshi = oshi.find((item) => item.id === filters.oshi);
  return (
    <div
      className={`dashboard page-content ${selected !== null ? "with-drawer" : ""}`}
    >
      <FeedHeader
        newCount={stats?.by_status.NEW}
        search={search}
        setSearch={setSearch}
        refreshing={loading}
        refresh={refresh}
      />
      <CategoryFilters filters={filters} onChange={setFilters} />
      {filters.oshi && (
        <div className="active-filter">
          <span>
            Following{" "}
            <strong>{selectedOshi?.name ?? `Oshi #${filters.oshi}`}</strong>
            {selectedOshi && !selectedOshi.active ? " · Paused" : ""}
          </span>
          <button
            className="text-button"
            onClick={() => setFilters({ oshi: undefined })}
          >
            Show all oshi
          </button>
        </div>
      )}
      <div className="live-notice" role="status">
        {notice}
      </div>
      {mutationError && selected === null && (
        <p className="inline-error" role="alert">
          {mutationError}
        </p>
      )}
      <UpdateFeed
        key={JSON.stringify(filters)}
        filters={filters}
        search={search}
        open={(id) => {
          setSelected(id);
          setMutationError("");
        }}
        changeStatus={changeStatus}
        busy={busy}
        reset={() => {
          setSearch("");
          setFilters({
            oshi: undefined,
            category: undefined,
            status: undefined,
            min_score: undefined,
          });
        }}
      />
      {selected !== null && (
        <UpdateDrawer
          key={selected}
          id={selected}
          revision={revision}
          oshi={oshi}
          onClose={() => setSelected(null)}
          onChange={changeStatus}
          busy={busy}
          error={mutationError}
          retry={refresh}
        />
      )}
    </div>
  );
}
