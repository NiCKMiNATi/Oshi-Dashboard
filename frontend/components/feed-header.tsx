"use client";

import {
  CATEGORIES,
  STATUSES,
  type Category,
  type FeedFilters,
  type UpdateStatus,
} from "@/lib/types";
import { CATEGORY_LABELS, STATUS_LABELS } from "@/lib/display";

export function FeedHeader({
  newCount,
  search,
  setSearch,
  refreshing,
  refresh,
}: {
  newCount?: number;
  search: string;
  setSearch: (value: string) => void;
  refreshing: boolean;
  refresh: () => void;
}) {
  return (
    <header className="page-header feed-header">
      <div>
        <div className="heading-line">
          <h1>For You</h1>
          {newCount !== undefined && (
            <span
              className="new-count"
              title="New updates across your entire feed"
            >
              {newCount} new
            </span>
          )}
        </div>
        <p>Updates worth your attention.</p>
      </div>
      <div className="header-actions">
        <label className="search-box">
          <span className="sr-only">Search loaded updates</span>
          <input
            type="search"
            value={search}
            onChange={(event) => setSearch(event.target.value)}
            placeholder="Search updates…"
          />
        </label>
        <button
          className="button refresh-button"
          disabled={refreshing}
          onClick={refresh}
        >
          {refreshing ? "Refreshing…" : "Refresh"}
        </button>
      </div>
    </header>
  );
}

export function CategoryFilters({
  filters,
  onChange,
}: {
  filters: FeedFilters;
  onChange: (changes: Partial<FeedFilters>) => void;
}) {
  return (
    <div className="filter-section">
      <div
        className="category-filters"
        role="group"
        aria-label="Filter by category"
      >
        <button
          className={`filter-pill ${!filters.category ? "selected" : ""}`}
          aria-pressed={!filters.category}
          onClick={() => onChange({ category: undefined })}
        >
          All
        </button>
        {CATEGORIES.map((category) => (
          <button
            key={category}
            className={`filter-pill ${filters.category === category ? "selected" : ""}`}
            aria-pressed={filters.category === category}
            onClick={() => onChange({ category: category as Category })}
          >
            {CATEGORY_LABELS[category]}
          </button>
        ))}
      </div>
      <div className="secondary-filters">
        <label>
          Status
          <span className="select-control">
            <select
              aria-label="Status"
              value={filters.status ?? ""}
              onChange={(event) =>
                onChange({
                  status: (event.target.value || undefined) as
                    UpdateStatus | undefined,
                })
              }
            >
              <option value="">All statuses</option>
              {STATUSES.map((status) => (
                <option value={status} key={status}>
                  {STATUS_LABELS[status]}
                </option>
              ))}
            </select>
          </span>
        </label>
        <label>
          Minimum score
          <span className="select-control">
            <select
              aria-label="Minimum score"
              value={filters.min_score ?? 0}
              onChange={(event) =>
                onChange({ min_score: Number(event.target.value) || undefined })
              }
            >
              {[...new Set([0, 40, 65, 80, 100, filters.min_score ?? 0])]
                .sort((a, b) => a - b)
                .map((score) => (
                  <option value={score} key={score}>
                    {score === 0 ? "Any priority" : `${score}+`}
                  </option>
                ))}
            </select>
          </span>
        </label>
      </div>
    </div>
  );
}
